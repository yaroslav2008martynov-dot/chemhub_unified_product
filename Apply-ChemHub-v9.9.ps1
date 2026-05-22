
param(
    [switch]$NoDocker
)

$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.9 final stable chemistry-aware agent patch"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v9_9_$Stamp"
New-Item -ItemType Directory -Path $Backup -Force | Out-Null

function Backup-File($src, $name) {
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Backup $name) -Force
    }
}

Backup-File ".\apps\api\app\extractor.py" "_apps_api_app_extractor.py"
Backup-File ".\apps\api\app\processor.py" "_apps_api_app_processor.py"

Write-Host "Backup created: $Backup"

if (!(Test-Path ".\patch_files\apps\api\app\extractor.py")) {
    throw "Patch file not found: patch_files\apps\api\app\extractor.py"
}
if (!(Test-Path ".\patch_files\apps\api\app\processor.py")) {
    throw "Patch file not found: patch_files\apps\api\app\processor.py"
}

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Write-Host "Local API files copied."

Write-Host "Checking local Python syntax..."
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    python -m py_compile ".\apps\api\app\extractor.py"
    python -m py_compile ".\apps\api\app\processor.py"
    Write-Host "Local syntax OK."
} else {
    Write-Host "Python not found locally, skipping local syntax check."
}

if (-not $NoDocker) {
    Write-Host "Copying files into running API container..."
    docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py"
    docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py"

    Write-Host "Restarting API..."
    docker compose restart api

    if (Test-Path ".\chemhub_v9_9_smoke.py") {
        Write-Host "Running smoke test inside API container..."
        docker cp ".\chemhub_v9_9_smoke.py" "chemhub_unified_product-api-1:/tmp/chemhub_v9_9_smoke.py"
        Start-Sleep -Seconds 3
        docker compose exec -T api sh -c "cd /app && python /tmp/chemhub_v9_9_smoke.py"
    }
}

Write-Host "Patch v9.9 installed successfully."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
Write-Host "Open site and press Ctrl+F5: http://localhost:3000"
