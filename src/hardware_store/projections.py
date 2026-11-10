"""从同一份领域模型生成工具定义和提示词中的规则说明。"""
from pydantic import BaseModel

from .actions import CancelOrder, FindOrders, RequestReturn
from .rules import CANCEL_RULES, RETURN_RULES, Rule


# strict 模式的 schema 不支持数值和字符串长度约束。这些约束从发给模型的 schema 中去掉，
# 执行时仍由 Pydantic 校验（见 executor.dispatch）。
_UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "multipleOf", "minLength", "maxLength"}


def _strip(schema):
    if isinstance(schema, dict):
        return {k: _strip(v) for k, v in schema.items() if k not in _UNSUPPORTED}
    if isinstance(schema, list):
        return [_strip(v) for v in schema]
    return schema


def to_tool(name: str, action: type[BaseModel]) -> dict:
    return {
        "name": name,
        "description": action.__doc__,
        "input_schema": _strip(action.model_json_schema()),
        "strict": True,
    }


def render_rules(rule_sets: dict[str, list[Rule]]) -> str:
    out = ["以下规则由系统强制执行，违反时工具会返回原因。规划时请提前考虑："]
    for action, rules in rule_sets.items():
        out.append(f"\n{action}：")
        out += [f"- {r.id} {r.text}" for r in rules]
    return "\n".join(out)


TOOLS = [
    to_tool("find_orders", FindOrders),
    to_tool("cancel_order", CancelOrder),
    to_tool("request_return", RequestReturn),
]

SYSTEM_PROMPT = "\n\n".join([
    "你是五金商城的售后客服。用户提到订单时，先用 find_orders 查询，不要猜订单号或行号。"
    "金额和可退数量以工具返回为准，不要自己计算。用户情绪激动时先安抚。",
    render_rules({"取消订单": CANCEL_RULES, "申请退货": RETURN_RULES}),
])
