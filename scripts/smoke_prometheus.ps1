# Generate /predict traffic into the Docker ETA API (same instance Prometheus scrapes).
param(
    [string]$PrometheusBase = "http://127.0.0.1:9090",
    [string]$EtaContainer = "infra-eta-api-1",
    [int]$Requests = 5
)

function Test-Port8000Conflict {
    $listeners = netstat -ano | Select-String "LISTENING" | Select-String ":8000"
    $pids = @()
    foreach ($line in $listeners) {
        if ($line -match "\s+(\d+)\s*$") { $pids += [int]$Matches[1] }
    }
    $unique = $pids | Sort-Object -Unique
    if ($unique.Count -gt 1) {
        Write-Warning "Port 8000: multiple PIDs ($($unique -join ', ')). localhost may not hit Docker eta-api."
        Write-Warning "Stop local uvicorn or Prometheus will show empty ETA metrics."
    }
}

Test-Port8000Conflict

$predictPy = "import json,urllib.request;b={'distance_km':5.2,'hour_of_day':14,'day_of_week':2,'warehouse_id':1,'items_count':3,'payment_type':1,'courier_load':0.4,'weather_code':0,'actual_minutes':42};d=json.dumps(b).encode();r=urllib.request.Request('http://127.0.0.1:8000/predict',data=d,method='POST',headers={'Content-Type':'application/json'});print(urllib.request.urlopen(r,timeout=10).read().decode())"

$container = docker ps --filter "name=$EtaContainer" --format "{{.Names}}" 2>$null
if (-not $container) {
    Write-Error "Container $EtaContainer not found. Run: cd infra; docker compose up -d"
    exit 1
}

Write-Host "=== Prometheus targets ==="
try {
    $targets = Invoke-RestMethod -Uri "$PrometheusBase/api/v1/targets" -TimeoutSec 10
    foreach ($t in $targets.data.activeTargets) {
        Write-Host "  $($t.labels.job): $($t.health) $($t.scrapeUrl)"
    }
} catch {
    Write-Error "Prometheus unreachable: $PrometheusBase"
    exit 1
}

Write-Host "`n=== POST /predict x$Requests (inside $container) ==="
for ($i = 1; $i -le $Requests; $i++) {
    try {
        $out = docker exec $container python -c $predictPy 2>&1
        if ($LASTEXITCODE -ne 0) { throw $out }
        Write-Host "  $i OK $out"
    } catch {
        Write-Host "  $i FAIL: $_"
        exit 1
    }
}

Write-Host "`nWaiting 25s for scrape (interval 15s)..."
Start-Sleep -Seconds 25

$queries = @(
    'up',
    'eta_predictions_total',
    'eta_predict_latency_seconds_count',
    'histogram_quantile(0.95, sum(rate(eta_predict_latency_seconds_bucket[5m])) by (le))'
)

Write-Host "`n=== PromQL ==="
foreach ($q in $queries) {
    $enc = [uri]::EscapeDataString($q)
    $res = Invoke-RestMethod -Uri "$PrometheusBase/api/v1/query?query=$enc" -TimeoutSec 10
    $n = @($res.data.result).Count
    Write-Host "  $q -> $n series"
    foreach ($row in $res.data.result) {
        $m = $row.metric
        $extra = if ($m.model) { " model=$($m.model)" } elseif ($m.job) { " job=$($m.job)" } else { "" }
        Write-Host "    $($m.__name__)$extra = $($row.value[1])"
    }
}

Write-Host ""
Write-Host "UI: ${PrometheusBase}/graph"
Write-Host 'Queries: up | eta_predictions_total | rate(eta_predictions_total[1m])'
