$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.8.1 strict oxidation layer patch"
$root = Get-Location
$backup = Join-Path $root ("backup_before_v9_8_1_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item .\apps\api\app\extractor.py $backup\extractor.py -ErrorAction SilentlyContinue

Copy-Item .\patch_files\apps\api\app\strict_oxidation_layer.py .\apps\api\app\strict_oxidation_layer.py -Force

$extractor = ".\apps\api\app\extractor.py"
$content = Get-Content $extractor -Raw -Encoding UTF8
if ($content -notmatch "strict_oxidation_layer") {
@'

# ChemHub v9.8.1 strict oxidation layer
try:
    from app.strict_oxidation_layer import patch_extractor_module as _chemhub_patch_strict_oxidation
    import sys as _chemhub_sys
    _chemhub_patch_strict_oxidation(_chemhub_sys.modules[__name__])
except Exception as _chemhub_ox_exc:
    print("CHEMHUB_STRICT_OXIDATION_LAYER_DISABLED", _chemhub_ox_exc)
'@ | Add-Content $extractor -Encoding UTF8
}

Write-Host "Copying into API container..."
docker compose cp .\apps\api\app\strict_oxidation_layer.py api:/app/app/strict_oxidation_layer.py
docker compose cp .\apps\api\app\extractor.py api:/app/app/extractor.py
Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 3
Write-Host "Smoke tests..."
docker compose exec -T api python -c "from app.extractor import extract_reactions_from_text; tests=['H2^0 + Ca^0 -> Ca+2H2-1','H2 + 2Li0 -> 2Li + 1H-1','S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3']; [print([(r.equation,r.temperature,r.conditions) for r in extract_reactions_from_text(t)]) for t in tests]"
Write-Host "Patch v9.8.1 installed. Press Ctrl+F5 in browser and upload a NEW PDF."
