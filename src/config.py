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
CANARY_WEIGHT = float(os.getenv("CANARY_WEIGHT", "0.33"))


def localhost_url(port: int, path: str = "") -> str:
    base = f"http://localhost:{port}"
    if not path:
        return base
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


ETA_PUBLIC_BASE_URL = os.getenv("ETA_PUBLIC_BASE_URL", localhost_url(8000))
MLFLOW_PUBLIC_URL = os.getenv("MLFLOW_PUBLIC_URL", localhost_url(5000))
PROMETHEUS_PUBLIC_URL = os.getenv("PROMETHEUS_PUBLIC_URL", localhost_url(9090))
GRAFANA_PUBLIC_URL = os.getenv("GRAFANA_PUBLIC_URL", localhost_url(3000))
AIRFLOW_PUBLIC_URL = os.getenv("AIRFLOW_PUBLIC_URL", localhost_url(8080))

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
