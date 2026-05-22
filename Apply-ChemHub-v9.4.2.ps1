
$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.4.2 PowerShell-safe installer fix"

$Root = Get-Location
$PatchDir = Join-Path $Root "patch_files"

if (!(Test-Path $PatchDir)) {
  Write-Host "ERROR: patch_files not found."
  Write-Host "Extract the v9.4.1 zip directly into C:\chemhub_unified_product first, then run this script."
  exit 1
}

$Backup = Join-Path $Root ("backup_before_v9_4_2_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $Backup | Out-Null

function Backup-IfExists($path) {
  if (Test-Path $path) {
    Copy-Item $path $Backup -Force
  }
}

Write-Host "Backup important files..."
Backup-IfExists (Join-Path $Root "apps\api\app\extractor.py")
Backup-IfExists (Join-Path $Root "apps\api\app\processor.py")
Backup-IfExists (Join-Path $Root "apps\site\src\main.jsx")
Backup-IfExists (Join-Path $Root "apps\site\src\styles.css")

function Copy-IfExists($src, $dst) {
  if (Test-Path $src) {
    $dstDir = Split-Path $dst -Parent
    if (!(Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
    Copy-Item $src $dst -Force
    Write-Host "Copied $src -> $dst"
  }
}

Write-Host "Copying local patch files..."
Copy-IfExists (Join-Path $PatchDir "apps\api\app\extractor.py") (Join-Path $Root "apps\api\app\extractor.py")
Copy-IfExists (Join-Path $PatchDir "apps\api\app\processor.py") (Join-Path $Root "apps\api\app\processor.py")
Copy-IfExists (Join-Path $PatchDir "apps\site\src\main.jsx") (Join-Path $Root "apps\site\src\main.jsx")
Copy-IfExists (Join-Path $PatchDir "apps\site\src\styles.css") (Join-Path $Root "apps\site\src\styles.css")

Write-Host "Checking Python syntax locally if Python is available..."
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
  if (Test-Path ".\apps\api\app\extractor.py") { python -m py_compile ".\apps\api\app\extractor.py" }
  if (Test-Path ".\apps\api\app\processor.py") { python -m py_compile ".\apps\api\app\processor.py" }
}

Write-Host "Copying files into running containers when available..."
$apiContainer = docker compose ps -q api
if ($apiContainer) {
  if (Test-Path ".\apps\api\app\extractor.py") { docker compose cp ".\apps\api\app\extractor.py" "api:/app/app/extractor.py" }
  if (Test-Path ".\apps\api\app\processor.py") { docker compose cp ".\apps\api\app\processor.py" "api:/app/app/processor.py" }
}
$siteContainer = docker compose ps -q site
if ($siteContainer) {
  if (Test-Path ".\apps\site\src\main.jsx") { docker compose cp ".\apps\site\src\main.jsx" "site:/app/src/main.jsx" }
  if (Test-Path ".\apps\site\src\styles.css") { docker compose cp ".\apps\site\src\styles.css" "site:/app/src/styles.css" }
}

Write-Host "Restarting API and site..."
docker compose restart api site

Write-Host "Waiting for API..."
Start-Sleep -Seconds 4

Write-Host "Smoke test import..."
$testCode = "from app.extractor import extract_reactions_from_text, canonical_equation; print('extractor ok'); print(canonical_equation('A + B -> C + D'));"
docker compose exec -T api python -c $testCode

Write-Host "Patch v9.4.2 installed."
Write-Host "Open site and AI Agent, then press Ctrl+F5."
Write-Host "Site: http://localhost:3000"
Write-Host "AI Agent: http://localhost:5173"
