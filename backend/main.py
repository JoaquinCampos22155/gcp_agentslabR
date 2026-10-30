import json
import os
import random
import time
import uuid

ORDERS: dict[str, dict] = {}


def _response(request, status_code: int, payload: dict, *, error_type: str | None = None) -> tuple[dict, int]:
    elapsed_ms = round((time.perf_counter() - request.environ.get("orders.started_at", time.perf_counter())) * 1000, 2)
    business = payload.get("order", payload)
    outcome = "success" if status_code < 400 else "client_error" if status_code < 500 else "server_error"
    event = {
        "severity": "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR",
        "message": "request_completed",
        "request_id": request.headers.get("X-Request-ID", str(uuid.uuid4())),
        "endpoint": request.path,
        "status_code": status_code,
        "outcome": outcome,
        "error_type": error_type,
        "latency_ms": elapsed_ms,
        "customer_tier": business.get("customer_tier"),
        "category": business.get("category"),
        "amount": business.get("amount"),
    }
    print(json.dumps(event), flush=True)
    return payload, status_code


def handle(request):
    request.environ["orders.started_at"] = time.perf_counter()
    try:
        time.sleep(max(0, int(os.getenv("EXTRA_LATENCY_MS", "0"))) / 1000)
        if random.random() < float(os.getenv("FAILURE_RATE", "0")):
            return _response(request, 500, {"error": "simulated_failure"}, error_type="simulated_failure")
        segments = [part for part in request.path.split("/") if part]
        if request.method == "POST" and segments == ["orders"]:
            payload = request.get_json(silent=True)
            required = {"customer_tier", "category", "amount"}
            if not isinstance(payload, dict) or not required.issubset(payload) or not isinstance(payload["amount"], (int, float)):
                return _response(request, 400, {"error": "invalid_payload"}, error_type="invalid_payload")
            order_id = str(uuid.uuid4())
            order = {"order_id": order_id, "status": "created", **payload}
            ORDERS[order_id] = order
            return _response(request, 201, {"order_id": order_id, "order": order})
        if len(segments) == 2 and segments[0] == "orders" and request.method == "GET":
            order = ORDERS.get(segments[1])
            if not order:
                return _response(request, 404, {"error": "order_not_found"}, error_type="order_not_found")
            return _response(request, 200, {"order": order})
        if len(segments) == 3 and segments[0] == "orders" and segments[2] == "cancel" and request.method == "POST":
            order = ORDERS.get(segments[1])
            if not order:
                return _response(request, 404, {"error": "order_not_found"}, error_type="order_not_found")
            if order["status"] == "cancelled":
                return _response(request, 409, {"error": "invalid_state_change", "order": order}, error_type="invalid_state_change")
            order["status"] = "cancelled"
            return _response(request, 200, {"order": order})
        return _response(request, 404, {"error": "endpoint_not_found"}, error_type="endpoint_not_found")
    except (TypeError, ValueError):
        return _response(request, 400, {"error": "invalid_payload"}, error_type="invalid_payload")
