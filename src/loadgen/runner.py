"""Synthetic /predict traffic for Prometheus demos (runs in Docker)."""
from __future__ import annotations

import os
import random
import sys
import time

import httpx

ETA_API_URL = os.getenv("ETA_API_URL", "http://eta-api:8000").rstrip("/")
INTERVAL_SEC = float(os.getenv("LOADGEN_INTERVAL_SEC", "300"))
JITTER_SEC = float(os.getenv("LOADGEN_JITTER_SEC", "60"))
MIN_REQUESTS = int(os.getenv("LOADGEN_MIN_REQUESTS", "1"))
MAX_REQUESTS = int(os.getenv("LOADGEN_MAX_REQUESTS", "5"))
INCLUDE_ACTUAL = os.getenv("LOADGEN_INCLUDE_ACTUAL", "true").lower() in ("1", "true", "yes")
STARTUP_WAIT_SEC = int(os.getenv("LOADGEN_STARTUP_WAIT_SEC", "120"))


def random_payload() -> dict:
    predicted_hint = random.uniform(25, 75)
    body: dict = {
        "distance_km": round(random.uniform(1.0, 30.0), 1),
        "hour_of_day": random.randint(0, 23),
        "day_of_week": random.randint(0, 6),
        "warehouse_id": random.randint(1, 5),
        "items_count": random.randint(1, 12),
        "payment_type": random.randint(0, 2),
        "courier_load": round(random.uniform(0.1, 0.95), 2),
        "weather_code": random.randint(0, 3),
        "order_id": f"loadgen-{random.randint(1, 10**9)}",
    }
    if INCLUDE_ACTUAL:
        body["actual_minutes"] = round(predicted_hint + random.uniform(-12, 12), 1)
    return body


def wait_for_api(client: httpx.Client) -> None:
    deadline = time.time() + STARTUP_WAIT_SEC
    while time.time() < deadline:
        try:
            r = client.get(f"{ETA_API_URL}/health", timeout=5.0)
            if r.status_code == 200:
                print(f"API ready: {ETA_API_URL}")
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    print(f"API not ready after {STARTUP_WAIT_SEC}s: {ETA_API_URL}", file=sys.stderr)
    sys.exit(1)


def run_burst(client: httpx.Client, n: int) -> None:
    for i in range(n):
        payload = random_payload()
        try:
            r = client.post(f"{ETA_API_URL}/predict", json=payload, timeout=15.0)
            r.raise_for_status()
            data = r.json()
            print(
                f"  [{i + 1}/{n}] OK model={data.get('model')} "
                f"pred={data.get('predicted_minutes')} order={payload.get('order_id')}"
            )
        except httpx.HTTPError as exc:
            print(f"  [{i + 1}/{n}] FAIL: {exc}", file=sys.stderr)
        if i < n - 1:
            time.sleep(random.uniform(0.3, 2.0))


def main() -> None:
    print(
        f"loadgen: every ~{INTERVAL_SEC}s (+/- {JITTER_SEC}s), "
        f"{MIN_REQUESTS}-{MAX_REQUESTS} requests/burst -> {ETA_API_URL}/predict"
    )
    with httpx.Client() as client:
        wait_for_api(client)
        while True:
            n = random.randint(MIN_REQUESTS, MAX_REQUESTS)
            print(f"\nBurst: {n} request(s)")
            run_burst(client, n)
            sleep_sec = max(60.0, INTERVAL_SEC + random.uniform(-JITTER_SEC, JITTER_SEC))
            print(f"Sleep {sleep_sec:.0f}s")
            time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
