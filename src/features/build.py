"""Build feature set and persist to parquet + PostgreSQL feature store."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.config import FEATURES_DIR, PROCESSED_DIR
from src.db import get_engine, init_schema

PAYMENT_MAP = {"card": 0, "cash": 1, "wallet": 2}
FEATURE_SET_ID = "v1"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hour_of_day"] = out["order_created"].dt.hour.astype(int)
    out["day_of_week"] = out["order_created"].dt.dayofweek.astype(int)
    out["payment_type"] = out["payment_type"].map(PAYMENT_MAP).fillna(0).astype(int)
    out["feature_set_id"] = FEATURE_SET_ID
    cols = [
        "order_id",
        "feature_set_id",
        "distance_km",
        "hour_of_day",
        "day_of_week",
        "warehouse_id",
        "items_count",
        "payment_type",
        "courier_load",
        "weather_code",
        "delivery_minutes",
    ]
    return out[cols]


def save_to_feature_store(features: pd.DataFrame, engine=None) -> int:
    eng = engine or get_engine()
    init_schema(eng)
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE features_eta"))
    features.to_sql("features_eta", eng, if_exists="append", index=False, method="multi", chunksize=500)
    return len(features)


def run(processed_path: Path | None = None, output_dir: Path | None = None) -> Path:
    proc = processed_path or (PROCESSED_DIR / "merged.parquet")
    df = pd.read_parquet(proc)
    features = build_features(df)
    out_dir = output_dir or FEATURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "features.parquet"
    features.to_parquet(path, index=False)
    try:
        n = save_to_feature_store(features)
        print(f"Loaded {n} rows into features_eta")
    except Exception as exc:
        print(f"Feature store DB skip: {exc}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=PROCESSED_DIR / "merged.parquet")
    args = parser.parse_args()
    path = run(args.input)
    print(f"Features saved: {path}")


if __name__ == "__main__":
    main()
