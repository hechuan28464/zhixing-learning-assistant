$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'
$logRoot = Join-Path $projectRoot 'data\private\logs'
$env:STUDY_DB_PATH = Join-Path $projectRoot 'data\private\learning.sqlite3'
$env:STUDY_API_TARGET = 'http://127.0.0.1:8765'
$localRuntimePath = Join-Path $projectRoot 'data\private\local-runtime.json'
if (Test-Path -LiteralPath $localRuntimePath) {
    $localRuntime = Get-Content -LiteralPath $localRuntimePath -Raw | ConvertFrom-Json
    $env:STUDY_AI_ENABLED = if ($localRuntime.ai_enabled -eq $true) { '1' } else { '0' }
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Python environment is missing. Follow README setup first.' }
if (-not (Test-Path -LiteralPath $vitePath)) { throw 'Frontend dependencies are missing. Run npm install first.' }
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Read-LocalPage([string]$url) {
    try { return Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing } catch { return $null }
}

$backend = Read-LocalPage 'http://127.0.0.1:8765/api/health'
if ($backend) {
    $health = $backend.Content | ConvertFrom-Json
    if ($health.application -ne 'zhixing-learning-studio') { throw 'Port 8765 is occupied by another application.' }
} else {
    if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8765 is already occupied.' }
    Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'backend.out.log') -RedirectStandardError (Join-Path $logRoot 'backend.err.log') | Out-Null
}

$frontend = Read-LocalPage 'http://127.0.0.1:5173/'
if ($frontend) {
    if ($frontend.Content -notmatch 'zhixing-learning-studio') { throw 'Port 5173 is occupied by another application.' }
} else {
    if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 5173 is already occupied.' }
    $nodePath = (Get-Command node).Source
    Start-Process -FilePath $nodePath -ArgumentList @(('"' + $vitePath + '"'),'--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'frontend.out.log') -RedirectStandardError (Join-Path $logRoot 'frontend.err.log') | Out-Null
}

for ($attempt=0; $attempt -lt 15; $attempt++) {
    if ((Read-LocalPage 'http://127.0.0.1:8765/api/health') -and (Read-LocalPage 'http://127.0.0.1:5173/')) {
        Write-Host 'Ready: http://127.0.0.1:5173/'
        Write-Host 'API:   http://127.0.0.1:8765/docs'
        exit 0
    }
    Start-Sleep -Milliseconds 500
}
throw 'Services did not become ready. Check data/private/logs.'
