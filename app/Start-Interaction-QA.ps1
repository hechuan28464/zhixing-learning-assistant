param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$RunName = 'interaction-20261103')
$ErrorActionPreference = 'Stop'
$qaProject = $PSScriptRoot
$qaRoot = Join-Path (Join-Path $qaProject '.qa') $RunName
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
foreach ($qaPort in @(5174,8766)) {
    if (Get-NetTCPConnection -LocalPort $qaPort -State Listen -ErrorAction SilentlyContinue) { throw "QA port $qaPort is already occupied; no existing service was stopped." }
}
$qaOldDb = $env:STUDY_DB_PATH
$qaOldTarget = $env:STUDY_API_TARGET
$qaOldCookie = $env:STUDY_AUTH_COOKIE
try {
    $env:STUDY_DB_PATH = Join-Path $qaRoot 'records.sqlite3'
    $env:STUDY_API_TARGET = 'http://127.0.0.1:8766'
    $env:STUDY_AUTH_COOKIE = 'zhixing_qa_' + $RunName
    $qaPython = Join-Path $qaProject '.venv\Scripts\python.exe'
    $qaVite = Join-Path $qaProject 'node_modules\vite\bin\vite.js'
    $qaBackend = Start-Process -FilePath $qaPython -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8766') -WorkingDirectory $qaProject -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $qaRoot 'backend.out.log') -RedirectStandardError (Join-Path $qaRoot 'backend.err.log')
    $qaFrontend = Start-Process -FilePath (Get-Command node).Source -ArgumentList @(('"'+$qaVite+'"'),'--host','127.0.0.1','--port','5174','--strictPort') -WorkingDirectory $qaProject -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $qaRoot 'frontend.out.log') -RedirectStandardError (Join-Path $qaRoot 'frontend.err.log')
    @{backend_pid=$qaBackend.Id;frontend_pid=$qaFrontend.Id;database=$env:STUDY_DB_PATH;frontend='http://127.0.0.1:5174';backend='http://127.0.0.1:8766'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qaRoot 'services.json') -Encoding utf8
} finally {
    $env:STUDY_DB_PATH = $qaOldDb
    $env:STUDY_API_TARGET = $qaOldTarget
    $env:STUDY_AUTH_COOKIE = $qaOldCookie
}
Write-Output 'Isolated interaction QA started: http://127.0.0.1:5174/'
