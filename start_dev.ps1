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
