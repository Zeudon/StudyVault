# StudyVault Quick Start Script
# This script starts both the frontend and backend servers

Write-Host "Starting StudyVault Application..." -ForegroundColor Green

# Check if Python virtual environment exists
$venvPath = "C:/Nived/Nived Personal/Academia/StudyVault/.venv/Scripts/python.exe"
if (-not (Test-Path $venvPath)) {
    Write-Host "Error: Python virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host "Please set up the virtual environment first." -ForegroundColor Yellow
    exit 1
}

# Start Backend Server
Write-Host "`nStarting Backend Server..." -ForegroundColor Cyan
$backendPath = "c:\Nived\Nived Personal\Academia\StudyVault\code\webapp\backend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; Write-Host 'Backend Server' -ForegroundColor Green; & '$venvPath' -m uvicorn main:app --host 0.0.0.0 --port 8000" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Frontend Server
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
$frontendPath = "c:\Nived\Nived Personal\Academia\StudyVault\code\webapp\frontend"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; Write-Host 'Frontend Server' -ForegroundColor Green; npm run dev" -WindowStyle Normal

Start-Sleep -Seconds 5

Write-Host "`n✅ Both servers are starting!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "`nPress Ctrl+C in each window to stop the servers." -ForegroundColor Gray
