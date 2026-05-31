# SLI / SLO: ETA ML System (Level 2)

**API (локально):** `http://localhost:8000` — **Grafana (внешний доступ):** tunnel4 → `localhost:3000`

| Компонент | SLI | SLO | Измерение |
|-----------|-----|-----|-----------|
| ETA API | Доля успешных `POST /predict` с HTTP 2xx | >= 99.5% за 30 дней | Prometheus + access logs |
| ETA API | p95 latency `/predict` | <= 2.5 с за 30 дней | `eta_predict_latency_seconds` histogram; дашборд Grafana `ETA ML - SLI / SLO` |
| ETA API | Availability `/health` | >= 99.9% | Blackbox probe каждые 60 с |
| PostgreSQL / Feature Store | p95 время SELECT фичей по `order_id` | <= 200 мс | App-side timing / pg_stat |
| MLflow Registry | p95 latency чтения Production версии | <= 1 с | Client metrics при старте API |
| Airflow DAG `eta_ml_pipeline` | Доля успешных daily runs | >= 99% за 30 дней | Airflow UI / метрики |
| Train job | Wall-clock полного train+eval | <= 30 мин | XCom / task duration |
| Model quality | Rolling MAE vs baseline (7d) | MAE <= baseline * 1.05 | `eta_abs_error_minutes` + batch eval |
| Model quality | On-time rate (+/-15 мин окно) | Не ниже baseline - 0.5 п.п. за 7d canary | BI / feedback loop |
| CI pipeline | Green builds on `main` | >= 95% за месяц | GitHub Actions |

## Алерты (рекомендации)

- **Critical:** p95 latency > 3.0 с 15 мин подряд
- **Critical:** DAG failed 2 раза подряд
- **Warning:** rolling MAE > baseline * 1.05
- **Warning:** PSI(`distance_km`) > 0.2 (дрейф)

## Canary gate (deploy)

Новая модель выкатывается при одновременном выполнении:

1. Offline MAE <= baseline * 1.05
2. Canary 33% трафика 7 дней без роста online MAE > 5%
3. p95 API остается <= 2.5 с

При провале: rollback на `production_backup.pkl` и архив версии в MLflow.
