# Run both local development servers. Press Ctrl+C to stop the pair.
$ErrorActionPreference = 'Stop'
$ssRoot = Split-Path -Parent $PSScriptRoot
$ssPython = Join-Path $ssRoot 'backend/.venv/Scripts/python.exe'
$ssVite = Join-Path $ssRoot 'frontend/node_modules/vite/bin/vite.js'
if (!(Test-Path -LiteralPath $ssPython) -or !(Test-Path -LiteralPath $ssVite)) {
    throw 'Install the backend and frontend dependencies first. See README.md.'
}
$ssLogs = Join-Path $ssRoot 'artifacts'
New-Item -ItemType Directory -Path $ssLogs -Force | Out-Null
$ssBackendProcess = $null
$ssFrontendProcess = $null
try {
    $ssBackendProcess = Start-Process -FilePath $ssPython -ArgumentList @('-u', 'backend/run.py') -WorkingDirectory $ssRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ssLogs 'backend.out.log') -RedirectStandardError (Join-Path $ssLogs 'backend.err.log')
    $ssFrontendProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--strictPort') -WorkingDirectory (Join-Path $ssRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ssLogs 'frontend.out.log') -RedirectStandardError (Join-Path $ssLogs 'frontend.err.log')
    Write-Host 'Starting SheetSense at http://127.0.0.1:5173'
    Write-Host 'Logs: artifacts/backend.err.log and artifacts/frontend.out.log'
    Write-Host 'Press Ctrl+C in this terminal to stop both servers.'
    while ($true) {
        Start-Sleep -Seconds 1
        if ($ssBackendProcess.HasExited -or $ssFrontendProcess.HasExited) {
            throw 'A server stopped. Check artifacts/*.log for details; ports 5000 and 5173 must be available.'
        }
    }
} finally {
    foreach ($ssProcess in @($ssBackendProcess, $ssFrontendProcess)) {
        if ($null -ne $ssProcess -and !$ssProcess.HasExited) {
            Stop-Process -InputObject $ssProcess -ErrorAction SilentlyContinue
        }
    }
}
