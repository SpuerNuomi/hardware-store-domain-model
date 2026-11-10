"""单条规则的边界测试。"""
from datetime import datetime, timedelta

import pytest

from hardware_store.actions import CancelOrder, RequestReturn
from hardware_store.executor import run_cancel_order, run_request_return
from hardware_store.model import OrderStatus
from hardware_store.repo import sample_repo


@pytest.fixture
def repo():
    return sample_repo()


def ret(order_id="O1001", line_no=1, qty=1):
    return RequestReturn(order_id=order_id, line_no=line_no, qty=qty, reason="测试")


@pytest.mark.parametrize("days, allowed", [(6.99, True), (7.01, False)])
def test_rt02_return_window(repo, days, allowed):
    repo.get_order("O1001").delivered_at = datetime.now() - timedelta(days=days)
    assert (run_request_return(ret(), repo)["status"] != "rejected") == allowed


def test_rt01_only_delivered(repo):
    assert run_request_return(ret("O1002"), repo)["rule"] == "RT-01"


def test_rt03_custom_item(repo):
    assert run_request_return(ret(line_no=2), repo)["rule"] == "RT-03"


@pytest.mark.parametrize("qty, allowed", [(10, True), (11, False)])
def test_rt04_refundable_qty(repo, qty, allowed):
    assert (run_request_return(ret(qty=qty), repo)["status"] != "rejected") == allowed


def test_rt04_counts_previous_requests(repo):
    assert run_request_return(ret(qty=6), repo)["status"] == "created"
    assert run_request_return(ret(qty=5), repo)["rule"] == "RT-04"


@pytest.mark.parametrize("qty, status", [(2, "created"), (3, "pending_approval")])
def test_rt05_approval_threshold(repo, qty, status):
    # 电锤每台实付 900 元：2 台 1800 元，3 台 2700 元
    assert run_request_return(ret(line_no=3, qty=qty), repo)["status"] == status


def test_co01_shipped_cannot_cancel(repo):
    assert run_cancel_order(CancelOrder(order_id="O1002", reason="x"), repo)["rule"] == "CO-01"


def test_cancel_paid_order_refunds_in_full(repo):
    result = run_cancel_order(CancelOrder(order_id="O1003", reason="x"), repo)
    order = repo.get_order("O1003")
    assert result["status"] == "cancelled"
    assert order.status == OrderStatus.CANCELLED
    assert order.refunded_total == order.paid_total


def test_unknown_order_rejected(repo):
    assert run_cancel_order(CancelOrder(order_id="O9999", reason="x"), repo)["status"] == "rejected"
