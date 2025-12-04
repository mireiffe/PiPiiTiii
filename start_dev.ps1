param (
    [int]$BE_PORT = 8000,
    [int]$FE_PORT = 5173
)

$env:BACKEND_PORT = $BE_PORT
$env:VITE_API_PORT = $BE_PORT
$env:VITE_FE_PORT = $FE_PORT  # 필요 없다면 이 줄은 지워도 됨

Write-Host "Using Backend Port: $BE_PORT"
Write-Host "Using Frontend Port: $FE_PORT"

# Cleanup function
function Cleanup {
    Write-Host "Stopping processes..."

    if ($BACKEND_PID) {
        Stop-Process -Id $BACKEND_PID -Force -ErrorAction SilentlyContinue
    }

    if ($FRONTEND_PID) {
        Stop-Process -Id $FRONTEND_PID -Force -ErrorAction SilentlyContinue
    }

    exit
}

# Register exit handler
Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

Write-Host "Checking for existing processes..."

# Function to kill process using port
function Kill-Port {
    param($port)

    $processInfo = netstat -ano | Select-String ":$port " | Select-Object -First 1
    if ($processInfo) {
        $pid = ($processInfo -split "\s+")[-1]
        if ($pid -match '^\d+$') {
            Write-Host "Killing process on port $port (PID: $pid)..."
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
}

# Kill backend port
Kill-Port $BE_PORT

# Kill frontend port
Kill-Port $FE_PORT

# Check Python path
if (Test-Path ".venv/Scripts/python.exe") {
    $PYTHON = ".venv/Scripts/python.exe"
}
elseif (Test-Path ".venv/bin/python") {
    $PYTHON = ".venv/bin/python"
}
else {
    $PYTHON = "python"
}

Write-Host "Starting Backend on port $BE_PORT..."
Start-Process -FilePath $PYTHON -ArgumentList "backend/main.py" -PassThru |
    ForEach-Object { $BACKEND_PID = $_.Id }

Write-Host "Starting Frontend on port $FE_PORT..."
Set-Location frontend
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --port $FE_PORT" -PassThru |
    ForEach-Object { $FRONTEND_PID = $_.Id }
Set-Location ..

# Wait loop
while ($true) {
    Start-Sleep -Seconds 1
}
