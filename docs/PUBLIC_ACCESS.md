# Публичный доступ к ETA API (IPv6)

Продакшен-эндпоинт для внешних клиентов (checkout, проверка задания):

| | |
|---|---|
| **Базовый URL** | `http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000` |
| **Health** | `http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/health` |
| **Predict** | `POST http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/predict` |
| **Metrics** | `http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/metrics` |

Квадратные скобки `[]` в URL обязательны для IPv6.

## Сеть

- **Интерфейс:** Wi-Fi ("Беспроводная сеть"), префикс провайдера `2a00:1370:8184:1c5d::/64`
- **Стабильный IPv6** (без privacy/temporary): `2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5`
- **IPv4 из интернета:** недоступен (LAN `192.168.1.70`, CGNAT), клиенты только с **IPv6** или через резервный туннель (ngrok)
- **Не использовать для публикации:** Radmin VPN (`fdfd::`), Teredo (`2001:0:...`), WSL (`172.20.x`)

## Подготовка хоста

### 1. Брандмауэр Windows (выполнено)

```powershell
New-NetFirewallRule -DisplayName "ETA API 8000 IPv6" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### 2. Запуск API

```powershell
cd c:\Users\egort\Documents\mlOPS
.\venv\Scripts\activate
python -m src.pipeline.run_all   # при необходимости
uvicorn src.serve.app:app --host 0.0.0.0 --port 8000
```

Или Docker (если входящий IPv6 до контейнера доходит):

```powershell
cd infra
docker compose up -d eta-api
```

При проблемах с IPv6 + Docker лучше **uvicorn на хосте** (`--host 0.0.0.0`).

### 3. Роутер

- IPv6 включен, входящие на хост не блокируются (IPv6 Firewall / "Защита")
- Port forwarding для IPv4 **не обязателен** при прямом глобальном IPv6 на ПК
- Отключить **Radmin VPN** на время демонстрации

## Проверка

**Локально:**

```powershell
curl http://127.0.0.1:8000/health
curl "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/health"
```

**С телефона (LTE, Wi-Fi выключен):** открыть health URL в браузере.

**Predict (PowerShell):**

```powershell
$uri = "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000/predict"
$body = @{
  distance_km = 5.2
  hour_of_day = 14
  day_of_week = 2
  warehouse_id = 1
  items_count = 3
  payment_type = 0
  courier_load = 0.4
  weather_code = 0
} | ConvertTo-Json
Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json"
```

Скрипт: [`scripts/check_public_health.ps1`](../scripts/check_public_health.ps1)

## Переменные окружения

См. [`.env.example`](../.env.example):

```env
ETA_PUBLIC_BASE_URL=http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000
```

## Смена IPv6

Windows может выдать новый **временный** IPv6. Для отчета используйте адрес **без** пометки "Временный" в `ipconfig`, либо настройте Duck DNS (AAAA) и обновите `ETA_PUBLIC_BASE_URL` в `.env`.

## Резерв (клиенты без IPv6)

```powershell
ngrok http 8000
```

В отчете указать основной канал (IPv6) и резерв (ngrok URL).
