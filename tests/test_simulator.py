import csv
from pathlib import Path

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
