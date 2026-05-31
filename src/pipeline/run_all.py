"""Run full ETA ML pipeline (local, without Airflow)."""
from __future__ import annotations

import argparse

from src.config import RAW_DIR
from src.data.generate_synthetic import generate, save_parquet
from src.deploy.register_deploy import run as deploy_run
from src.etl.clean import run as etl_run
from src.features.build import run as features_run
from src.train.train import run as train_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ETA pipeline end-to-end")
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--n-orders", type=int, default=20_000)
    args = parser.parse_args()

    orders, routes, events = generate(n_orders=args.n_orders)
    save_parquet(orders, routes, events, RAW_DIR)
    etl_run()
    features_run()
    train_run()
    if not args.skip_deploy:
        deploy_run()


if __name__ == "__main__":
    main()
