import json
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    monkeypatch.setenv("FAILURE_RATE", "0")
    monkeypatch.setenv("EXTRA_LATENCY_MS", "0")
    from backend import main
    main.ORDERS.clear()


def request(method, path, payload=None, request_id="req-1"):
    from backend.main import handle
    return handle(SimpleNamespace(
        method=method,
        path=path,
        headers={"X-Request-ID": request_id},
        environ={},
        get_json=lambda silent=True: payload,
    ))


def test_create_order_returns_201_and_structured_log(capsys):
    body, status = request("POST", "/orders", {"customer_tier": "gold", "category": "electronics", "amount": 19.5})
    assert status == 201
    order_id = body["order_id"]
    event = json.loads(capsys.readouterr().out)
    assert event["message"] == "request_completed"
    assert event["request_id"] == "req-1"
    assert event["status_code"] == 201
    assert event["customer_tier"] == "gold"
    assert event["category"] == "electronics"
    assert event["amount"] == 19.5
    assert order_id


def test_missing_order_is_404():
    body, status = request("GET", "/orders/missing")
    assert status == 404
    assert body["error"] == "order_not_found"


def test_cancelling_twice_is_409():
    body, _ = request("POST", "/orders", {"customer_tier": "basic", "category": "books", "amount": 10})
    assert request("POST", f"/orders/{body['order_id']}/cancel")[1] == 200
    assert request("POST", f"/orders/{body['order_id']}/cancel")[1] == 409
