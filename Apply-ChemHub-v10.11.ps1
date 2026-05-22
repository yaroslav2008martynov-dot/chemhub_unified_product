$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.11 strict oxidation OCR + visual conditions pipeline patch"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $Root "backup_before_v10_11_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null

$files = @(
  @{src="apps\api\app\extractor.py"; patch="patch_files\apps\api\app\extractor.py"; container="chemhub_unified_product-api-1:/app/app/extractor.py"},
  @{src="apps\api\app\processor.py"; patch="patch_files\apps\api\app\processor.py"; container="chemhub_unified_product-api-1:/app/app/processor.py"},
  @{src="apps\api\app\local_hybrid_filter.py"; patch="patch_files\apps\api\app\local_hybrid_filter.py"; container="chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py"}
)

foreach ($f in $files) {
  if (Test-Path $f.src) {
    $safe = ($f.src -replace '[\\/]', '_')
    Copy-Item $f.src (Join-Path $backup $safe) -Force
  }
}
Write-Host "Backup created: $backup"

foreach ($f in $files) {
  $dir = Split-Path $f.src -Parent
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
  Copy-Item $f.patch $f.src -Force
}
Write-Host "Local API files copied."

Write-Host "Checking local Python syntax..."
python -m py_compile .\apps\api\app\extractor.py .\apps\api\app\processor.py .\apps\api\app\local_hybrid_filter.py
Write-Host "Local syntax OK."

Write-Host "Copying files into running API container..."
foreach ($f in $files) {
  docker cp $f.src $f.container
}

Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 4

$smoke = @'
from app.extractor import extract_reactions_from_text
cases = [
    ("2H20 + O2 -> 2H2O", "2H2 + O2 → 2H2O"),
    ("2H2^0 + O2^0 -> 2H2O", "2H2 + O2 → 2H2O"),
    ("2H2O + O2 -> 2H2O", "2H2 + O2 → 2H2O"),
    ("H2O + S -> H2S", "H2 + S → H2S"),
    ("H2O + CuO -> Cu + H2O", "H2 + CuO → Cu + H2O"),
    ("H2O + Ca -> CaH2", "H2 + Ca → CaH2"),
    ("2K + Cl2 -> 2KX X = Cl", "2K + Cl2 → 2KCl"),
]
for text, expected in cases:
    got = [r.equation for r in extract_reactions_from_text(text)]
    print(text, "=>", got)
    assert expected in got, (text, expected, got)
r = extract_reactions_from_text("300 °C, в токе H2\n2Tl + S -> Tl2S")[0]
print("condition test =>", r.equation, r.conditions)
assert r.equation == "2Tl + S → Tl2S"
assert r.conditions == "300 °C, в токе H2"
r = extract_reactions_from_text("HNO3 конц. + Cu -> Cu(NO3)2 + NO2")[0]
assert r.conditions == "" and "конц." in r.equation
r = extract_reactions_from_text("SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0,6)")[0]
assert "pKa" not in r.equation and r.conditions == ""
print("CHEMHUB_V10_11_SMOKE_OK")
'@
$smokePath = Join-Path $Root "chemhub_v10_11_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8

docker cp $smokePath chemhub_unified_product-api-1:/tmp/chemhub_v10_11_smoke.py
Write-Host "Running smoke tests inside API container..."
docker compose exec -T -w /app api python /tmp/chemhub_v10_11_smoke.py

Write-Host "Patch v10.11 installed successfully."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
