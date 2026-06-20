[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$statePath = Join-Path $root ".demo/processes.json"
if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "No demo process state was found."
    exit 0
}

$records = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
$records = @($records)
for ($index = $records.Count - 1; $index -ge 0; $index--) {
    $record = $records[$index]
    $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if (-not $process) {
        continue
    }
    $expected = [DateTime]::Parse($record.start_time).ToUniversalTime()
    $actual = $process.StartTime.ToUniversalTime()
    if ([Math]::Abs(($actual - $expected).TotalSeconds) -gt 5) {
        Write-Warning "Skipped PID $($record.pid): it no longer matches the recorded $($record.role) process."
        continue
    }
    Stop-Process -Id $process.Id -Force
    Write-Host "Stopped $($record.role) (PID $($record.pid))."
}

Remove-Item -LiteralPath $statePath -Force
Write-Host "Demo stopped."
