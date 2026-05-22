$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.0 agent editor + templates + conditions safe patch"

$root = Get-Location
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v10_0_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

function BackupFile($path, $name) {
  if (Test-Path $path) { Copy-Item $path (Join-Path $backup $name) -Force }
}

BackupFile ".\apps\api\app\extractor.py" "extractor.py"
BackupFile ".\apps\api\app\processor.py" "processor.py"
BackupFile ".\apps\agent\src\main.jsx" "agent_main.jsx"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\agent\src\main.jsx" ".\apps\agent\src\main.jsx" -Force

Write-Host "Local files copied. Checking syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py"
Write-Host "Local Python syntax OK."

Write-Host "Copying files into running containers..."
docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py"
docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py"
docker cp ".\apps\agent\src\main.jsx" "chemhub_unified_product-agent-1:/app/src/main.jsx"

Write-Host "Restarting API and agent..."
docker compose restart api agent

$smoke = @'
from app.extractor import extract_reactions_from_text, canonical_equation

cases = [
    ("hydride", "2M + H2 -> 2MH (M = Li, Na, K)"),
    ("ca_hydride", "H2^0 + Ca^0 -> Ca+2H2-1"),
    ("conditions1", "2Re2O7 -> t -> 2ReO2 + 3H2O"),
    ("conditions2", "CH2(COOH)2 -> 140 o C, P4O10 -> C3O2 + 2H2O"),
    ("conditions3", "2Tl + S -> 300 o C, в токе H2 -> Tl2S"),
    ("template_al_ga", "2M + 6H2O -> 2M(OH)3 + 3H2 (M = Al, Ga)"),
    ("bad_ion", "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)"),
]
for name, text in cases:
    rs = extract_reactions_from_text(text)
    print(name, [(r.equation, r.temperature, r.conditions, r.catalysts) for r in rs])
print("canonical", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
'@
$smokeFile = Join-Path $root "chemhub_v10_0_smoke.py"
Set-Content -Path $smokeFile -Value $smoke -Encoding UTF8
docker cp $smokeFile "chemhub_unified_product-api-1:/tmp/chemhub_v10_0_smoke.py"

Start-Sleep -Seconds 2
Write-Host "Running smoke test inside API container..."
docker compose exec -w /app -T api python /tmp/chemhub_v10_0_smoke.py

Write-Host "Patch v10.0 installed."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
