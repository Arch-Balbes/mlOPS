"""Load production and canary models for inference."""
from __future__ import annotations

import os
import pickle
import random
from pathlib import Path
from typing import Any

from src.config import FEATURE_COLUMNS, MODELS_DIR


def _load_pickle(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        data = pickle.load(f)
    if isinstance(data, dict) and "model" in data:
        return data
    return {"model": data, "model_name": "unknown", "feature_columns": FEATURE_COLUMNS}


class ModelRouter:
    def __init__(self) -> None:
        self.production_uri = os.getenv("MODEL_URI", str(MODELS_DIR / "deploy" / "production.pkl"))
        self.canary_uri = os.getenv("CANARY_MODEL_URI", str(MODELS_DIR / "deploy" / "canary.pkl"))
        self.canary_weight = float(os.getenv("CANARY_WEIGHT", "0.05"))
        self._prod = None
        self._canary = None

    def _ensure_loaded(self) -> None:
        if self._prod is None:
            path = Path(self.production_uri)
            if not path.exists():
                path = MODELS_DIR / "production.pkl"
            self._prod = _load_pickle(path)
        if self._canary is None and Path(self.canary_uri).exists():
            self._canary = _load_pickle(Path(self.canary_uri))

    def predict(self, features: dict[str, float | int]) -> tuple[float, str]:
        self._ensure_loaded()
        use_canary = self._canary is not None and random.random() < self.canary_weight
        bundle = self._canary if use_canary else self._prod
        assert bundle is not None
        cols = bundle.get("feature_columns", FEATURE_COLUMNS)
        import pandas as pd

        X = pd.DataFrame([{c: features[c] for c in cols}])
        pred = float(bundle["model"].predict(X)[0])
        tag = bundle.get("model_name", "model")
        if use_canary:
            tag = f"canary:{tag}"
        return pred, tag


router = ModelRouter()
