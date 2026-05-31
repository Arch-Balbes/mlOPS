# Check ETA API on public IPv6 and localhost
param(
    [string]$PublicBaseUrl = $env:ETA_PUBLIC_BASE_URL,
    [string]$LocalUrl = "http://127.0.0.1:8000"
)

if (-not $PublicBaseUrl) {
    $PublicBaseUrl = "http://[2a00:1370:8184:1c5d:e61b:c8fa:a5ca:aed5]:8000"
}

$healthPublic = "$PublicBaseUrl.TrimEnd('/')/health"
$healthLocal = "$LocalUrl.TrimEnd('/')/health"

Write-Host "Local:  $healthLocal"
try {
    $r = Invoke-RestMethod -Uri $healthLocal -TimeoutSec 5
    Write-Host "OK:" ($r | ConvertTo-Json -Compress)
} catch {
    Write-Host "FAIL:" $_.Exception.Message
}

Write-Host "`nPublic IPv6: $healthPublic"
try {
    $r = Invoke-RestMethod -Uri $healthPublic -TimeoutSec 10
    Write-Host "OK:" ($r | ConvertTo-Json -Compress)
} catch {
    Write-Host "FAIL:" $_.Exception.Message
    Write-Host "Tip: uvicorn --host 0.0.0.0 --port 8000, disable VPN, check router IPv6 firewall"
}
