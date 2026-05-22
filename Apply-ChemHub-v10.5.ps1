$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.5 conditions + generalized templates safe patch"
$Root = Get-Location
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v10_5_$Stamp"
New-Item -ItemType Directory -Path $Backup -Force | Out-Null

function Backup-File($Path, $Name) {
  if (Test-Path $Path) { Copy-Item $Path (Join-Path $Backup $Name) -Force }
}

Backup-File ".\apps\api\app\extractor.py" "extractor.py"
Backup-File ".\apps\api\app\processor.py" "processor.py"
Backup-File ".\apps\api\app\local_hybrid_filter.py" "local_hybrid_filter.py"
Write-Host "Backup created: $Backup"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force
Write-Host "Local API files copied."

Write-Host "Checking local Python syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"
Write-Host "Local Python syntax OK."

Write-Host "Copying files into running API container..."
docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py"
docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py"
docker cp ".\apps\api\app\local_hybrid_filter.py" "chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py"

Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 3

Write-Host "Running smoke tests inside API container..."
docker cp ".\chemhub_v10_5_smoke.py" "chemhub_unified_product-api-1:/tmp/chemhub_v10_5_smoke.py"
docker compose exec -w /app -T api python /tmp/chemhub_v10_5_smoke.py

Write-Host "Patch v10.5 installed successfully."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
