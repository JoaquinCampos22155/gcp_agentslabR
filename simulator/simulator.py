import asyncio
import csv
import json
import time
import uuid
from pathlib import Path

import httpx
import numpy as np

FIELDS = ["request_id", "scheduled_at_min", "sent_at", "operation", "intentional_event", "status_code", "client_latency_ms"]


def build_schedule(n_requests: int, mu_min: float, sigma_min: float, seed: int) -> list[float]:
    return np.clip(np.random.default_rng(seed).normal(mu_min, sigma_min, n_requests), 0, 60).tolist()


def write_results(output: Path, rows: list[dict]) -> None:
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def choose_request(minute: float, invalid_share: float, scenarios: list[dict], draw: float | None = None):
    matching = next((item for item in scenarios if item["start_min"] <= minute <= item["end_min"]), None)
    category = matching.get("category", "books") if matching else "books"
    probability = invalid_share * 2 if matching and matching.get("effect") == "double_errors" else invalid_share
    invalid = (np.random.random() if draw is None else draw) < probability
    operation = ("create", "get", "cancel")[int((np.random.random() if draw is None else draw) * 3) % 3]
    return operation, {"customer_tier": "gold", "category": category, "amount": 19.5}, invalid


async def send(client, target_url, scheduled_at_min, invalid_share, scenario):
    await asyncio.sleep(max(0, scheduled_at_min * 60 - (time.monotonic() - scenario["started"])))
    request_id = str(uuid.uuid4())
    operation, payload, invalid = choose_request(scheduled_at_min, invalid_share, scenario["scenarios"])
    url = target_url.rstrip("/") + "/orders"
    order_ids = scenario.setdefault("order_ids", [])
    order_id = order_ids[-1] if order_ids and not invalid else "missing-order"
    if operation == "get":
        url += f"/{order_id}"
    elif operation == "cancel":
        url += f"/{order_id}/cancel"
    if invalid:
        payload = {"category": payload["category"]}
    started = time.perf_counter()
    headers = {"X-Request-ID": request_id}
    if operation == "get":
        response = await client.get(url, headers=headers)
    else:
        response = await client.post(url, json=payload, headers=headers)
    if operation == "create" and response.status_code == 201:
        created_id = response.json().get("order_id")
        if created_id:
            order_ids.append(created_id)
    return {"request_id": request_id, "scheduled_at_min": scheduled_at_min, "sent_at": time.time(), "operation": operation, "intentional_event": "invalid_payload" if invalid else "valid", "status_code": response.status_code, "client_latency_ms": round((time.perf_counter() - started) * 1000, 2)}


async def main(config_path=Path(__file__).with_name("config.json")):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    scenario = {"started": time.monotonic(), "scenarios": config["scenarios"]}
    schedule = build_schedule(config["n_requests"], config["mu_min"], config["sigma_min"], config["seed"])
    async with httpx.AsyncClient(timeout=60) as client:
        rows = await asyncio.gather(*(send(client, config["target_url"], minute, config["invalid_share"], scenario) for minute in schedule))
    write_results(Path(config_path).with_name("requests.csv"), rows)


if __name__ == "__main__":
    asyncio.run(main())
