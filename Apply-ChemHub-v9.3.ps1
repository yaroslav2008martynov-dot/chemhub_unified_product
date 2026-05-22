$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.3 chemistry-aware conditions + site rendering patch"
$Root = (Get-Location).Path
$Backup = Join-Path $Root ("backup_before_v9_3_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

function Backup-IfExists($rel) {
  $p = Join-Path $Root $rel
  if (Test-Path $p) {
    $dest = Join-Path $Backup $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item $p $dest -Force
  }
}

Backup-IfExists "apps\api\app\extractor.py"
Backup-IfExists "apps\api\app\processor.py"
Backup-IfExists "apps\site\src\main.jsx"
Backup-IfExists "apps\site\src\styles.css"
Write-Host "Backup created: $Backup"

Copy-Item ".\patch_files\apps\api\app\extractor.py" ".\apps\api\app\extractor.py" -Force
Copy-Item ".\patch_files\apps\api\app\processor.py" ".\apps\api\app\processor.py" -Force
Copy-Item ".\patch_files\apps\site\src\main.jsx" ".\apps\site\src\main.jsx" -Force
Copy-Item ".\patch_files\apps\site\src\styles.css" ".\apps\site\src\styles.css" -Force
Write-Host "Local files copied."

Write-Host "Applying safe DB compatibility and duplicate cleanup..."
$sql = @'
ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;
ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT;
ALTER TABLE reactions ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;
ALTER TABLE reactions ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT TRUE;
ALTER TABLE reactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT;
ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS review_reason TEXT;
ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_status TEXT DEFAULT 'not_checked';
ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_note TEXT;
UPDATE reactions SET canonical_equation = lower(regexp_replace(coalesce(equation,''), '\s+', '', 'g')) WHERE canonical_equation IS NULL OR canonical_equation = '';
UPDATE reactions SET hidden = TRUE WHERE equation ~* '(^|[[:space:]])(катод|анод|полуреакц|электрон)' OR equation LIKE '%ē%' OR equation ~* '(^|[+[:space:]])e[-−]?([+[:space:]]|$)';
WITH ranked AS (
  SELECT id, row_number() OVER (
    PARTITION BY canonical_equation
    ORDER BY (
      length(coalesce(conditions,'')) + length(coalesce(catalysts,'')) + length(coalesce(solvents,'')) +
      length(coalesce(temperature,'')) + length(coalesce(pressure,'')) + length(coalesce(reaction_name,'')) +
      length(coalesce(equation,''))
    ) DESC, id ASC
  ) AS rn
  FROM reactions
  WHERE canonical_equation IS NOT NULL AND canonical_equation <> '' AND coalesce(hidden,false) = false
)
UPDATE reactions r SET hidden = TRUE FROM ranked WHERE r.id = ranked.id AND ranked.rn > 1;
'@
$sql | docker compose exec -T postgres psql -U chemhub -d chemhub | Out-Host

Write-Host "Copying files into running containers..."
docker compose cp ".\apps\api\app\extractor.py" api:/app/app/extractor.py | Out-Host
docker compose cp ".\apps\api\app\processor.py" api:/app/app/processor.py | Out-Host
docker compose cp ".\apps\site\src\main.jsx" site:/app/src/main.jsx | Out-Host
docker compose cp ".\apps\site\src\styles.css" site:/app/src/styles.css | Out-Host

Write-Host "Restarting API and site..."
docker compose restart api site | Out-Host
Start-Sleep -Seconds 3

Write-Host "Smoke test extractor inside API container..."
$smoke = @'
from app.extractor import extract_reactions_from_text, canonical_equation
cases = {
  "h2_oxidation_not_water": "H20 + S -> H2+1S",
  "line_merge": "BeO + H2SO4 -> BeSO4 +\n+ H2O",
  "condition_range": "120-150 o C\n2Tl + Cl2 -> 2TlCl",
  "named": "2NH3 + NaOCl -> желатин -> N2H4 + NaCl + H2O (синтез Рашига)",
  "ionic_reject": "катод: Mg2+ + 2ē -> Mg",
  "complex_charge": "S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3",
}
for name, text in cases.items():
    rs = extract_reactions_from_text(text)
    print(name, [(r.equation, r.conditions, r.temperature, r.reaction_name) for r in rs])
print("canon", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
'@
$smokePath = Join-Path $Root "chemhub_v9_3_smoke.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker compose cp $smokePath api:/tmp/chemhub_v9_3_smoke.py | Out-Host
docker compose exec -T api python /tmp/chemhub_v9_3_smoke.py | Out-Host
Remove-Item $smokePath -Force -ErrorAction SilentlyContinue

Write-Host "Patch v9.3 installed. Open site and AI Agent, then press Ctrl+F5."
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
