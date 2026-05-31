"""Register model in MLflow Registry and deploy with MAE gate + canary."""
from __future__ import annotations

import argparse
import json
import os
import shutil

import mlflow
from mlflow.tracking import MlflowClient

from src.config import MLFLOW_REGISTERED_MODEL, MLFLOW_TRACKING_URI, MODELS_DIR


def load_train_result() -> dict:
    path = MODELS_DIR / "train_metrics.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def promote_to_production(version: str | None = None) -> str:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    name = MLFLOW_REGISTERED_MODEL

    if version is None:
        versions = client.search_model_versions(f"name='{name}'")
        if not versions:
            raise RuntimeError(f"No registered versions for {name}")
        version = str(max(int(v.version) for v in versions))

    client.transition_model_version(
        name=name,
        version=version,
        stage="Production",
        archive_existing_versions=True,
    )
    return version


def deploy_local_canary(canary_weight: float | None = None) -> dict:
    """Copy production model; set canary env metadata for API."""
    weight = canary_weight if canary_weight is not None else float(os.getenv("CANARY_WEIGHT", "0.05"))
    src = MODELS_DIR / "production.pkl"
    prod_path = MODELS_DIR / "deploy" / "production.pkl"
    canary_path = MODELS_DIR / "deploy" / "canary.pkl"
    prod_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, prod_path)
    shutil.copy2(src, canary_path)

    meta = {
        "production_model": str(prod_path),
        "canary_model": str(canary_path),
        "canary_weight": weight,
        "status": "deployed",
    }
    with open(MODELS_DIR / "deploy" / "deployment.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def rollback() -> dict:
    backup = MODELS_DIR / "deploy" / "production_backup.pkl"
    prod = MODELS_DIR / "deploy" / "production.pkl"
    if backup.exists():
        shutil.copy2(backup, prod)
    return {"status": "rolled_back", "production_model": str(prod)}


def run(skip_gate: bool = False, promote_mlflow: bool = True) -> dict:
    result = load_train_result()
    gate_ok = result.get("gate_passed", False) or skip_gate

    if not gate_ok:
        rb = rollback()
        return {"deployed": False, "reason": "MAE gate failed", "rollback": rb}

    prod_path = MODELS_DIR / "production.pkl"
    deploy_dir = MODELS_DIR / "deploy"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    backup = deploy_dir / "production_backup.pkl"
    if prod_path.exists():
        shutil.copy2(prod_path, backup)

    meta = deploy_local_canary()
    out = {"deployed": True, "gate_passed": True, **meta}

    if promote_mlflow:
        try:
            ver = promote_to_production()
            out["mlflow_production_version"] = ver
        except Exception as exc:
            out["mlflow_promote_error"] = str(exc)

    print(json.dumps(out, indent=2))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()
    run(skip_gate=args.skip_gate, promote_mlflow=not args.no_mlflow)


if __name__ == "__main__":
    main()
