import asyncio
import csv
import time
from pathlib import Path

import simulator.simulator as simulator
from simulator.simulator import build_schedule, choose_request, write_results


def test_schedule_is_truncated_to_lab_hour():
    schedule = build_schedule(n_requests=100, mu_min=30, sigma_min=10, seed=42)
    assert len(schedule) == 100
    assert all(0 <= minute <= 60 for minute in schedule)


def test_write_results_creates_required_csv_columns(tmp_path):
    output = tmp_path / "requests.csv"
    write_results(output, [{"request_id": "r-1", "scheduled_at_min": 1, "sent_at": "now", "operation": "create", "intentional_event": "valid", "status_code": 201, "client_latency_ms": 3.2}])
    with output.open(newline="", encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["request_id"] == "r-1"
    assert row["status_code"] == "201"


def test_scenario_doubles_invalid_probability_for_matching_category():
    operation, payload, invalid = choose_request(40, 0.08, [{"start_min": 35, "end_min": 45, "effect": "double_errors", "category": "electronics"}], draw=0.12)
    assert operation in {"create", "get", "cancel"}
    assert invalid is True
    assert payload["category"] == "electronics"


def test_send_uses_get_for_order_lookup(monkeypatch):
    class Client:
        def __init__(self):
            self.get_calls = []
            self.post_calls = []

        async def get(self, url, headers):
            self.get_calls.append((url, headers))
            return type("Response", (), {"status_code": 404})()

        async def post(self, url, json, headers):
            self.post_calls.append((url, json, headers))
            return type("Response", (), {"status_code": 201})()

    monkeypatch.setattr(simulator, "choose_request", lambda *_: ("get", {"customer_tier": "gold"}, False))
    client = Client()
    row = asyncio.run(simulator.send(client, "https://example.test", 0, 0.08, {"started": time.monotonic(), "scenarios": []}))

    assert row["status_code"] == 404
    assert client.get_calls[0][0] == "https://example.test/orders/missing-order"
    assert client.post_calls == []


def test_send_uses_a_created_order_for_valid_lookup(monkeypatch):
    class Client:
        async def get(self, url, headers):
            self.url = url
            return type("Response", (), {"status_code": 200})()

        async def post(self, url, json, headers):
            raise AssertionError("A lookup must not use POST")

    monkeypatch.setattr(simulator, "choose_request", lambda *_: ("get", {"customer_tier": "gold"}, False))
    client = Client()
    asyncio.run(simulator.send(client, "https://example.test", 0, 0.08, {"started": time.monotonic(), "scenarios": [], "order_ids": ["created-123"]}))

    assert client.url == "https://example.test/orders/created-123"
