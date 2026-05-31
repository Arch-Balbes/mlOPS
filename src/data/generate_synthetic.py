"""Generate synthetic orders, routes, and delivery events for ETA training."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RAW_DIR

PAYMENT_TYPES = ["card", "cash", "wallet"]
RNG = np.random.default_rng(42)


def _delivery_minutes(
    distance_km: np.ndarray,
    hour: np.ndarray,
    courier_load: np.ndarray,
    weather: np.ndarray,
    items: np.ndarray,
) -> np.ndarray:
    base = 15.0 + distance_km * 4.2
    rush = np.where((hour >= 17) & (hour <= 20), 12.0, 0.0)
    load_penalty = courier_load * 8.0
    weather_penalty = weather * 3.5
    items_penalty = np.clip(items - 3, 0, None) * 1.5
    noise = RNG.normal(0, 6, size=len(distance_km))
    return np.clip(base + rush + load_penalty + weather_penalty + items_penalty + noise, 10, 180)


def generate(n_orders: int = 20_000, days_back: int = 180) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    end = pd.Timestamp.utcnow().normalize()
    start = end - pd.Timedelta(days=days_back)
    order_created = pd.to_datetime(
        RNG.integers(start.value, end.value, size=n_orders),
        unit="ns",
    )

    orders = pd.DataFrame(
        {
            "order_id": [f"ord_{i:06d}" for i in range(n_orders)],
            "order_created": order_created,
            "warehouse_id": RNG.integers(1, 6, size=n_orders),
            "distance_km": np.round(RNG.uniform(0.5, 25.0, size=n_orders), 2),
            "items_count": RNG.integers(1, 12, size=n_orders),
            "payment_type": RNG.choice(PAYMENT_TYPES, size=n_orders),
        }
    )

    routes = pd.DataFrame(
        {
            "route_id": [f"route_{i:06d}" for i in range(n_orders)],
            "order_id": orders["order_id"],
            "courier_id": [f"c_{RNG.integers(1, 80)}" for _ in range(n_orders)],
            "courier_load": np.round(RNG.uniform(0.1, 1.0, size=n_orders), 2),
            "weather_code": RNG.integers(0, 4, size=n_orders),
        }
    )

    hour = orders["order_created"].dt.hour.to_numpy()
    minutes = _delivery_minutes(
        orders["distance_km"].to_numpy(),
        hour,
        routes["courier_load"].to_numpy(),
        routes["weather_code"].to_numpy(),
        orders["items_count"].to_numpy(),
    )
    delivered_at = orders["order_created"] + pd.to_timedelta(minutes, unit="m")

    events = pd.DataFrame(
        {
            "event_id": [f"evt_{i:06d}" for i in range(n_orders)],
            "order_id": orders["order_id"],
            "delivered_at": delivered_at,
        }
    )
    return orders, routes, events


def save_parquet(orders: pd.DataFrame, routes: pd.DataFrame, events: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    orders.to_parquet(out_dir / "orders.parquet", index=False)
    routes.to_parquet(out_dir / "routes.parquet", index=False)
    events.to_parquet(out_dir / "delivery_events.parquet", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ETA dataset")
    parser.add_argument("--n-orders", type=int, default=20_000)
    parser.add_argument("--output", type=Path, default=RAW_DIR)
    args = parser.parse_args()
    orders, routes, events = generate(n_orders=args.n_orders)
    save_parquet(orders, routes, events, args.output)
    print(f"Saved {len(orders)} orders to {args.output}")


if __name__ == "__main__":
    main()
