$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.2 UTF-8 stable extractor + editor patch"

$root = (Get-Location).Path
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v10_2_$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null

function Backup-File($path, $name) {
  if (Test-Path $path) { Copy-Item $path (Join-Path $backup $name) -Force }
}
Backup-File ".\apps\api\app\extractor.py" "extractor.py"
Backup-File ".\apps\api\app\processor.py" "processor.py"
Backup-File ".\apps\api\app\local_hybrid_filter.py" "local_hybrid_filter.py"
Backup-File ".\apps\agent\src\main.jsx" "agent_main.jsx"
Backup-File ".\apps\agent\src\styles.css" "agent_styles.css"
Backup-File ".\apps\site\src\main.jsx" "site_main.jsx"

Write-Host "Backup created: $backup"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\local_hybrid_filter.py" ".\apps\api\app\local_hybrid_filter.py" -Force
Copy-Item ".\patch_files\apps\agent\src\main.jsx" ".\apps\agent\src\main.jsx" -Force
Copy-Item ".\patch_files\apps\site\src\main.jsx" ".\apps\site\src\main.jsx" -Force

if (Test-Path ".\patch_files\apps\agent\src\styles.v10.2.add.css") {
  $cssAdd = Get-Content ".\patch_files\apps\agent\src\styles.v10.2.add.css" -Raw -Encoding UTF8
  $cssPath = ".\apps\agent\src\styles.css"
  if (Test-Path $cssPath) {
    $css = Get-Content $cssPath -Raw -Encoding UTF8
    if ($css -notlike "*Minimal additions for v10.2*") {
      Add-Content $cssPath "`n$cssAdd" -Encoding UTF8
    }
  }
}

Write-Host "Local files copied."

Write-Host "Checking local Python syntax..."
python -m py_compile ".\apps\api\app\extractor.py" ".\apps\api\app\processor.py" ".\apps\api\app\local_hybrid_filter.py"
Write-Host "Local Python syntax OK."

Write-Host "Copying files into containers..."
docker cp ".\apps\api\app\extractor.py" chemhub_unified_product-api-1:/app/app/extractor.py
docker cp ".\apps\api\app\processor.py" chemhub_unified_product-api-1:/app/app/processor.py
docker cp ".\apps\api\app\local_hybrid_filter.py" chemhub_unified_product-api-1:/app/app/local_hybrid_filter.py
docker cp ".\apps\agent\src\main.jsx" chemhub_unified_product-agent-1:/app/src/main.jsx
docker cp ".\apps\agent\src\styles.css" chemhub_unified_product-agent-1:/app/src/styles.css
docker cp ".\apps\site\src\main.jsx" chemhub_unified_product-site-1:/app/src/main.jsx

Write-Host "Restarting api, agent, site..."
docker compose restart api agent site
Start-Sleep -Seconds 3

$smoke = @'
from app.extractor import extract_reactions_from_text, canonical_equation

cases = {
    "M hydrides": "2M + H2 -> 2MH (M = Li, Na, K)",
    "X chloride": "2K + Cl2 -> 2KX (X = Cl)",
    "Li oxidation": "H2 + 2Li0 -> 2Li + 1H-1",
    "Ca oxidation": "H2^0 + Ca^0 -> Ca+2H2-1",
    "conditions": "2Tl + S -> 300 °C, в токе H2 -> Tl2S",
    "pKa reject": "H3BO3 + H2O -> H + + [B(OH)4] - (pKa = 9,2)",
    "cathode reject": "катод: Mg2+ + 2e- -> Mg",
}
for name, text in cases.items():
    rs = extract_reactions_from_text(text)
    print(name, "=>", [(r.equation, r.conditions, r.temperature, r.reaction_name) for r in rs])
'@
$smokePath = Join-Path $root "chemhub_v10_2_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker cp $smokePath chemhub_unified_product-api-1:/tmp/chemhub_v10_2_smoke.py

Write-Host "Running smoke test inside API container..."
docker compose exec -T -w /app api python /tmp/chemhub_v10_2_smoke.py

Write-Host "Patch v10.2 installed."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
Write-Host "Open site and press Ctrl+F5: http://localhost:3000"
