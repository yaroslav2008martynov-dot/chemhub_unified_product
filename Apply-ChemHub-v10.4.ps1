$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.4 conditions-over-arrow UTF-8 patch"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $Root "backup_before_v10_4_$stamp"
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

Write-Host "Checking local Python syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"

Write-Host "Copying into API container..."
docker cp ".\apps\api\app\extractor.py" chemhub_unified_product-api-1:/app/app/extractor.py
docker cp ".\apps\api\app\processor.py" chemhub_unified_product-api-1:/app/app/processor.py
docker cp ".\apps\api\app\local_hybrid_filter.py" chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py

Write-Host "Restarting API..."
docker compose restart api

Start-Sleep -Seconds 3

$smoke = @'
from app.extractor import extract_reactions_from_text
tests = {
    "arrow_condition": "140 °C, P4O10\nCH2(COOH)2 -> C3O2 + 2H2O",
    "between_arrows": "2Tl + S -> 300 °C, в токе H2 -> Tl2S",
    "template_x": "2K + Cl2 -> 2KX (X = Cl)",
    "template_m": "2M + H2 -> 2MH (M = Li, Na, K)",
    "pka_reject": "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)",
}
for name, text in tests.items():
    rs = extract_reactions_from_text(text)
    print(name, [(r.equation, r.conditions, r.temperature) for r in rs])
'@
$smokePath = Join-Path $env:TEMP "chemhub_v10_4_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker cp $smokePath chemhub_unified_product-api-1:/tmp/chemhub_v10_4_smoke.py
docker compose exec -w /app api python /tmp/chemhub_v10_4_smoke.py

Write-Host "Patch v10.4 installed. Open AI Agent and press Ctrl+F5."