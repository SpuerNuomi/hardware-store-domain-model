# 五金商城售后：用领域模型约束 Agent

文章《用领域模型表达 Agent 的业务对象、关系和规则》的配套代码。

这个项目用一份领域模型描述五金商城的订单售后流程，包括对象、关系、状态机、规则和动作。工具定义、提示词中的规则说明、执行前的校验和测试都从这份模型生成。

## 运行

需要 Python 3.11 及以上版本和 [uv](https://docs.astral.sh/uv/)。

```bash
uv run pytest                      # 运行测试
uv run python demo.py              # 不调用模型，直接执行几个动作
uv run --extra agent python agent.py   # 用 Claude 驱动的客服 Agent，需要 ANTHROPIC_API_KEY
```

## 代码结构

| 文件 | 内容 |
| --- | --- |
| `src/hardware_store/model.py` | 对象、关系、订单和退货单的状态机、不变式 |
| `src/hardware_store/rules.py` | 推导规则（可退数量、退款金额）和行为规则（CO-01、RT-01 到 RT-05） |
| `src/hardware_store/actions.py` | 开放给模型的动作：`find_orders`、`cancel_order`、`request_return` |
| `src/hardware_store/executor.py` | 先校验、再执行；被拒绝时返回规则编号、原因和下一步建议 |
| `src/hardware_store/projections.py` | 从模型生成工具定义和系统提示词 |
| `src/hardware_store/repo.py` | 内存仓库和示例数据 |
| `tests/test_rules.py` | 每条规则的边界测试 |
| `tests/test_invariants.py` | 随机执行大量动作，每一步之后检查不变式 |
| `agent.py` | 用 Claude 接口实现的工具调用循环 |

## 几个设计决定

- 工具清单里没有 `refund` 和 `update_order`。退款只能由取消订单或退货触发，金额由系统计算。
- 申请退货时就扣减可退数量，防止同一行商品在审核期间被重复申请。
- 发给模型的工具定义开启了 `strict: true`。strict 模式不支持数值约束，`projections.py` 会把这类约束从 schema 中去掉，执行时由 Pydantic 再校验一次。
- 业务上的拒绝作为普通工具结果返回；参数不合法或系统故障时，工具结果标记 `is_error: true`。
