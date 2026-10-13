<#
Resets the demo to a clean state: stops any running uvicorn on port 8000, deletes the SQLite
file so alerts/readings/audit log are wiped, and reminds you to restart the backend
(regions and demo users are auto-reseeded on startup — see backend/app/main.py lifespan()).
#>
param(
    [string]$DbPath = "backend\ewsa.db"
)

$proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($proc) {
    Write-Host "Stopping process on port 8000 (PID $proc)..."
    Stop-Process -Id $proc -Force
    Start-Sleep -Seconds 1
}

if (Test-Path $DbPath) {
    Remove-Item $DbPath -Force
    Write-Host "Deleted $DbPath"
} else {
    Write-Host "No existing db at $DbPath (nothing to delete)"
}

Write-Host "Demo state reset. Restart the backend now:"
Write-Host "  cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:create_app --factory --reload --port 8000"