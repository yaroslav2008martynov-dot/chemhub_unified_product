$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.7 generalized templates + strict chemistry extraction patch"

$root = Get-Location
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v9_7_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

function Copy-IfExists($src, $dst) {
  if (Test-Path $src) {
    $dir = Split-Path $dst -Parent
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Copy-Item $src $dst -Force
  }
}

Write-Host "Backup current files..."
Copy-IfExists ".\apps\api\app\extractor.py" (Join-Path $backup "extractor.py")
Copy-IfExists ".\apps\api\app\processor.py" (Join-Path $backup "processor.py")
Copy-IfExists ".\apps\site\src\main.jsx" (Join-Path $backup "site_main.jsx")
Copy-IfExists ".\apps\site\src\styles.css" (Join-Path $backup "site_styles.css")

Write-Host "Copy patch files locally..."
Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\site\src\main.jsx" ".\apps\site\src\main.jsx" -Force
Copy-Item ".\patch_files\apps\site\src\styles.css" ".\apps\site\src\styles.css" -Force

Write-Host "Local Python syntax check..."
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
  python -m py_compile .\apps\api\app\extractor.py .\apps\api\app\processor.py
}

Write-Host "Safe DB compatibility + duplicate cleanup..."
$Sqls = @(
  "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;",
  "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT;",
  "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;",
  "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT TRUE;",
  "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",
  "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;",
  "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS review_reason TEXT;",
  "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_status TEXT DEFAULT 'not_checked';",
  "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_note TEXT;",
  "UPDATE reactions SET canonical_equation = lower(regexp_replace(coalesce(equation,''), '\\s+', '', 'g')) WHERE canonical_equation IS NULL OR canonical_equation = '';",
  "WITH ranked AS (SELECT id, row_number() OVER (PARTITION BY canonical_equation ORDER BY (length(coalesce(conditions,''))+length(coalesce(temperature,''))+length(coalesce(catalysts,''))+length(coalesce(reaction_name,''))+length(coalesce(equation,''))) DESC, id ASC) rn FROM reactions WHERE canonical_equation IS NOT NULL AND canonical_equation <> '') UPDATE reactions r SET hidden = TRUE, approved = FALSE FROM ranked x WHERE r.id = x.id AND x.rn > 1;"
)
foreach ($sql in $Sqls) {
  docker compose exec -T postgres psql -U chemhub -d chemhub -c $sql | Write-Host
}

Write-Host "Copy into running containers..."
docker compose cp .\apps\api\app\extractor.py api:/app/app/extractor.py
docker compose cp .\apps\api\app\processor.py api:/app/app/processor.py
docker compose cp .\apps\site\src\main.jsx site:/app/src/main.jsx
docker compose cp .\apps\site\src\styles.css site:/app/src/styles.css

Write-Host "Restart API and site..."
docker compose restart api site
Start-Sleep -Seconds 5

Write-Host "Smoke test inside API container..."
$smoke = @'
from app.extractor import extract_reactions_from_text, canonical_equation
cases = [
    ("ca_hydride", "H2^0 + Ca^0 -> Ca+2H2-1", "Ca + H2 -> CaH2"),
    ("li_hydride", "H2 + 2Li0 -> 2Li + 1H-1", "2Li + H2 -> 2LiH"),
    ("template", "Na[Al(OH)4] + CO2 -> Al(OH)3 + NaHCO3 (Al = Al, Ga, In)", "Na[Ga(OH)4]"),
    ("reject_pka", "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)", ""),
    ("reject_electrode", "катод: Mg2+ + 2e- -> Mg", ""),
    ("negative", "Bi + 4HNO3 конц. !=", ""),
    ("haber", "3H2^0 + N2 -> t,p,кат.(Fe) -> 2NH3+1 (Синтез аммиака процесс Габера-Боша)", "3H2 + N2"),
    ("cluster", "S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3", "[S8^2+]"),
    ("wrap", "BeO + H2SO4 -> BeSO4 +\n+ H2O", "BeSO4 + H2O"),
]
for name, text, expected in cases:
    rs = extract_reactions_from_text(text.replace('!=','≠'))
    joined = ' | '.join([r.equation + ' ' + r.conditions + ' ' + r.reaction_name for r in rs])
    print(name, joined)
    if expected and expected not in joined:
        raise SystemExit(f"FAILED {name}: expected {expected}, got {joined}")
    if not expected and joined:
        raise SystemExit(f"FAILED {name}: expected reject, got {joined}")
print("canonical", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
print("SMOKE_OK")
'@
$smokePath = Join-Path $root "chemhub_v9_7_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker compose cp $smokePath api:/tmp/chemhub_v9_7_smoke.py
docker compose exec -T api sh -lc "cd /app && python /tmp/chemhub_v9_7_smoke.py"

Write-Host "Patch v9.7 installed successfully. Open site and AI Agent, then press Ctrl+F5."
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
