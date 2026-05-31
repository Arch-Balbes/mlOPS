"""Smoke tests for ETA pipeline."""
from __future__ import annotations

import numpy as np
import pytest

from src.config import FEATURE_COLUMNS
from src.data.generate_synthetic import generate, save_parquet
from src.etl.clean import clean_from_parquet
from src.features.build import build_features
from src.train.train import evaluate, passes_gate, train_models


@pytest.fixture
def sample_data(tmp_path):
    orders, routes, events = generate(n_orders=500)
    save_parquet(orders, routes, events, tmp_path)
    return tmp_path


def test_synthetic_generation(sample_data):
    df = clean_from_parquet(sample_data)
    assert len(df) == 500
    assert "delivery_minutes" in df.columns
    assert df["delivery_minutes"].min() > 0


def test_feature_build(sample_data):
    df = clean_from_parquet(sample_data)
    feats = build_features(df)
    assert list(feats.columns) == [
        "order_id",
        "feature_set_id",
        *FEATURE_COLUMNS,
        "delivery_minutes",
    ]


def test_train_and_gate(sample_data):
    df = clean_from_parquet(sample_data)
    feats = build_features(df)
    model, name, metrics, baseline = train_models(feats)
    assert metrics["mae"] > 0
    assert name in ("baseline_median", "linear_regression", "lightgbm")
    assert isinstance(passes_gate(metrics["mae"], baseline["mae"]), bool)


def test_evaluate_metrics():
    y = np.array([40.0, 50.0, 60.0])
    pred = np.array([42.0, 48.0, 70.0])
    m = evaluate(y, pred)
    assert "mae" in m and "within_15min" in m
