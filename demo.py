"""不调用模型，直接执行几个动作，看领域模型怎样放行和拒绝。

    uv run python demo.py
"""
import json

from hardware_store.executor import dispatch
from hardware_store.projections import SYSTEM_PROMPT, TOOLS
from hardware_store.repo import sample_repo

CASES = [
    ("已签收订单，退 3 盒螺栓", "request_return", {"order_id": "O1001", "line_no": 1, "qty": 3, "reason": "买多了"}),
    ("同一行再退 8 盒，超过可退数量", "request_return", {"order_id": "O1001", "line_no": 1, "qty": 8, "reason": "买多了"}),
    ("退切割过的钢管", "request_return", {"order_id": "O1001", "line_no": 2, "qty": 1, "reason": "长度不对"}),
    ("退 3 台电锤，金额超过审批线", "request_return", {"order_id": "O1001", "line_no": 3, "qty": 3, "reason": "项目取消"}),
    ("取消已发货的订单", "cancel_order", {"order_id": "O1002", "reason": "不要了"}),
    ("取消已付款、未发货的订单", "cancel_order", {"order_id": "O1003", "reason": "不要了"}),
    ("编造的订单号", "cancel_order", {"order_id": "O9999", "reason": "不要了"}),
]


def main() -> None:
    repo = sample_repo()
    for title, tool, args in CASES:
        print(f"\n# {title}\n{tool}({json.dumps(args, ensure_ascii=False)})")
        print(json.dumps(dispatch(tool, args, repo), ensure_ascii=False, indent=2))

    print("\n# 生成的工具定义（request_return）")
    print(json.dumps(TOOLS[2], ensure_ascii=False, indent=2))
    print("\n# 生成的系统提示词\n" + SYSTEM_PROMPT)


if __name__ == "__main__":
    main()
