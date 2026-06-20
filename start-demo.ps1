[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$McpPort = 8002,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$stateDir = Join-Path $root ".demo"
$statePath = Join-Path $stateDir "processes.json"

function Assert-PortFree([int]$Port, [string]$Role) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) {
        throw "$Role port $Port is already in use. Stop the existing service or pass another port."
    }
}

function Wait-Port([int]$Port, [int]$TimeoutSeconds = 20) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $pending = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            if ($pending.AsyncWaitHandle.WaitOne(300) -and $client.Connected) {
                $client.EndConnect($pending)
                return
            }
        } catch {
        } finally {
            $client.Dispose()
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Timed out waiting for port $Port."
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds = 25) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 1
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
        }
        Start-Sleep -Milliseconds 350
    }
    throw "Timed out waiting for $Url."
}

Assert-PortFree $BackendPort "Backend"
Assert-PortFree $McpPort "MCP"
Assert-PortFree $FrontendPort "Frontend"

$python = (Get-Command python.exe -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$vite = Join-Path $frontend "node_modules/vite/bin/vite.js"
if (-not (Test-Path -LiteralPath $vite)) {
    throw "Frontend dependencies are missing. Run npm install in the frontend directory first."
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
if (Test-Path -LiteralPath $statePath) {
    throw "A demo state file already exists. Run ./stop-demo.ps1 before starting again."
}

$env:MCP_SERVER_HOST = "127.0.0.1"
$env:MCP_SERVER_PORT = "$McpPort"
$env:MCP_SERVER_URL = "http://127.0.0.1:$McpPort/mcp"
$env:VITE_BACKEND_TARGET = "http://127.0.0.1:$BackendPort"
$started = @()

try {
    $mcp = Start-Process -FilePath $python -ArgumentList "-m", "app.mcp_server" `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $stateDir "mcp.out.log") `
        -RedirectStandardError (Join-Path $stateDir "mcp.err.log")
    $started += [pscustomobject]@{ role = "mcp"; process = $mcp }

    $api = Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $stateDir "backend.out.log") `
        -RedirectStandardError (Join-Path $stateDir "backend.err.log")
    $started += [pscustomobject]@{ role = "backend"; process = $api }

    $ui = Start-Process -FilePath $node -ArgumentList $vite, "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort" `
        -WorkingDirectory $frontend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $stateDir "frontend.out.log") `
        -RedirectStandardError (Join-Path $stateDir "frontend.err.log")
    $started += [pscustomobject]@{ role = "frontend"; process = $ui }

    Wait-Port $McpPort
    Wait-Http "http://127.0.0.1:$BackendPort/api/health"
    Wait-Http "http://127.0.0.1:$FrontendPort"

    $records = $started | ForEach-Object {
        [pscustomobject]@{
            role = $_.role
            pid = $_.process.Id
            start_time = $_.process.StartTime.ToUniversalTime().ToString("o")
        }
    }
    $records | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8

    Write-Host "Demo started successfully."
    Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
    Write-Host "Business API: http://127.0.0.1:$BackendPort"
    Write-Host "MCP endpoint: http://127.0.0.1:$McpPort/mcp"
    Write-Host "Run ./stop-demo.ps1 to stop all three processes."
} catch {
    for ($index = $started.Count - 1; $index -ge 0; $index--) {
        $item = $started[$index]
        if (-not $item.process.HasExited) {
            Stop-Process -Id $item.process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    throw
}
