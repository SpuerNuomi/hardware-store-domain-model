"""对象、关系、生命周期和不变式。"""
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class OrderStatus(str, Enum):
    PENDING = "待支付"
    PAID = "已支付"
    PROCESSING = "加工中"
    SHIPPED = "已发货"
    DELIVERED = "已签收"
    CANCELLED = "已取消"


class OrderLine(BaseModel):
    line_no: int
    sku_id: str                    # 关系：订单行 → SKU
    sku_name: str
    qty: int                       # 购买数量
    paid_amount: Decimal           # 这一行分摊到的实付金额
    is_custom: bool = False        # 是否按客户要求加工过
    returned_qty: int = 0          # 已申请退货的数量


class Order(BaseModel):
    """订单。订单行和退款金额只能通过订单上的动作修改（聚合）。"""
    id: str
    customer_id: str               # 关系：订单 → 客户
    status: OrderStatus
    lines: list[OrderLine]         # 关系：一个订单有多个订单行
    paid_total: Decimal = Decimal("0")
    refunded_total: Decimal = Decimal("0")
    delivered_at: datetime | None = None


class ReturnStatus(str, Enum):
    REQUESTED = "待审核"
    AWAITING_ITEM = "待寄回"
    RECEIVED = "已收货"
    REFUNDED = "已退款"
    REJECTED = "已拒绝"


class ReturnRequest(BaseModel):
    id: str
    order_id: str                  # 关系：退货单 → 订单
    line_no: int                   # 关系：退货单 → 订单行
    qty: int
    refund_amount: Decimal         # 由系统计算，不由模型填写
    reason: str
    needs_approval: bool = False
    status: ReturnStatus = ReturnStatus.REQUESTED


# 生命周期：每个状态允许变成哪些状态
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING:    {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID:       {OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED:    {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED:  set(),
    OrderStatus.CANCELLED:  set(),
}

RETURN_TRANSITIONS: dict[ReturnStatus, set[ReturnStatus]] = {
    ReturnStatus.REQUESTED:     {ReturnStatus.AWAITING_ITEM, ReturnStatus.REJECTED},
    ReturnStatus.AWAITING_ITEM: {ReturnStatus.RECEIVED},
    ReturnStatus.RECEIVED:      {ReturnStatus.REFUNDED},
    ReturnStatus.REFUNDED:      set(),
    ReturnStatus.REJECTED:      set(),
}


def invariants(order: Order) -> list[str]:
    """检查订单是否处于合法状态，返回所有不成立的条件。"""
    errors = []
    for line in order.lines:
        if not 0 <= line.returned_qty <= line.qty:
            errors.append(f"第 {line.line_no} 行的退货数量超出了购买数量")
    if order.refunded_total > order.paid_total:
        errors.append("累计退款超过了实付金额")
    return errors
