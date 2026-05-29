# Stop any process on port 8001, then start the API
$port = 8001
$connections = netstat -ano | Select-String ":$port\s+.*LISTENING"
foreach ($line in $connections) {
    $procId = ($line -split '\s+')[-1]
    if ($procId -match '^\d+$') {
        Write-Host "Stopping process $procId on port $port..."
        taskkill /PID $procId /F 2>$null
    }
}
Set-Location "$PSScriptRoot\..\backend"
& "..\.venv\Scripts\python.exe" api.py
