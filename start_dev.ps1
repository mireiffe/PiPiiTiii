# Kill existing processes
Write-Host "Checking for existing processes..."

# Kill processes on port 8000 (Backend)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "Killing process on port 8000..."
    $processId = $port8000.OwningProcess
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Kill processes on port 5173 (Frontend - Vite default)
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "Killing process on port 5173..."
    $processId = $port5173.OwningProcess
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Start Backend
Write-Host "Starting Backend..."
$backendCmd = "python backend/main.py"
if (Test-Path ".venv\Scripts\python.exe") {
    $backendCmd = ".venv\Scripts\python.exe backend/main.py"
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$backendCmd"

# Start Frontend
Write-Host "Starting Frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
