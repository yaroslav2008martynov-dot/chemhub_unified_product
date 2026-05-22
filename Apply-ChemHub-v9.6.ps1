$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.6 stable chemistry + SEO safe patch"

$Root = (Get-Location).Path
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v9_6_$Stamp"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

$Files = @(
  "apps\api\app\extractor.py",
  "apps\api\app\processor.py",
  "apps\api\app\models.py",
  "apps\api\app\db.py",
  "apps\api\app\main.py",
  "apps\api\app\seo.py",
  "apps\api\app\schemas.py",
  "apps\site\src\main.jsx",
  "apps\site\src\styles.css",
  "apps\agent\src\main.jsx"
)

foreach ($F in $Files) {
  $Src = Join-Path $Root $F
  if (Test-Path $Src) {
    $Dest = Join-Path $Backup $F
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    Copy-Item $Src $Dest -Force
  }
}
Write-Host "Backup created: $Backup"

foreach ($F in $Files) {
  $Patch = Join-Path $Root (Join-Path "patch_files" $F)
  $Dest = Join-Path $Root $F
  if (Test-Path $Patch) {
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    Copy-Item $Patch $Dest -Force
  }
}
Write-Host "Local files copied."

Write-Host "Applying safe DB compatibility migration..."
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT DEFAULT '';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS reaction_kind TEXT DEFAULT '';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT DEFAULT '';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT DEFAULT '';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS review_reason TEXT DEFAULT '';" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE processing_jobs ALTER COLUMN created_at SET DEFAULT NOW();" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ALTER COLUMN created_at SET DEFAULT NOW();" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ALTER COLUMN updated_at SET DEFAULT NOW();" | Out-Host
docker compose exec -T postgres psql -U chemhub -d chemhub -c "ALTER TABLE reactions ALTER COLUMN validation_status SET DEFAULT 'not_checked';" | Out-Host

Write-Host "Copying files into running containers..."
$ApiFiles = @("extractor.py","processor.py","models.py","db.py","main.py","seo.py","schemas.py")
foreach ($Name in $ApiFiles) {
  docker compose cp ".\apps\api\app\$Name" "api:/app/app/$Name" | Out-Host
}
docker compose cp ".\apps\site\src\main.jsx" "site:/app/src/main.jsx" | Out-Host
docker compose cp ".\apps\site\src\styles.css" "site:/app/src/styles.css" | Out-Host
docker compose cp ".\apps\agent\src\main.jsx" "agent:/app/src/main.jsx" | Out-Host

Write-Host "Restarting api/site/agent..."
docker compose restart api site agent | Out-Host
Start-Sleep -Seconds 3

Write-Host "Smoke-test extractor inside API container..."
docker compose exec -T api python -c "import sys; sys.path.insert(0,'/app'); from app.extractor import extract_reactions_from_text, canonical_equation; rs=extract_reactions_from_text('H2^0 + Ca^0 -> Ca+2H2-1'); assert rs and rs[0].equation == 'H2 + Ca → CaH2', rs; rs=extract_reactions_from_text('H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)'); assert rs == [], rs; print('extractor smoke ok')" | Out-Host

Write-Host "Patch v9.6 installed. Open site and AI Agent, then press Ctrl+F5."
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
