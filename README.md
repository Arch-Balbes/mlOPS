# ETA Delivery ML System (Level 2)

ML-система прогноза времени доставки: ETL -> feature store -> обучение (MLflow) -> деплой с MAE gate и canary -> FastAPI + Prometheus + Airflow.

**Уровень зрелости: 2.** См. [docs/ML_MANIFEST.md](docs/ML_MANIFEST.md).

## Публичный API (IPv6)

Внешний доступ к сервису (домашний хост, глобальный IPv6):

| Эндпоинт | URL |
|----------|-----|
| Health | http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/health |
| Predict | `POST` http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/predict |
| Metrics | http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/metrics |

Подробно: [docs/PUBLIC_ACCESS.md](docs/PUBLIC_ACCESS.md). Переменная: `ETA_PUBLIC_BASE_URL` в [`.env.example`](.env.example).

Проверка:

```powershell
.\scripts\check_public_health.ps1
```

## Быстрый старт (локально)

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

python -m src.pipeline.run_all

# API: слушать все интерфейсы (нужно для IPv6)
uvicorn src.serve.app:app --host 0.0.0.0 --port 8000
```

Пример запроса (localhost):

```powershell
$body = '{"distance_km":5.2,"hour_of_day":14,"day_of_week":2,"warehouse_id":1,"items_count":3,"payment_type":0,"courier_load":0.4,"weather_code":0}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/predict" -Method Post -Body $body -ContentType "application/json"
```

Публичный IPv6 (тот же body):

```powershell
Invoke-RestMethod -Uri "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/predict" -Method Post -Body $body -ContentType "application/json"
```

## Docker Compose

```powershell
cd infra
docker compose up -d postgres mlflow
# После train:
docker compose up -d eta-api prometheus
```

| Сервис | Локально | Публично (только API) |
|--------|----------|------------------------|
| API | http://localhost:8000 | http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000 |
| MLflow | http://localhost:5000 | не публикуется |
| Prometheus | http://localhost:9090 | не публикуется |
| Airflow | http://localhost:8080 | не публикуется |

Если с LTE не открывается Docker по IPv6, запускайте `uvicorn` на хосте (см. PUBLIC_ACCESS.md).

## Структура

```
docs/           ML_MANIFEST, SLI_SLO, MDD_LATENCY, PUBLIC_ACCESS
src/            etl, features, train, serve, deploy, pipeline
scripts/        check_public_health.ps1
dags/           Airflow eta_ml_pipeline
infra/          docker-compose, prometheus, terraform, sql
notebooks/      mdd_latency.ipynb
tests/          pytest smoke
```

## Документация задания

- [Публичный доступ IPv6](docs/PUBLIC_ACCESS.md)
- [SLI/SLO](docs/SLI_SLO.md)
- [MDD latency](docs/MDD_LATENCY.md)
- [ML Manifest](docs/ML_MANIFEST.md)

## Terraform

```bash
cd infra/terraform
terraform init && terraform apply
```

По умолчанию `eta_api_public_url` указывает на IPv6 API; генерируется `generated.env`.
