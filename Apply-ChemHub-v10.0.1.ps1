$ErrorActionPreference = "Stop"

Write-Host "ChemHub v10.0.1 missing local_hybrid_filter fix"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Backup = Join-Path $Root ("backup_before_v10_0_1_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

if (Test-Path ".\apps\api\app\local_hybrid_filter.py") {
  Copy-Item ".\apps\api\app\local_hybrid_filter.py" (Join-Path $Backup "local_hybrid_filter.py") -Force
}

Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force
Write-Host "Local file copied."

Write-Host "Checking local syntax..."
python -m py_compile ".\apps\api\app\local_hybrid_filter.py"

Write-Host "Copying into API container..."
docker cp ".\apps\api\app\local_hybrid_filter.py" "chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py"

Write-Host "Restarting API..."
docker compose restart api

Write-Host "Waiting for API..."
Start-Sleep -Seconds 5

Write-Host "Smoke test..."
docker compose exec -w /app api python -c "from app.local_hybrid_filter import build_hybrid_page_text; from app.extractor import extract_reactions_from_text; print('hybrid ok'); print([(r.equation,r.conditions,r.temperature) for r in extract_reactions_from_text('2Re2O7 + 3H2 -> t -> 2ReO2 + 3H2O')])"

Write-Host "Patch v10.0.1 installed."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
