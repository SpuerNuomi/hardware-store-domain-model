"""用 Claude 驱动的售后客服 Agent。需要设置 ANTHROPIC_API_KEY。

    uv run --extra agent python agent.py
"""
import json

import anthropic
from pydantic import ValidationError

from hardware_store.executor import dispatch
from hardware_store.projections import SYSTEM_PROMPT, TOOLS
from hardware_store.repo import sample_repo

MODEL = "claude-opus-5-5"


def run_turn(client: anthropic.Anthropic, messages: list, repo) -> str:
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT + "\n\n当前用户的客户编号是 C001。",
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output = dispatch(block.name, block.input, repo)
                # 业务上的拒绝也是正常的工具结果，由模型据此回复用户
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(output, ensure_ascii=False)})
            except ValidationError as e:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"参数不合法：{e}", "is_error": True})
            except Exception as e:  # 系统故障，和业务拒绝区分开
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"系统错误：{e}", "is_error": True})
            print(f"  [工具] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
            print(f"         → {results[-1]['content']}")
        messages.append({"role": "user", "content": results})


def main() -> None:
    client = anthropic.Anthropic()
    repo = sample_repo()
    messages: list = []
    print("五金商城售后客服（输入 q 退出）")
    while (text := input("\n你：").strip()) not in {"q", "quit", ""}:
        messages.append({"role": "user", "content": text})
        print(f"客服：{run_turn(client, messages, repo)}")


if __name__ == "__main__":
    main()
