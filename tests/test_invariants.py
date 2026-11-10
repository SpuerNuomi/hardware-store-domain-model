"""随机执行大量动作，每一步之后检查不变式。

这对应文章第六节的推导：只要每个动作都先校验再执行，
不管模型选了哪些动作，系统都不会进入不合法的状态。
"""
import random

from pydantic import ValidationError

from hardware_store.executor import dispatch
from hardware_store.model import invariants
from hardware_store.repo import sample_repo

ORDER_IDS = ["O1001", "O1002", "O1003", "O9999"]


def random_action(rng: random.Random) -> tuple[str, dict]:
    if rng.random() < 0.2:
        return "cancel_order", {"order_id": rng.choice(ORDER_IDS), "reason": "随机"}
    return "request_return", {"order_id": rng.choice(ORDER_IDS),
                               "line_no": rng.randint(0, 4),
                               "qty": rng.randint(-1, 12), "reason": "随机"}


def test_invariants_hold_under_random_actions():
    for seed in range(20):
        rng = random.Random(seed)
        repo = sample_repo()
        for _ in range(200):
            name, args = random_action(rng)
            try:
                dispatch(name, args, repo)
            except ValidationError:
                pass    # 结构规则在参数校验阶段就拦住了
            for order in repo.orders.values():
                assert invariants(order) == [], (seed, name, args)
