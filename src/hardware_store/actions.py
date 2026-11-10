"""动作：只开放业务动作，不开放 refund、update_order 这类工具。"""
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from .rules import CANCEL_RULES, RETURN_RULES, Rule


class FindOrders(BaseModel):
    """按客户编号查询订单，返回每一行的可退数量和可退金额。其他工具需要的订单号、行号都从这里取。"""
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(description="客户编号")


class CancelOrder(BaseModel):
    """取消一个尚未加工、尚未发货的订单。已付款的订单会自动原路退款，不需要另外发起。"""
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(description="订单号，只能取自 find_orders 的返回结果")
    reason: str = Field(description="用户陈述的取消原因")

    rules: ClassVar[list[Rule]] = CANCEL_RULES


class RequestReturn(BaseModel):
    """为已签收订单中的一行商品申请退货。退款金额由系统计算，不需要填写。"""
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(description="订单号，只能取自 find_orders 的返回结果")
    line_no: int = Field(ge=1, description="订单行号，取自 find_orders 的返回结果")
    qty: int = Field(gt=0, description="退货数量，不能超过这一行的可退数量")
    reason: str = Field(description="用户陈述的退货原因")

    rules: ClassVar[list[Rule]] = RETURN_RULES
