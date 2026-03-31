# ============================================================
# ErrorLens Deploy Verify
# Checks that after docker compose up --build nginx
# server serves new JS bundle (no stale cache)
#
# Usage:
#   pwsh -File scripts\deploy-verify.ps1
#   pwsh -File scripts\deploy-verify.ps1 -Host 192.168.1.74 -Port 3000
# ============================================================

param(
    [string]$ServerHost = "192.168.1.74",
    [int]$ServerPort    = 3000,
    [string]$Username   = "admin",
    [string]$Password   = "Misha2026",
    [switch]$Quiet
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistDir     = Join-Path $ProjectRoot "dashboard-vue\dist\assets"
$BaseUrl     = "http://${ServerHost}:${ServerPort}"

function Write-Status {
    param([string]$Msg, [string]$Status = "INFO")
    $color = switch ($Status) {
        "OK"   { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "INFO" { "Cyan" }
        default { "Gray" }
    }
    if (-not $Quiet) {
        Write-Host "[$Status] $Msg" -ForegroundColor $color
    }
}

$errors = 0
$checks = 0

Write-Status "════════════════════════════════════"
Write-Status "ErrorLens Deploy Verify"
Write-Status "Server: $BaseUrl"
Write-Status "════════════════════════════════════"

# ── 1. Health check ───────────────────────────────────────────
$checks++
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/api/health" -TimeoutSec 10
    if ($health.status -eq "ok") {
        Write-Status "Backend health: OK (version=$($health.version))" "OK"
    } else {
        Write-Status "Backend health: unexpected response" "WARN"
    }
} catch {
    Write-Status "Backend health FAILED: $_" "FAIL"
    $errors++
}

# ── 2. Auth login ─────────────────────────────────────────────
$checks++
$token = $null
try {
    $loginBody = @{ username = $Username; password = $Password } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri "$BaseUrl/api/auth/login" `
                                    -Method POST `
                                    -Body $loginBody `
                                    -ContentType "application/json" `
                                    -TimeoutSec 10
    $token = $loginResp.access_token
    if ($token) {
        Write-Status "Auth login: OK" "OK"
    } else {
        Write-Status "Auth login: no token in response" "FAIL"
        $errors++
    }
} catch {
    Write-Status "Auth login FAILED: $_" "FAIL"
    $errors++
}

# ── 3. Dashboard page loads ───────────────────────────────────
$checks++
try {
    $dashResp = Invoke-WebRequest -Uri "$BaseUrl/dashboard/" -TimeoutSec 10 -UseBasicParsing
    if ($dashResp.StatusCode -eq 200 -and $dashResp.Content -match 'script.*\.js') {
        Write-Status "Dashboard page: OK (${BaseUrl}/dashboard/)" "OK"
    } else {
        Write-Status "Dashboard page: unexpected content (status=$($dashResp.StatusCode))" "WARN"
    }
} catch {
    Write-Status "Dashboard page FAILED: $_" "FAIL"
    $errors++
}

# ── 4. JS bundle hash comparison ─────────────────────────────
$checks++
Write-Status "Checking JS bundle hashes..."

if (-not (Test-Path $DistDir)) {
    Write-Status "Local dist/assets not found: $DistDir" "WARN"
} else {
    $localFiles = Get-ChildItem -Path $DistDir -Filter "*.js" -File
    if (-not $localFiles) {
        Write-Status "No .js files in local dist/assets" "WARN"
    } else {
        $mainBundle = $localFiles |
            Where-Object { $_.Name -match '^index-' } |
            Sort-Object Length -Descending |
            Select-Object -First 1

        if (-not $mainBundle) {
            $mainBundle = $localFiles | Sort-Object Length -Descending | Select-Object -First 1
        }

        if ($mainBundle) {
            $localHash = (Get-FileHash -Path $mainBundle.FullName -Algorithm MD5).Hash
            $serverJsUrl = "$BaseUrl/dashboard/dist/assets/$($mainBundle.Name)"

            try {
                $serverBytes = (Invoke-WebRequest -Uri $serverJsUrl -TimeoutSec 15 -UseBasicParsing).Content
                $stream = [System.IO.MemoryStream]::new([byte[]]$serverBytes)
                $md5 = [System.Security.Cryptography.MD5]::Create()
                $serverHashBytes = $md5.ComputeHash($stream)
                $serverHash = [BitConverter]::ToString($serverHashBytes).Replace("-","")
                $stream.Dispose()

                if ($localHash -eq $serverHash) {
                    Write-Status "Bundle hash MATCH: $($mainBundle.Name)" "OK"
                    Write-Status "  Local:  $localHash" "INFO"
                    Write-Status "  Server: $serverHash" "INFO"
                } else {
                    Write-Status "Bundle hash MISMATCH! Server has OLD bundle!" "FAIL"
                    Write-Status "  Expected (local):  $localHash" "INFO"
                    Write-Status "  Got (server):      $serverHash" "INFO"
                    Write-Status "  File: $($mainBundle.Name)" "INFO"
                    Write-Status "  Try: docker compose exec nginx nginx -s reload" "WARN"
                    $errors++
                }
            } catch {
                Write-Status "Could not fetch server bundle: $_" "WARN"
                Write-Status "  Tried URL: $serverJsUrl" "INFO"
            }
        }
    }
}

# ── 5. API endpoint smoke tests ───────────────────────────────
if ($token) {
    $checks++
    $headers = @{ Authorization = "Bearer $token" }
    $endpoints = @(
        @{ url = "/api/projects"; name = "Projects list" },
        @{ url = "/api/tasks?limit=1"; name = "Tasks list" },
        @{ url = "/api/testcases?limit=1"; name = "TestCases list" },
        @{ url = "/api/articles?limit=1"; name = "Articles list" }
    )
    $endpointErrors = 0
    foreach ($ep in $endpoints) {
        try {
            $resp = Invoke-WebRequest -Uri "$BaseUrl$($ep.url)" `
                                      -Headers $headers `
                                      -TimeoutSec 10 -UseBasicParsing
            if ($resp.StatusCode -eq 200) {
                Write-Status "  $($ep.name): OK" "OK"
            } else {
                Write-Status "  $($ep.name): HTTP $($resp.StatusCode)" "WARN"
                $endpointErrors++
            }
        } catch {
            Write-Status "  $($ep.name): FAILED" "FAIL"
            $endpointErrors++
        }
    }
    if ($endpointErrors -eq 0) {
        Write-Status "API smoke tests: all OK" "OK"
    } else {
        Write-Status "API smoke tests: $endpointErrors failures" "FAIL"
        $errors++
    }
}

# ── Summary ───────────────────────────────────────────────────
Write-Status "════════════════════════════════════"
if ($errors -eq 0) {
    Write-Status "DEPLOY VERIFIED — all $checks checks passed" "OK"
    exit 0
} else {
    Write-Status "DEPLOY ISSUES — $errors/$checks checks failed" "FAIL"
    exit 1
}
