# Optional: allow inbound TCP 3000 for Grafana (tunnel4 usually does not need this).
# Other services bind 127.0.0.1 only — no external access.
# Run as Administrator.

$port = 3000
$ruleName = "ETA ML Grafana $port"

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Rule exists: $ruleName"
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow
    Write-Host "Created: $ruleName"
}

Write-Host "`nGrafana local: http://localhost:3000"
Write-Host "External demo: tunnel4 -> localhost:3000 (see scripts/grafana_tunnel_env.ps1)"
