# Update infra/.env for Grafana behind tunnel4 (dynamic root_url + CSRF origin).
param(
    [Parameter(Mandatory = $true)]
    [string]$TunnelUrl,
    [switch]$Recreate,
    [switch]$ResetGrafanaData
)

$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root "infra\.env"

$u = $TunnelUrl.Trim().TrimEnd("/")
if ($u -match "/login") {
    $u = $u -replace "/login$", ""
}
if ($u -notmatch "^https?://") {
    Write-Error "Pass full URL, e.g. https://abc123.tunnel4.com"
    exit 1
}

# Do NOT set GRAFANA_ROOT_URL: compose uses %(protocol)s://%(domain)s/ from tunnel Host header.
$grafanaVars = [ordered]@{
    GRAFANA_CSRF_ORIGINS      = $u
    GRAFANA_COOKIE_SECURE     = "false"
    GRAFANA_COOKIE_SAMESITE   = "lax"
    GRAFANA_ANONYMOUS_ENABLED = "true"
    GRAFANA_DISABLE_LOGIN     = "true"
}

$other = @{}
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $Matches[1].Trim()
            if ($key -eq "GRAFANA_ROOT_URL") { return }
            if (-not $grafanaVars.Contains($key)) {
                $other[$key] = $Matches[2].Trim()
            }
        }
    }
}

$lines = @(
    "# Grafana tunnel (updated $(Get-Date -Format 'yyyy-MM-dd HH:mm'))",
    "# root_url is dynamic: %(protocol)s://%(domain)s/ from request Host"
)
foreach ($k in $grafanaVars.Keys) {
    $lines += "$k=$($grafanaVars[$k])"
}
foreach ($k in ($other.Keys | Sort-Object)) {
    $lines += "$k=$($other[$k])"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($envFile, $lines, $utf8NoBom)
Write-Host "Updated: $envFile"
foreach ($k in $grafanaVars.Keys) {
    Write-Host "  $k=$($grafanaVars[$k])"
}

if ($ResetGrafanaData) {
    Push-Location (Join-Path $root "infra")
    docker compose stop grafana 2>$null
    docker rm -f infra-grafana-1 2>$null
    Pop-Location
    Write-Host "Removed grafana container (fresh datasource uid=prometheus)."
}

if ($Recreate) {
    Push-Location (Join-Path $root "infra")
    docker compose up -d grafana --force-recreate
    Pop-Location
    Write-Host "Grafana recreated. Open: $u"
    Write-Host "If 403 on /api/ds/query persists, tunnel4 may block POST — use http://localhost:3000 for Grafana."
} else {
    Write-Host ""
    Write-Host "Recreate: cd infra; docker compose up -d grafana --force-recreate"
}
