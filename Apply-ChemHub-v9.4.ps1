param()

$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.4 extractor + site rendering safe patch" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v9_4_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $backup "apps_api_app") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $backup "apps_site_src") -Force | Out-Null

if (Test-Path ".\apps\api\app\extractor.py") { Copy-Item ".\apps\api\app\extractor.py" (Join-Path $backup "apps_api_app\extractor.py") -Force }
if (Test-Path ".\apps\site\src\main.jsx") { Copy-Item ".\apps\site\src\main.jsx" (Join-Path $backup "apps_site_src\main.jsx") -Force }
if (Test-Path ".\apps\site\src\styles.css") { Copy-Item ".\apps\site\src\styles.css" (Join-Path $backup "apps_site_src\styles.css") -Force }
Write-Host "Backup created: $backup"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\site\src\main.jsx" ".\apps\site\src\main.jsx" -Force
Copy-Item ".\patch_files\apps\site\src\styles.css" ".\apps\site\src\styles.css" -Force

Write-Host "Running local syntax check..."
if (Get-Command python -ErrorAction SilentlyContinue) {
  python -m py_compile ".\apps\api\app\extractor.py"
}

Write-Host "Applying safe DB cleanup..."
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "UPDATE reactions SET hidden = TRUE WHERE equation ILIKE '%pKa%' OR equation ILIKE '%pKb%' OR equation ILIKE '%pK%' OR equation ILIKE '%ПР%' OR equation ILIKE '%катод%' OR equation ILIKE '%анод%' OR equation ILIKE '%ē%' OR equation ILIKE '% e-%' OR equation ILIKE '%H +%' OR equation ILIKE '%Cl-%';" | Out-Host

Write-Host "Copying files into running containers..."
docker compose cp ".\apps\api\app\extractor.py" "api:/app/app/extractor.py" | Out-Host
docker compose cp ".\apps\site\src\main.jsx" "site:/app/src/main.jsx" | Out-Host
docker compose cp ".\apps\site\src\styles.css" "site:/app/src/styles.css" | Out-Host

Write-Host "Restarting API and site..."
docker compose restart api site | Out-Host
Start-Sleep -Seconds 4

$smoke = @'
from app.extractor import extract_reactions_from_text, canonical_equation
cases = [
    "H20 + S -> H2+1S",
    "4CuSO4 + H3PO2 + H2O -> 4CuH + H3PO4 + H2SO4",
    "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)",
    "2Tl + Cl2 120-150 C -> 2TlCl",
    "S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3",
]
for c in cases:
    rs = extract_reactions_from_text(c)
    print("CASE", c)
    print([(r.equation, r.temperature, r.conditions, r.catalysts, r.reaction_name) for r in rs])
print("CANON", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
'@
$smokePath = Join-Path $root "chemhub_v9_4_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker compose cp $smokePath "api:/tmp/chemhub_v9_4_smoke.py" | Out-Host
docker compose exec -T api sh -lc "cd /app && python /tmp/chemhub_v9_4_smoke.py" | Out-Host

Write-Host "Patch v9.4 installed. Open site and AI Agent, then press Ctrl+F5." -ForegroundColor Green
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
