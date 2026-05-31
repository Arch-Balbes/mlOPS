"""ETL: clean and merge raw tables into processed dataset."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR
from src.data.generate_synthetic import generate, save_parquet


def clean_from_parquet(raw_dir: Path | None = None) -> pd.DataFrame:
    base = raw_dir or RAW_DIR
    orders = pd.read_parquet(base / "orders.parquet")
    routes = pd.read_parquet(base / "routes.parquet")
    events = pd.read_parquet(base / "delivery_events.parquet")

    orders["order_created"] = pd.to_datetime(orders["order_created"], utc=True)
    events["delivered_at"] = pd.to_datetime(events["delivered_at"], utc=True)

    df = orders.merge(routes, on="order_id").merge(events, on="order_id")
    df["delivery_minutes"] = (
        (df["delivered_at"] - df["order_created"]).dt.total_seconds() / 60.0
    )
    df = df.dropna(subset=["delivery_minutes"])
    df = df[df["delivery_minutes"] > 0]
    return df


def run(raw_dir: Path | None = None, output: Path | None = None) -> Path:
    out = output or PROCESSED_DIR
    out.mkdir(parents=True, exist_ok=True)
    df = clean_from_parquet(raw_dir)
    path = out / "merged.parquet"
    df.to_parquet(path, index=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--generate", action="store_true", help="Generate synthetic data if missing")
    args = parser.parse_args()
    if args.generate or not (args.raw_dir / "orders.parquet").exists():
        orders, routes, events = generate()
        save_parquet(orders, routes, events, args.raw_dir)
    path = run(args.raw_dir)
    print(f"Processed dataset: {path} ({pd.read_parquet(path).shape[0]} rows)")


if __name__ == "__main__":
    main()
