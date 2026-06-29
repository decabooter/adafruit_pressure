# Run from repo root: .\ingestion\start.ps1
#
# One-time setup:
#   1. Install Mosquitto:  winget install -e --id EclipseFoundation.Mosquitto
#   2. Create credentials: mosquitto_passwd -c ingestion\mosquitto.passwd iot_user
#   3. Install Python deps:
#        pip install -r ingestion\requirements.txt
#        pip install -r backend\requirements.txt
#   4. Set credentials for this session:
#        $env:MQTT_USER = 'iot_user'
#        $env:MQTT_PASS = 'your_password'

$ErrorActionPreference = 'Stop'

if (-not (Test-Path "ingestion\mosquitto.passwd")) {
    Write-Host ""
    Write-Host "ERROR: ingestion\mosquitto.passwd not found."
    Write-Host "Run: mosquitto_passwd -c ingestion\mosquitto.passwd iot_user"
    Write-Host ""
    exit 1
}

if (-not $env:MQTT_USER -or -not $env:MQTT_PASS) {
    Write-Host ""
    Write-Host "ERROR: MQTT credentials not set. Run:"
    Write-Host "  `$env:MQTT_USER = 'iot_user'"
    Write-Host "  `$env:MQTT_PASS = 'your_password'"
    Write-Host ""
    exit 1
}

Write-Host "Starting Mosquitto broker..."
$mosquitto = Start-Process -FilePath "mosquitto" `
    -ArgumentList "-c ingestion\mosquitto.conf" `
    -PassThru -WindowStyle Hidden

Write-Host "Starting FastAPI backend at http://localhost:8000 ..."
$uvicorn = Start-Process -FilePath "python" `
    -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000" `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "Starting subscriber (Ctrl+C to stop everything)..."
try {
    python -m ingestion.subscriber
} finally {
    Write-Host "Shutting down..."
    Stop-Process -Id $mosquitto.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $uvicorn.Id   -ErrorAction SilentlyContinue
}
