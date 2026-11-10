"""执行：先校验，再在同一个事务里执行效果；被拒绝时返回结构化原因。"""
from .actions import CancelOrder, FindOrders, RequestReturn
from .repo import Repo
from .rules import Rule, first_violation, refund_for, refundable_qty

NOT_FOUND = {"status": "rejected", "reason": "没有找到这个订单号",
             "next": "请先用 find_orders 按客户编号查询"}


def rejected(rule: Rule) -> dict:
    return {"status": "rejected", "rule": rule.id, "reason": rule.text, "next": rule.hint}


def run_find_orders(action: FindOrders, repo: Repo) -> dict:
    orders = repo.find_orders(action.customer_id)
    return {"orders": [
        {"order_id": o.id, "status": o.status.value,
         "lines": [{"line_no": l.line_no, "sku": l.sku_name, "qty": l.qty,
                    "is_custom": l.is_custom,
                    "refundable_qty": refundable_qty(l),
                    "refundable_amount": str(refund_for(l, refundable_qty(l)))}
                   for l in o.lines]}
        for o in orders]}


def run_cancel_order(action: CancelOrder, repo: Repo) -> dict:
    order = repo.get_order(action.order_id)
    if order is None:
        return NOT_FOUND
    if rule := first_violation(CancelOrder.rules, order, action):
        return rejected(rule)

    refund = order.paid_total - order.refunded_total
    repo.cancel(order, refund)      # 同一个事务里：改状态、记退款
    return {"status": "cancelled", "refund": str(refund)}


def run_request_return(action: RequestReturn, repo: Repo) -> dict:
    order = repo.get_order(action.order_id)
    if order is None:
        return NOT_FOUND
    line = next((l for l in order.lines if l.line_no == action.line_no), None)
    if line is None:
        return {"status": "rejected", "reason": f"这个订单没有第 {action.line_no} 行"}

    rule = first_violation(RequestReturn.rules, order, line, action)
    if rule and rule.on_fail == "reject":
        return rejected(rule)

    amount = refund_for(line, action.qty)
    # 同一个事务里：新建退货单，并扣减这一行的可退数量
    ret = repo.create_return(order, line, action.qty, amount, action.reason,
                             needs_approval=rule is not None)
    result = {"status": "pending_approval" if rule else "created",
              "return_id": ret.id, "refund_amount": str(amount)}
    if rule:
        result.update(rule=rule.id, next=rule.hint)
    return result


HANDLERS = {
    "find_orders": (FindOrders, run_find_orders),
    "cancel_order": (CancelOrder, run_cancel_order),
    "request_return": (RequestReturn, run_request_return),
}


def dispatch(name: str, args: dict, repo: Repo) -> dict:
    """按工具名执行。参数先经过 Pydantic 校验（结构规则），再进入执行逻辑。"""
    action_cls, handler = HANDLERS[name]
    return handler(action_cls.model_validate(args), repo)
