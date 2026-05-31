"""FastAPI ETA prediction service with Prometheus metrics."""
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.config import (
    AIRFLOW_PUBLIC_URL,
    ETA_PUBLIC_BASE_URL,
    FEATURE_COLUMNS,
    GRAFANA_PUBLIC_URL,
    MLFLOW_PUBLIC_URL,
    PROMETHEUS_PUBLIC_URL,
)
from src.db import get_engine
from src.serve.model_loader import router

PREDICTIONS = Counter("eta_predictions_total", "Total ETA predictions", ["model"])
LATENCY = Histogram(
    "eta_predict_latency_seconds",
    "Latency of /predict",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0),
)
ABS_ERROR = Histogram(
    "eta_abs_error_minutes",
    "Absolute error when actual is provided",
    buckets=(5, 10, 15, 20, 30, 45, 60),
)

app = FastAPI(title="ETA Prediction API", version="1.0.0")


class PredictRequest(BaseModel):
    order_id: Optional[str] = None
    distance_km: float = Field(..., gt=0)
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    warehouse_id: int = Field(..., ge=1)
    items_count: int = Field(..., ge=1)
    payment_type: int = Field(..., ge=0, le=2)
    courier_load: float = Field(..., ge=0, le=1)
    weather_code: int = Field(0, ge=0, le=3)
    actual_minutes: Optional[float] = None


class PredictResponse(BaseModel):
    order_id: Optional[str]
    predicted_minutes: float
    promised_window_min: float
    promised_window_max: float
    model: str


def _window(pred: float, margin: float = 15.0) -> tuple[float, float]:
    return max(10.0, pred - margin), pred + margin


def _log_prediction(order_id: str | None, pred: float, model: str) -> None:
    if not order_id:
        return
    try:
        eng = get_engine()
        with eng.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO predictions_log (order_id, predicted_minutes, model_uri) "
                    "VALUES (:oid, :pred, :uri)"
                ),
                {"oid": order_id, "pred": pred, "uri": model},
            )
    except Exception:
        pass


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "eta-api",
        "public_base_url": ETA_PUBLIC_BASE_URL,
        "health_url": f"{ETA_PUBLIC_BASE_URL.rstrip('/')}/health",
        "predict_url": f"{ETA_PUBLIC_BASE_URL.rstrip('/')}/predict",
        "mlflow_url": MLFLOW_PUBLIC_URL,
        "prometheus_url": PROMETHEUS_PUBLIC_URL,
        "grafana_url": GRAFANA_PUBLIC_URL,
        "airflow_url": AIRFLOW_PUBLIC_URL,
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    start = time.perf_counter()
    features = {c: getattr(req, c) for c in FEATURE_COLUMNS}
    try:
        pred, model_name = router.predict(features)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model unavailable: {exc}") from exc

    LATENCY.observe(time.perf_counter() - start)
    PREDICTIONS.labels(model=model_name).inc()

    if req.actual_minutes is not None:
        ABS_ERROR.observe(abs(req.actual_minutes - pred))

    wmin, wmax = _window(pred)
    _log_prediction(req.order_id, pred, model_name)

    return PredictResponse(
        order_id=req.order_id,
        predicted_minutes=round(pred, 1),
        promised_window_min=round(wmin, 1),
        promised_window_max=round(wmax, 1),
        model=model_name,
    )


@app.get("/features/{order_id}")
def get_features(order_id: str) -> dict:
    try:
        eng = get_engine()
        with eng.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM features_eta WHERE order_id = :oid"),
                {"oid": order_id},
            ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def main() -> None:
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("src.serve.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
