$ErrorActionPreference = 'Stop'
Write-Host 'ChemHub v9.5 stable chemistry-aware extractor + SEO/site patch'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (!(Test-Path '.\docker-compose.yml')) { Write-Error 'Run this script from C:\chemhub_unified_product with docker-compose.yml'; exit 1 }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $Root "backup_before_v9_5_$stamp"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$files = @(
  'apps\api\app\extractor.py',
  'apps\api\app\processor.py',
  'apps\api\app\models.py',
  'apps\api\app\db.py',
  'apps\api\app\main.py',
  'apps\api\app\seo.py',
  'apps\site\src\main.jsx',
  'apps\site\src\styles.css'
)
foreach ($f in $files) {
  if (Test-Path $f) {
    $dest = Join-Path $backup $f
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item $f $dest -Force
  }
}
Write-Host "Backup created: $backup"
Write-Host 'Copying patch files to local project...'
Copy-Item '.\patch_files\apps\api\app\extractor.py' '.\apps\api\app\extractor.py' -Force
Copy-Item '.\patch_files\apps\api\app\processor.py' '.\apps\api\app\processor.py' -Force
Copy-Item '.\patch_files\apps\api\app\models.py' '.\apps\api\app\models.py' -Force
Copy-Item '.\patch_files\apps\api\app\db.py' '.\apps\api\app\db.py' -Force
Copy-Item '.\patch_files\apps\api\app\main.py' '.\apps\api\app\main.py' -Force
Copy-Item '.\patch_files\apps\api\app\seo.py' '.\apps\api\app\seo.py' -Force
Copy-Item '.\patch_files\apps\site\src\main.jsx' '.\apps\site\src\main.jsx' -Force
Copy-Item '.\patch_files\apps\site\src\styles.css' '.\apps\site\src\styles.css' -Force
Write-Host 'Applying safe DB compatibility migrations...'
docker compose up -d postgres | Out-Host
$queries = @(
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT DEFAULT '';",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS reaction_kind VARCHAR(100) DEFAULT '';",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS impossible_note TEXT DEFAULT '';",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS approved BOOLEAN DEFAULT TRUE;",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS hidden BOOLEAN DEFAULT FALSE;",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS origin VARCHAR(100) DEFAULT 'ai';",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS validation_status VARCHAR(100) DEFAULT 'needs_review';",
"ALTER TABLE reactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",
"ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS canonical_equation TEXT DEFAULT '';",
"ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS review_reason TEXT DEFAULT '';",
"ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_status VARCHAR(100) DEFAULT 'not_checked';",
"ALTER TABLE job_reactions ADD COLUMN IF NOT EXISTS internet_note TEXT DEFAULT '';",
"ALTER TABLE processing_jobs ALTER COLUMN created_at SET DEFAULT NOW();",
"ALTER TABLE reactions ALTER COLUMN created_at SET DEFAULT NOW();",
"ALTER TABLE reactions ALTER COLUMN updated_at SET DEFAULT NOW();",
"UPDATE processing_jobs SET created_at=NOW() WHERE created_at IS NULL;",
"UPDATE reactions SET created_at=NOW() WHERE created_at IS NULL;",
"UPDATE reactions SET updated_at=NOW() WHERE updated_at IS NULL;",
"UPDATE reactions SET validation_status='needs_review' WHERE validation_status IS NULL;"
)
foreach ($q in $queries) { docker compose exec -T postgres psql -U chemhub -d chemhub -c $q | Out-Host }
Write-Host 'Copying patch files into running containers...'
docker compose up -d api site | Out-Host
Start-Sleep -Seconds 2
docker compose cp '.\apps\api\app\extractor.py' 'api:/app/app/extractor.py' | Out-Host
docker compose cp '.\apps\api\app\processor.py' 'api:/app/app/processor.py' | Out-Host
docker compose cp '.\apps\api\app\models.py' 'api:/app/app/models.py' | Out-Host
docker compose cp '.\apps\api\app\db.py' 'api:/app/app/db.py' | Out-Host
docker compose cp '.\apps\api\app\main.py' 'api:/app/app/main.py' | Out-Host
docker compose cp '.\apps\api\app\seo.py' 'api:/app/app/seo.py' | Out-Host
docker compose cp '.\apps\site\src\main.jsx' 'site:/app/src/main.jsx' | Out-Host
docker compose cp '.\apps\site\src\styles.css' 'site:/app/src/styles.css' | Out-Host
Write-Host 'Restarting API and site...'
docker compose restart api site | Out-Host
Start-Sleep -Seconds 4
Write-Host 'Running smoke tests inside API container...'
docker compose cp '.\patch_files\chemhub_v9_5_smoke.py' 'api:/tmp/chemhub_v9_5_smoke.py' | Out-Host
docker compose exec -T api sh -lc 'cd /app && python /tmp/chemhub_v9_5_smoke.py --cleanup' | Out-Host
Write-Host 'Patch v9.5 installed successfully.'
Write-Host 'Open site and press Ctrl+F5: http://localhost:3000'
Write-Host 'Open AI Agent and press Ctrl+F5: http://localhost:5173'
