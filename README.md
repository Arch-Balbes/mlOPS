# ETA Delivery ML System (Level 2)

ML-система прогноза времени доставки: ETL -> feature store -> обучение (MLflow) -> деплой с MAE gate и canary -> FastAPI + Prometheus + Airflow.

**Уровень зрелости: 2.** См. [docs/ML_MANIFEST.md](docs/ML_MANIFEST.md).

## Доступ к сервисам

Все сервисы на **localhost** (в Docker привязаны к `127.0.0.1`). **Извне** доступна только **Grafana** через tunnel4.

| Сервис | URL | Логин |
|--------|-----|-------|
| ETA API /health | http://localhost:8000/health | - |
| ETA Predict | `POST` http://localhost:8000/predict | - |
| MLflow | http://localhost:5000 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | без логина |
| Airflow | http://localhost:8080 | admin / admin |


Grafana снаружи: tunnel4 на порт **3000** → `.\scripts\grafana_tunnel_env.ps1 -TunnelUrl "https://....tunnel4.com" -Recreate`

## Docker Compose

```powershell
cd infra
docker compose build airflow
docker compose up -d
```

Первый `build airflow` нужен для установки mlflow/lightgbm в образ Airflow (задача `train_evaluate`).

### Grafana (дашборды по умолчанию)

http://localhost:3000 — **без логина** (учебный стенд).

При входе открывается дашборд **ETA ML - SLI / SLO** (p95/p50 latency, RPS, UP, ошибка модели). Источник данных — Prometheus (`http://prometheus:9090` внутри Docker).

При смене туннеля:

```powershell
.\scripts\grafana_tunnel_env.ps1 -TunnelUrl "https://ВАШ-ID.tunnel4.com" -Recreate
```


**Автотрафик (опционально):** сервис `eta-loadgen` в compose раз в ~5 минут (±1 мин) шлёт 1–5 случайных `POST /predict` в `eta-api` — метрики в Prometheus обновляются без ручных запросов.

```powershell
cd infra
docker compose up -d eta-loadgen
docker logs -f infra-eta-loadgen-1
```

Метрики API: `GET http://localhost:8000/metrics` (сырой текст для отладки).

## Структура

```
docs/           CHEATSHEET, ML_MANIFEST, SLI_SLO, MDD_LATENCY
src/            etl, features, train, serve, deploy, pipeline
scripts/        check_public_health.ps1
dags/           Airflow eta_ml_pipeline
infra/          docker-compose, prometheus, grafana, terraform, sql
notebooks/      mdd_latency.ipynb
tests/          pytest smoke
```

## Документация задания

- [SLI/SLO](docs/SLI_SLO.md)
- [MDD latency](docs/MDD_LATENCY.md)
- [ML Manifest](docs/ML_MANIFEST.md)

## Terraform

```powershell
cd infra\terraform
terraform init
terraform apply
```

Генерируется `generated.env` с localhost URL.
