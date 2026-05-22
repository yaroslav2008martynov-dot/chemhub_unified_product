$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.6 precise arrow conditions + no generic templates patch"

$root = (Get-Location).Path
$backup = Join-Path $root ("backup_before_v10_6_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $backup | Out-Null

function Backup-IfExists($path, $name) {
  if (Test-Path $path) {
    Copy-Item $path (Join-Path $backup $name) -Force
  }
}

Backup-IfExists ".\apps\api\app\extractor.py" "apps_api_app_extractor.py"
Backup-IfExists ".\apps\api\app\processor.py" "apps_api_app_processor.py"
Backup-IfExists ".\apps\api\app\local_hybrid_filter.py" "apps_api_app_local_hybrid_filter.py"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force
Write-Host "Local API files copied. Backup: $backup"

Write-Host "Checking local Python syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"
Write-Host "Local syntax OK."

Write-Host "Copying files into running API container..."
docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py"
docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py"
docker cp ".\apps\api\app\local_hybrid_filter.py" "chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py"

Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 5

$test = @'
from app.extractor import extract_reactions_from_text

cases = {
    "alkali_hydrides": "2M + H2 -> 2MH M = Li, Na, K",
    "alkali_oxides": "M2O + H2O -> 2MOH M = Li, Na, K",
    "halide_product": "2K + Cl2 -> 2KX X = Cl",
    "inline_condition": "CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O",
    "condition_above": "300 °C, в токе H2\n2Tl + S -> Tl2S",
    "no_condition": "2Na + 2H2O -> 2NaOH + H2",
    "bad_pka": "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)",
}

for name, text in cases.items():
    rows = [(r.equation, r.conditions, r.temperature) for r in extract_reactions_from_text(text)]
    print(name, rows)
    if name == "alkali_hydrides":
        assert ("2Li + H2 → 2LiH", "", "") in rows
        assert ("2Na + H2 → 2NaH", "", "") in rows
        assert not any("M" in x[0] or "=" in x[0] for x in rows)
    if name == "alkali_oxides":
        assert ("Li2O + H2O → 2LiOH", "", "") in rows
        assert not any("M" in x[0] or "=" in x[0] for x in rows)
    if name == "halide_product":
        assert rows == [("2K + Cl2 → 2KCl", "", "")]
    if name == "inline_condition":
        assert rows == [("CH2(COOH)2 → C3O2 + 2H2O", "140 °C, P4O10", "")]
    if name == "condition_above":
        assert rows == [("2Tl + S → Tl2S", "300 °C, в токе H2", "")]
    if name == "no_condition":
        assert rows == [("2Na + 2H2O → 2NaOH + H2", "", "")]
    if name == "bad_pka":
        assert rows == []

print("CHEMHUB_V10_6_SMOKE_OK")
'@

$testPath = ".\chemhub_v10_6_smoke.py"
Set-Content -Path $testPath -Value $test -Encoding UTF8
docker cp $testPath "chemhub_unified_product-api-1:/tmp/chemhub_v10_6_smoke.py"
Write-Host "Running smoke tests inside API container..."
docker compose exec -w /app -T api python /tmp/chemhub_v10_6_smoke.py

Write-Host "Patch v10.6 installed. Open AI Agent and press Ctrl+F5: http://localhost:5173"
