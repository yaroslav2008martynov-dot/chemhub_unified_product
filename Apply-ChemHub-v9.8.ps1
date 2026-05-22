$ErrorActionPreference = 'Stop'
Write-Host "ChemHub v9.8 stable extractor + SEO/site compatibility patch"
$Root = (Get-Location).Path
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v9_8_$Stamp"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

function Backup-IfExists($Path) {
  if (Test-Path $Path) {
    $name = ($Path -replace '[:\\/]', '_')
    Copy-Item $Path (Join-Path $Backup $name) -Force
  }
}

Backup-IfExists ".\apps\api\app\extractor.py"
Backup-IfExists ".\apps\api\app\processor.py"
Backup-IfExists ".\apps\api\app\main.py"
Backup-IfExists ".\apps\site\src\main.jsx"
Backup-IfExists ".\apps\site\src\styles.css"
Write-Host "Backup created: $Backup"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\api\app\main.py" ".\apps\api\app\main.py" -Force
Copy-Item ".\patch_files\apps\site\src\main.jsx" ".\apps\site\src\main.jsx" -Force
Copy-Item ".\patch_files\apps\site\src\styles.css" ".\apps\site\src\styles.css" -Force
Write-Host "Local files copied."

Write-Host "Applying safe DB compatibility migrations..."
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS review_reason TEXT;" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_status TEXT DEFAULT 'not_checked';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_note TEXT;" | Out-Host

Write-Host "Copying files into running containers if they exist..."
docker cp ".\apps\api\app\extractor.py" "chemhub_unified_product-api-1:/app/app/extractor.py" | Out-Host
docker cp ".\apps\api\app\processor.py" "chemhub_unified_product-api-1:/app/app/processor.py" | Out-Host
docker cp ".\apps\api\app\main.py" "chemhub_unified_product-api-1:/app/app/main.py" | Out-Host
try { docker cp ".\apps\site\src\main.jsx" "chemhub_unified_product-site-1:/app/src/main.jsx" | Out-Host } catch { Write-Host "Site container copy skipped: $($_.Exception.Message)" }
try { docker cp ".\apps\site\src\styles.css" "chemhub_unified_product-site-1:/app/src/styles.css" | Out-Host } catch { Write-Host "Site CSS copy skipped: $($_.Exception.Message)" }

Write-Host "Restarting API and site..."
docker compose restart api site | Out-Host
Start-Sleep -Seconds 4

Write-Host "Running smoke tests inside API container..."
$Smoke = @'
import sys
sys.path.insert(0, "/app")
from app.extractor import extract_reactions_from_text, canonical_equation
cases = {
 "hydride_ca": ("H2^0 + Ca^0 -> Ca+2H2-1", "CaH2"),
 "hydride_li": ("H2 + 2Li0 -> 2Li + 1H-1", "2LiH"),
 "haber": ("3H2^0 + N2 -> t, p, кат. (Fe) -> 2NH3+1 (Синтез аммиака (процесс Габера-Боша))", "2NH3"),
 "pka_reject": ("H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)", ""),
 "complex_charge": ("S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3", "[S8^2+]"),
 "template_al": ("Na[Al(OH)4] + CO2 -> Al(OH)3↓ + NaHCO3 (Al -> Al, Ga, In)", "Na[Ga(OH)4]"),
}
for name, (text, expected) in cases.items():
    rs = extract_reactions_from_text(text)
    joined = " | ".join([r.equation + " " + r.conditions + " " + r.temperature + " " + r.reaction_name for r in rs])
    if expected and expected not in joined:
        raise SystemExit(f"SMOKE FAIL {name}: {joined}")
    if not expected and rs:
        raise SystemExit(f"SMOKE FAIL {name}: should reject, got {joined}")
print("CHEMHUB_V9_8_SMOKE_OK", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
'@
$SmokePath = Join-Path $Root "chemhub_v9_8_smoke.py"
Set-Content -Path $SmokePath -Value $Smoke -Encoding UTF8
docker cp $SmokePath "chemhub_unified_product-api-1:/tmp/chemhub_v9_8_smoke.py" | Out-Host
docker compose exec -T api python /tmp/chemhub_v9_8_smoke.py | Out-Host

Write-Host "Patch v9.8 installed. Open site and AI Agent, then press Ctrl+F5."
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
