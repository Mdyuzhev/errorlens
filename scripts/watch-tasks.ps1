# ============================================================
# ErrorLens Task Watcher v8
#
# Stability detection:
#   - Don't launch agent immediately on Created/Changed
#   - Launch after STABLE_WAIT_SEC since LAST change
#   - Timer resets on each new Changed
#
# Cleanup:
#   - After agent finishes — plan + task-* moved to done/
#
# Startup:
#   - Does NOT auto-launch existing plans
#   - Only new plans (Created after watcher starts)
# ============================================================

$ProjectRoot    = Split-Path -Parent $PSScriptRoot
$TasksDir       = Join-Path $ProjectRoot ".claude\tasks"
$DoneDir        = Join-Path $ProjectRoot ".claude\tasks\done"
$LogFile        = Join-Path $ProjectRoot ".claude\tasks\watcher.log"
$claudeScript   = "C:\Users\Михаил\AppData\Roaming\npm\claude.ps1"
$STABLE_WAIT_MS = 5000    # wait 5 seconds of silence before launch

# ── Global variables ─────────────────────────────────────
$global:EL_Launched    = [System.Collections.Generic.HashSet[string]]::new()
$global:EL_LastChange  = @{}    # filename → datetime of last change
$global:EL_Timers      = @{}    # filename → Timer object
$global:EL_TasksDir    = $TasksDir
$global:EL_DoneDir     = $DoneDir
$global:EL_LogFile     = $LogFile
$global:EL_Claude      = $claudeScript
$global:EL_Root        = $ProjectRoot
$global:EL_StableMs    = $STABLE_WAIT_MS

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts    = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line  = "[$ts] [$Level] $Message"
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "TRIGGER" { "Cyan" }
        "SKIP"    { "DarkGray" }
        "OK"      { "Green" }
        "WAIT"    { "Yellow" }
        default   { "Gray" }
    }
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

if (-not (Test-Path $TasksDir)) { New-Item -ItemType Directory -Path $TasksDir | Out-Null }
if (-not (Test-Path $DoneDir))  { New-Item -ItemType Directory -Path $DoneDir  | Out-Null }

# Log rotation
if (Test-Path $LogFile) {
    $lines = Get-Content $LogFile -Encoding UTF8
    if ($lines.Count -gt 1000) {
        $lines | Select-Object -Last 500 | Set-Content $LogFile -Encoding UTF8
    }
}

Write-Log "═══════════════════════════════════════════════"
Write-Log "ErrorLens Task Watcher v8 started"
Write-Log "Stability wait: ${STABLE_WAIT_MS}ms"
Write-Log "Project: $ProjectRoot"
if (Test-Path $claudeScript) {
    Write-Log "claude: $claudeScript" -Level "OK"
} else {
    Write-Log "claude NOT FOUND: $claudeScript" -Level "ERROR"
}
Write-Log "═══════════════════════════════════════════════"

function Is-PlanDone { param([string]$n); return Test-Path (Join-Path $DoneDir $n) }

function Get-PwshPath {
    $candidates = @(
        "$env:ProgramFiles\PowerShell\7\pwsh.exe",
        "C:\Program Files\PowerShell\7\pwsh.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return "powershell.exe"
}

function Cleanup-PlanFiles {
    param([string]$PlanFileName)
    $src = Join-Path $global:EL_TasksDir $PlanFileName
    $dst = Join-Path $global:EL_DoneDir $PlanFileName
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Log "  Moved $PlanFileName -> done/" -Level "OK"
    }
    $taskFiles = Get-ChildItem -Path $global:EL_TasksDir -Filter "task-*.md" -File -ErrorAction SilentlyContinue
    foreach ($tf in $taskFiles) {
        $tdst = Join-Path $global:EL_DoneDir $tf.Name
        Move-Item -Path $tf.FullName -Destination $tdst -Force
        Write-Log "  Moved $($tf.Name) -> done/" -Level "OK"
    }
}

function Invoke-ClaudeAgentStable {
    param([string]$FileName)

    if (Is-PlanDone $FileName) {
        Write-Log "Skip $FileName — in done/" -Level "SKIP"
        return
    }
    if ($global:EL_Launched.Contains($FileName)) {
        Write-Log "Skip $FileName — already launched" -Level "SKIP"
        return
    }
    if (-not (Test-Path $global:EL_Claude)) {
        Write-Log "claude not found" -Level "ERROR"
        return
    }

    $global:EL_Launched.Add($FileName) | Out-Null
    Write-Log "▶ LAUNCHING: $FileName (file stable ${STABLE_WAIT_MS}ms)" -Level "TRIGGER"

    $pwshPath    = Get-PwshPath
    $launcherPath = Join-Path $env:TEMP "errorlens_agent_$($FileName -replace '[^a-zA-Z0-9]','_').ps1"
    $root        = $global:EL_Root
    $claude      = $global:EL_Claude
    $doneDir     = $global:EL_DoneDir
    $tasksDir    = $global:EL_TasksDir
    $logFile     = $global:EL_LogFile

    $launcherContent = @"
Set-Location '$root'
Write-Host "=== ErrorLens Agent: $FileName ===" -ForegroundColor Cyan
Write-Host ""

# Run the agent
& '$claude' "Read .claude/tasks/$FileName and execute as orchestrator"

Write-Host ""
Write-Host "=== Agent finished ===" -ForegroundColor Green

# Cleanup: move plan + task files to done/
`$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path '$logFile' -Value "[`$ts] [OK] Cleanup after $FileName" -Encoding UTF8

# Move plan
`$src = Join-Path '$tasksDir' '$FileName'
`$dst = Join-Path '$doneDir' '$FileName'
if (Test-Path `$src) {
    Move-Item -Path `$src -Destination `$dst -Force
    Write-Host "  Moved $FileName -> done/" -ForegroundColor DarkGray
}

# Move task-*.md files
`$taskFiles = Get-ChildItem -Path '$tasksDir' -Filter "task-*.md" -File -ErrorAction SilentlyContinue
foreach (`$tf in `$taskFiles) {
    `$tdst = Join-Path '$doneDir' `$tf.Name
    Move-Item -Path `$tf.FullName -Destination `$tdst -Force
    Write-Host "  Moved `$(`$tf.Name) -> done/" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Press Enter to close ===" -ForegroundColor DarkGray
Read-Host
"@

    Set-Content -Path $launcherPath -Value $launcherContent -Encoding UTF8

    try {
        Start-Process -FilePath $pwshPath `
                      -ArgumentList "-NoExit", "-File", $launcherPath `
                      -WindowStyle Normal
        Write-Log "Agent window opened: $FileName" -Level "OK"
    } catch {
        Write-Log "Start-Process error: $_" -Level "ERROR"
        $global:EL_Launched.Remove($FileName) | Out-Null
    }
}

# ── Stability check (called from timer) ──────────
$global:EL_PendingFiles = [System.Collections.Concurrent.ConcurrentDictionary[string, datetime]]::new()

function Schedule-LaunchAfterStable {
    param([string]$FileName)
    $now = Get-Date
    $global:EL_PendingFiles[$FileName] = $now
    Write-Log "Waiting for stability: $FileName (${STABLE_WAIT_MS}ms)" -Level "WAIT"
}

# ── FileSystemWatcher ─────────────────────────────────────────
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path         = $TasksDir
$watcher.Filter       = "PLAN-*.md"
$watcher.NotifyFilter = [System.IO.NotifyFilters]::FileName `
                      -bor [System.IO.NotifyFilters]::LastWrite
$watcher.EnableRaisingEvents = $true

$onCreated = Register-ObjectEvent -InputObject $watcher -EventName Created -Action {
    $fn = $Event.SourceEventArgs.Name
    if (Test-Path (Join-Path $global:EL_DoneDir $fn)) { return }
    if ($global:EL_Launched.Contains($fn)) { return }
    $global:EL_PendingFiles[$fn] = Get-Date
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $global:EL_LogFile -Value "[$ts] [WAIT] FSW:Created -> $fn — scheduling stability check" -Encoding UTF8
}

$onChanged = Register-ObjectEvent -InputObject $watcher -EventName Changed -Action {
    $fn = $Event.SourceEventArgs.Name
    if (Test-Path (Join-Path $global:EL_DoneDir $fn)) { return }
    if ($global:EL_Launched.Contains($fn)) { return }
    $global:EL_PendingFiles[$fn] = Get-Date
}

Write-Host ""
Write-Host "  Watcher v8 active. Stability: ${STABLE_WAIT_MS}ms. Ctrl+C to stop." -ForegroundColor Green
Write-Host "  Existing plans are NOT auto-launched (new files only)." -ForegroundColor DarkGray
Write-Host ""

# Show existing plans without launching
$existing = Get-ChildItem -Path $TasksDir -Filter "PLAN-*.md" -File -ErrorAction SilentlyContinue
if ($existing) {
    Write-Log "Existing plans (not auto-launched):"
    foreach ($f in $existing) {
        if (Is-PlanDone $f.Name) {
            Write-Log "  $($f.Name) — done" -Level "SKIP"
        } else {
            Write-Log "  $($f.Name) — awaiting manual launch" -Level "INFO"
        }
    }
}

# ── Main polling loop ─────────────────────────────────────────
try {
    while ($true) {
        Start-Sleep -Milliseconds 500

        # Check pending files for stability
        foreach ($kvp in @($global:EL_PendingFiles.GetEnumerator())) {
            $fn = $kvp.Key
            $lastChange = $kvp.Value
            $elapsed = (Get-Date) - $lastChange

            if ($elapsed.TotalMilliseconds -ge $global:EL_StableMs) {
                # Remove from pending
                [void]$global:EL_PendingFiles.TryRemove($fn, [ref]$null)

                # Final checks
                if (Is-PlanDone $fn) { continue }
                if ($global:EL_Launched.Contains($fn)) { continue }
                if (-not (Test-Path (Join-Path $TasksDir $fn))) { continue }

                # Launch!
                Invoke-ClaudeAgentStable -FileName $fn
            }
        }
    }
} finally {
    Unregister-Event -SourceIdentifier $onCreated.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $onChanged.Name -ErrorAction SilentlyContinue
    $watcher.Dispose()
    Write-Log "Watcher stopped"
}
