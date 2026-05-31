"""Database helpers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or DATABASE_URL, pool_pre_ping=True)


@contextmanager
def connection(engine: Engine | None = None) -> Generator:
    eng = engine or get_engine()
    with eng.connect() as conn:
        yield conn


def init_schema(engine: Engine | None = None, sql_path: str | None = None) -> None:
    from src.config import ROOT_DIR

    eng = engine or get_engine()
    path = sql_path or str(ROOT_DIR / "infra" / "sql" / "init.sql")
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    with eng.begin() as conn:
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def load_parquet_to_db(raw_dir: str | None = None) -> None:
    """Load raw parquet files into PostgreSQL."""
    from pathlib import Path

    import pandas as pd

    from src.config import RAW_DIR

    base = Path(raw_dir or RAW_DIR)
    eng = get_engine()
    init_schema(eng)

    for name, table in [
        ("orders.parquet", "orders"),
        ("routes.parquet", "routes"),
        ("delivery_events.parquet", "delivery_events"),
    ]:
        path = base / name
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        with eng.begin() as conn:
            conn.execute(text(f"TRUNCATE {table} CASCADE"))
        df.to_sql(table, eng, if_exists="append", index=False, method="multi", chunksize=500)
