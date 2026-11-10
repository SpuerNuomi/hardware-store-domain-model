"""推导规则（由系统计算）和行为规则（执行前校验）。"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Callable, Literal

from .model import ORDER_TRANSITIONS, OrderLine, OrderStatus

CENT = Decimal("0.01")
RETURN_WINDOW = timedelta(days=7)
APPROVAL_THRESHOLD = Decimal("2000")


# ---- 推导规则 ----

def refundable_qty(line: OrderLine) -> int:
    return line.qty - line.returned_qty


def refund_for(line: OrderLine, qty: int) -> Decimal:
    """按这一行的实付分摊计算退款，向下取整到分。"""
    return (line.paid_amount * qty / line.qty).quantize(CENT, rounding=ROUND_DOWN)


# ---- 行为规则 ----

@dataclass(frozen=True)
class Rule:
    id: str
    text: str                       # 给人和模型读
    check: Callable[..., bool]      # 给程序执行
    on_fail: Literal["reject", "require_approval"] = "reject"
    hint: str = ""                  # 违反之后，建议模型下一步怎么做


CANCEL_RULES = [
    Rule("CO-01", "只有待支付或已支付（尚未加工、尚未发货）的订单可以取消",
         lambda o, a: OrderStatus.CANCELLED in ORDER_TRANSITIONS[o.status],
         hint="已发货的订单引导用户拒收，已签收的订单引导用户申请退货，加工中的订单转人工"),
]

# 按顺序检查，遇到第一条不满足的就停；需要审批的规则必须放在最后。
RETURN_RULES = [
    Rule("RT-01", "只有已签收的订单可以退货",
         lambda o, line, a: o.status == OrderStatus.DELIVERED,
         hint="未发货的订单可以直接取消"),
    Rule("RT-02", "签收超过 7 天不可退货",
         lambda o, line, a: datetime.now() - o.delivered_at <= RETURN_WINDOW),
    Rule("RT-03", "加工件不可退货",
         lambda o, line, a: not line.is_custom,
         hint="向用户说明加工件不退；如果是质量问题，转质量投诉"),
    Rule("RT-04", "退货数量不能超过这一行的可退数量",
         lambda o, line, a: a.qty <= refundable_qty(line),
         hint="用 find_orders 查看每一行的可退数量，再和用户确认"),
    Rule("RT-05", "退款金额超过 2000 元需要人工审批",
         lambda o, line, a: refund_for(line, a.qty) <= APPROVAL_THRESHOLD,
         on_fail="require_approval",
         hint="告诉用户申请已提交审批，不要承诺结果"),
]


def first_violation(rules: list[Rule], *args) -> Rule | None:
    for rule in rules:
        if not rule.check(*args):
            return rule
    return None
