$ErrorActionPreference = 'Stop'
Write-Host 'ChemHub live PDF progress patch'

if (!(Test-Path '.\docker-compose.yml')) {
  Write-Host 'ERROR: run this script from C:\chemhub_unified_product' -ForegroundColor Red
  exit 1
}
if (!(Test-Path '.\patch_files\apps\api\app\processor.py')) {
  Write-Host 'ERROR: patch_files not found. Extract the ZIP into project root first.' -ForegroundColor Red
  exit 1
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = ".\backup_before_live_patch_$stamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir\apps\api\app" | Out-Null
New-Item -ItemType Directory -Force -Path "$backupDir\apps\agent\src" | Out-Null

if (Test-Path '.\apps\api\app\processor.py') { Copy-Item '.\apps\api\app\processor.py' "$backupDir\apps\api\app\processor.py" -Force }
if (Test-Path '.\apps\agent\src\main.jsx') { Copy-Item '.\apps\agent\src\main.jsx' "$backupDir\apps\agent\src\main.jsx" -Force }

Write-Host '[1/4] Copying files to local project...'
Copy-Item '.\patch_files\apps\api\app\processor.py' '.\apps\api\app\processor.py' -Force
Copy-Item '.\patch_files\apps\agent\src\main.jsx' '.\apps\agent\src\main.jsx' -Force

Write-Host '[2/4] Copying files into running containers...'
$apiId = docker compose ps -q api
$agentId = docker compose ps -q agent
if ($apiId) { docker cp '.\apps\api\app\processor.py' "$apiId`:/app/app/processor.py" }
if ($agentId) { docker cp '.\apps\agent\src\main.jsx' "$agentId`:/app/src/main.jsx" }

Write-Host '[3/4] Restarting API and agent...'
docker compose restart api agent

Write-Host '[4/4] Checking services...'
docker compose ps

Write-Host ''
Write-Host 'Patch installed. Open AI Agent and press Ctrl+F5:'
Write-Host 'http://localhost:5173'
Write-Host ''
Write-Host 'Now reactions should appear while PDF is still processing.'
