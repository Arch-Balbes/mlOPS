"""Train ETA models with MLflow tracking and registry."""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from src.config import (
    FEATURE_COLUMNS,
    FEATURES_DIR,
    MAE_GATE_RATIO,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_REGISTERED_MODEL,
    MLFLOW_TRACKING_URI,
    MODELS_DIR,
)


def load_features(path: Path | None = None) -> pd.DataFrame:
    p = path or (FEATURES_DIR / "features.parquet")
    return pd.read_parquet(p)


def within_15_min(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred) <= 15))


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "within_15min": within_15_min(y_true, y_pred),
    }


class WarehouseMedianBaseline:
    """Predict median delivery_minutes per warehouse_id."""

    def __init__(self):
        self.medians_: dict[int, float] = {}
        self.global_median_: float = 45.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "WarehouseMedianBaseline":
        df = X.copy()
        df["y"] = y.values
        self.medians_ = df.groupby("warehouse_id")["y"].median().to_dict()
        self.global_median_ = float(y.median())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.array(
            [self.medians_.get(int(w), self.global_median_) for w in X["warehouse_id"]],
            dtype=float,
        )


def train_models(df: pd.DataFrame) -> tuple[object, str, dict[str, float], dict[str, float]]:
    X = df[FEATURE_COLUMNS]
    y = df["delivery_minutes"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    baseline = WarehouseMedianBaseline()
    baseline.fit(X_train, y_train)
    baseline_metrics = evaluate(y_test.values, baseline.predict(X_test))

    candidates: list[tuple[str, object, dict]] = [
        ("baseline_median", baseline, baseline_metrics),
    ]

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_metrics = evaluate(y_test.values, lr.predict(X_test))
    candidates.append(("linear_regression", lr, lr_metrics))

    lgbm = LGBMRegressor(
        n_estimators=120,
        max_depth=8,
        learning_rate=0.08,
        random_state=42,
        verbose=-1,
    )
    lgbm.fit(X_train, y_train)
    lgbm_metrics = evaluate(y_test.values, lgbm.predict(X_test))
    candidates.append(("lightgbm", lgbm, lgbm_metrics))

    best = min(candidates, key=lambda c: c[2]["mae"])
    return best[1], best[0], best[2], baseline_metrics


def register_model(model, model_name: str, metrics: dict) -> str:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_params({"model_type": model_name})
        mlflow.log_metrics(metrics)
        if hasattr(model, "predict") and model_name != "baseline_median":
            mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=MLFLOW_REGISTERED_MODEL)
        else:
            path = MODELS_DIR / "baseline.pkl"
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump(model, f)
            mlflow.log_artifact(str(path), artifact_path="model")
        return run.info.run_id


def passes_gate(candidate_mae: float, baseline_mae: float, ratio: float = MAE_GATE_RATIO) -> bool:
    return candidate_mae <= baseline_mae * ratio


def run(features_path: Path | None = None, register: bool = True) -> dict:
    df = load_features(features_path)
    model, name, metrics, baseline_metrics = train_models(df)
    gate_ok = passes_gate(metrics["mae"], baseline_metrics["mae"])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    local_path = MODELS_DIR / "production.pkl"
    with open(local_path, "wb") as f:
        pickle.dump({"model": model, "model_name": name, "feature_columns": FEATURE_COLUMNS}, f)

    result = {
        "model_name": name,
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "gate_passed": gate_ok,
        "local_model_path": str(local_path),
    }

    metrics_path = MODELS_DIR / "train_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if register:
        try:
            run_id = register_model(model, name, metrics)
            result["mlflow_run_id"] = run_id
        except Exception as exc:
            result["mlflow_error"] = str(exc)

    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=None)
    parser.add_argument("--no-register", action="store_true")
    args = parser.parse_args()
    run(features_path=args.features, register=not args.no_register)


if __name__ == "__main__":
    main()
