$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.8 exact visual arrow-conditions patch"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v10_8_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

$files = @(
  "apps\api\app\extractor.py",
  "apps\api\app\processor.py",
  "apps\api\app\local_hybrid_filter.py"
)

foreach ($f in $files) {
  if (Test-Path $f) {
    Copy-Item $f (Join-Path $backup ($f -replace "\\","_")) -Force
  }
}

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force

Write-Host "Local API files copied. Backup: $backup"
Write-Host "Checking local Python syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"
Write-Host "Local syntax OK."

Write-Host "Copying files into running API container..."
docker cp ".\apps\api\app\extractor.py" chemhub_unified_product-api-1:/app/app/extractor.py
docker cp ".\apps\api\app\processor.py" chemhub_unified_product-api-1:/app/app/processor.py
docker cp ".\apps\api\app\local_hybrid_filter.py" chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py

Write-Host "Restarting API..."
docker compose restart api

$smoke = @'
from app.extractor import extract_reactions_from_text
tests = [
    ("no_condition", "2Tl + S -> Tl2S"),
    ("arrow_condition", "CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O"),
    ("any_arrow_condition", "A + B -> SO2 ж, -80 °C -> C + D"),
    ("concentration_inside", "3Cu + 8HNO3 разб. -> 3Cu(NO3)2 + 2NO + 4H2O"),
    ("template_m", "M2O + H2O -> 2MOH M = Li, Na, K"),
    ("template_x", "2K + Cl2 -> 2KX X = Cl"),
    ("bad_meta", "SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0.6)"),
]
for name, text in tests:
    rows = extract_reactions_from_text(text)
    print(name, [(r.equation, r.conditions) for r in rows])
assert extract_reactions_from_text("2Tl + S -> Tl2S")[0].conditions == ""
assert extract_reactions_from_text("CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O")[0].conditions == "140 °C, P4O10"
assert "разб." in extract_reactions_from_text("3Cu + 8HNO3 разб. -> 3Cu(NO3)2 + 2NO + 4H2O")[0].equation
assert extract_reactions_from_text("3Cu + 8HNO3 разб. -> 3Cu(NO3)2 + 2NO + 4H2O")[0].conditions == ""
assert not extract_reactions_from_text("SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0.6)")
'@

$smokePath = Join-Path $root "chemhub_v10_8_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker cp $smokePath chemhub_unified_product-api-1:/tmp/chemhub_v10_8_smoke.py

Write-Host "Running smoke tests inside API container..."
docker compose exec -w /app api python /tmp/chemhub_v10_8_smoke.py

Write-Host "Patch v10.8 installed. Open AI Agent and press Ctrl+F5: http://localhost:5173"
