$ErrorActionPreference = "Stop"

Write-Host "ChemHub v10.9 strict oxidation removal + exact visual arrow conditions patch"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $Root "backup_before_v10_9_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

function Backup-File($path, $name) {
  if (Test-Path $path) {
    Copy-Item $path (Join-Path $backup $name) -Force
  }
}

Backup-File ".\apps\api\app\extractor.py" "apps_api_app_extractor.py"
Backup-File ".\apps\api\app\processor.py" "apps_api_app_processor.py"
Backup-File ".\apps\api\app\local_hybrid_filter.py" "apps_api_app_local_hybrid_filter.py"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force

Write-Host "Local API files copied. Backup: $backup"
Write-Host "Checking local Python syntax..."

$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
  python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"
  Write-Host "Local syntax OK."
} else {
  Write-Host "Python not found locally, skipping local syntax check."
}

Write-Host "Copying files into running API container..."
docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py"
docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py"
docker cp ".\apps\api\app\local_hybrid_filter.py" "chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py"

Write-Host "Restarting API..."
docker compose restart api

$smoke = @'
from app.extractor import extract_reactions_from_text

tests = [
    ("oxidation", "H2^0 + S -> H2+1S", [("H2 + S → H2S", "", "")]),
    ("visual_condition_separate", "300° C, в токе H2\n2Tl + S -> Tl2S", [("2Tl + S → Tl2S", "300 °C, в токе H2", "300 °C")]),
    ("visual_condition_inline", "2Tl + S -> 300° C, в токе H2 -> Tl2S", [("2Tl + S → Tl2S", "300 °C, в токе H2", "300 °C")]),
    ("no_condition", "2Tl + S -> Tl2S", [("2Tl + S → Tl2S", "", "")]),
    ("concentration_inside", "HNO3 конц. + Cu -> Cu(NO3)2 + NO2", [("HNO3 конц. + Cu → Cu(NO3)2 + NO2", "", "")]),
    ("p4o10_condition", "CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O", [("CH2(COOH)2 → C3O2 + 2H2O", "140 °C, P4O10", "140 °C")]),
    ("template_x", "2K + Cl2 -> 2KX X = Cl", [("2K + Cl2 → 2KCl", "", "")]),
    ("template_m", "M2O + H2O -> 2MOH M = Li, Na, K", [("Li2O + H2O → 2LiOH", "", ""), ("Na2O + H2O → 2NaOH", "", ""), ("K2O + H2O → 2KOH", "", "")]),
    ("bad_constant", "SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0,6)", [("SnCl4 + 2HCl → H2SnCl6", "", "")]),
    ("lg_noise", "(lg(B)=11,2)", []),
]

ok = True
for name, text, expected in tests:
    got = [(r.equation, r.conditions, r.temperature) for r in extract_reactions_from_text(text)]
    print(name, "=>", got)
    if got != expected:
        print("EXPECTED:", expected)
        ok = False
if not ok:
    raise SystemExit(1)
print("SMOKE_OK")
'@

$smokePath = Join-Path $Root "chemhub_v10_9_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8

Write-Host "Running smoke tests inside API container..."
docker cp $smokePath "chemhub_unified_product-api-1:/tmp/chemhub_v10_9_smoke.py"
docker compose exec -w /app api python /tmp/chemhub_v10_9_smoke.py

Write-Host "Patch v10.9 installed. Open AI Agent and press Ctrl+F5: http://localhost:5173"
