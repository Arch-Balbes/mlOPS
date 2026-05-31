"""Airflow DAG: ETA ML pipeline (level 2 orchestration)."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator

# Project root on PYTHONPATH in Airflow container
PROJECT_ROOT = os.getenv("ETA_PROJECT_ROOT", "/opt/eta_ml")
sys.path.insert(0, PROJECT_ROOT)

default_args = {
    "owner": "eta-ml",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _ingest(**context):
    from src.config import RAW_DIR
    from src.data.generate_synthetic import generate, save_parquet
    from src.db import load_parquet_to_db

    orders, routes, events = generate(n_orders=20_000)
    save_parquet(orders, routes, events, RAW_DIR)
    try:
        load_parquet_to_db(str(RAW_DIR))
    except Exception as exc:
        print(f"DB load skipped: {exc}")


def _etl(**context):
    from src.etl.clean import run as etl_run
    etl_run()


def _features(**context):
    from src.features.build import run as features_run
    features_run()


def _train(**context):
    from src.train.train import run as train_run
    result = train_run()
    context["ti"].xcom_push(key="train_result", value=result)


def _check_gate(**context):
    ti = context["ti"]
    result = ti.xcom_pull(key="train_result", task_ids="train_evaluate")
    if result and result.get("gate_passed"):
        return "deploy_canary"
    return "gate_failed_skip_deploy"


def _deploy(**context):
    from src.deploy.register_deploy import run as deploy_run
    deploy_run()


def _gate_failed(**context):
    print("MAE gate failed: skipping deploy, keeping previous production model")


with DAG(
    dag_id="eta_ml_pipeline",
    default_args=default_args,
    description="ETA delivery ML: ingest -> features -> train -> deploy",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["eta", "mlops", "level2"],
) as dag:
    ingest = PythonOperator(task_id="ingest_data", python_callable=_ingest)
    etl = PythonOperator(task_id="etl_clean", python_callable=_etl)
    features = PythonOperator(task_id="build_features", python_callable=_features)
    train = PythonOperator(task_id="train_evaluate", python_callable=_train)

    gate_branch = BranchPythonOperator(
        task_id="check_mae_gate",
        python_callable=_check_gate,
    )
    deploy = PythonOperator(task_id="deploy_canary", python_callable=_deploy)
    skip_deploy = PythonOperator(task_id="gate_failed_skip_deploy", python_callable=_gate_failed)

    init_db = BashOperator(
        task_id="ensure_schema",
        bash_command=(
            f'cd {PROJECT_ROOT} && python -c "from src.db import init_schema; init_schema()"'
        ),
    )

    init_db >> ingest >> etl >> features >> train >> gate_branch
    gate_branch >> [deploy, skip_deploy]
