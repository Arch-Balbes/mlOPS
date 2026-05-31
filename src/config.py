"""Central configuration for ETA ML system."""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
MODELS_DIR = ROOT_DIR / "models"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://eta:eta@localhost:5432/eta_db",
)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "eta_delivery")
MLFLOW_REGISTERED_MODEL = os.getenv("MLFLOW_REGISTERED_MODEL", "eta_model")

MAE_GATE_RATIO = float(os.getenv("MAE_GATE_RATIO", "1.05"))
CANARY_WEIGHT = float(os.getenv("CANARY_WEIGHT", "0.05"))

# Public URL for external access (home host IPv6)
ETA_PUBLIC_BASE_URL = os.getenv(
    "ETA_PUBLIC_BASE_URL",
    "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000",
)

FEATURE_COLUMNS = [
    "distance_km",
    "hour_of_day",
    "day_of_week",
    "warehouse_id",
    "items_count",
    "payment_type",
    "courier_load",
    "weather_code",
]
