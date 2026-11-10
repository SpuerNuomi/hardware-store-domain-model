"""内存仓库。真实项目里换成数据库，并把每个写方法放进一个事务。"""
import itertools
from datetime import datetime, timedelta
from decimal import Decimal

from .model import Order, OrderLine, OrderStatus, ReturnRequest


class Repo:
    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}
        self.returns: list[ReturnRequest] = []
        self._ids = itertools.count(1)

    def add(self, order: Order) -> Order:
        self.orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def find_orders(self, customer_id: str) -> list[Order]:
        return [o for o in self.orders.values() if o.customer_id == customer_id]

    def cancel(self, order: Order, refund: Decimal) -> None:
        order.status = OrderStatus.CANCELLED
        order.refunded_total += refund

    def create_return(self, order: Order, line: OrderLine, qty: int, amount: Decimal,
                      reason: str, needs_approval: bool = False) -> ReturnRequest:
        line.returned_qty += qty
        ret = ReturnRequest(id=f"R{next(self._ids):04d}", order_id=order.id,
                            line_no=line.line_no, qty=qty, refund_amount=amount,
                            reason=reason, needs_approval=needs_approval)
        self.returns.append(ret)
        return ret


def sample_repo() -> Repo:
    """示例数据：客户 C001 的三张订单。"""
    repo = Repo()
    now = datetime.now()
    repo.add(Order(
        id="O1001", customer_id="C001", status=OrderStatus.DELIVERED,
        delivered_at=now - timedelta(days=2),
        paid_total=Decimal("4899.90"),
        lines=[
            OrderLine(line_no=1, sku_id="SCR-M6-20-304", sku_name="M6×20 304 内六角螺栓（100 个/盒）",
                      qty=10, paid_amount=Decimal("99.90")),
            OrderLine(line_no=2, sku_id="PIPE-DN25-CUT", sku_name="DN25 镀锌钢管（定长切割 1.2 米）",
                      qty=2, paid_amount=Decimal("300.00"), is_custom=True),
            OrderLine(line_no=3, sku_id="DRL-SDS-18V", sku_name="18V 锂电 SDS-plus 电锤",
                      qty=5, paid_amount=Decimal("4500.00")),
        ]))
    repo.add(Order(
        id="O1002", customer_id="C001", status=OrderStatus.SHIPPED,
        paid_total=Decimal("128.00"),
        lines=[OrderLine(line_no=1, sku_id="ANC-M8", sku_name="M8 膨胀螺栓（20 个/盒）",
                         qty=4, paid_amount=Decimal("128.00"))]))
    repo.add(Order(
        id="O1003", customer_id="C001", status=OrderStatus.PAID,
        paid_total=Decimal("56.00"),
        lines=[OrderLine(line_no=1, sku_id="BIT-SDS-8", sku_name="SDS-plus 8mm 钻头",
                         qty=2, paid_amount=Decimal("56.00"))]))
    return repo
