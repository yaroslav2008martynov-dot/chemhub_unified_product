$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.2 chemistry-aware extraction patch" -ForegroundColor Cyan

$root = Get-Location
$extractorSrc = Join-Path $root "patch_files\apps\api\app\extractor.py"
$processorSrc = Join-Path $root "patch_files\apps\api\app\processor.py"
$apiApp = Join-Path $root "apps\api\app"

if (!(Test-Path $extractorSrc)) { throw "Patch file not found: $extractorSrc" }
if (!(Test-Path $processorSrc)) { throw "Patch file not found: $processorSrc" }
if (!(Test-Path $apiApp)) { throw "Run this script from C:\chemhub_unified_product. apps\api\app not found." }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v9_2_agent_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item (Join-Path $apiApp "extractor.py") (Join-Path $backup "extractor.py") -ErrorAction SilentlyContinue
Copy-Item (Join-Path $apiApp "processor.py") (Join-Path $backup "processor.py") -ErrorAction SilentlyContinue
Write-Host "Backup created: $backup" -ForegroundColor DarkGray

Copy-Item $extractorSrc (Join-Path $apiApp "extractor.py") -Force
Copy-Item $processorSrc (Join-Path $apiApp "processor.py") -Force
Write-Host "Local files copied." -ForegroundColor Green

Write-Host "Checking syntax locally if Python is available..." -ForegroundColor Yellow
try {
  python -m py_compile (Join-Path $apiApp "extractor.py") (Join-Path $apiApp "processor.py")
} catch {
  Write-Host "Local Python syntax check skipped/failed. Continuing with container check." -ForegroundColor Yellow
}

Write-Host "Copying files into running API container..." -ForegroundColor Yellow
$apiName = (docker compose ps -q api)
if ([string]::IsNullOrWhiteSpace($apiName)) {
  Write-Host "API container is not running; starting api..." -ForegroundColor Yellow
  docker compose up -d api
  Start-Sleep -Seconds 3
  $apiName = (docker compose ps -q api)
}
if ([string]::IsNullOrWhiteSpace($apiName)) { throw "API container was not found. Check docker compose ps." }

docker cp (Join-Path $apiApp "extractor.py") "$apiName`:/app/app/extractor.py"
docker cp (Join-Path $apiApp "processor.py") "$apiName`:/app/app/processor.py"

Write-Host "Restarting API..." -ForegroundColor Yellow
docker compose restart api | Out-Host
Start-Sleep -Seconds 3

Write-Host "Smoke test extractor inside container..." -ForegroundColor Yellow
$smoke = @'
from app.extractor import extract_reactions_from_text
cases = [
    "H20 + S -> H2+1S",
    "2Tl + S -> 300 o C, в токе H2 -> Tl2S",
    "BeO + H2SO4 -> BeSO4 +\n+ H2O",
    "4Li + O2 -> 2Li2O (оксид)",
    "катод: Mg2+ + 2e- -> Mg",
    "S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3",
]
for text in cases:
    rs = extract_reactions_from_text(text)
    print(text, "=>", [(getattr(r, "equation", ""), getattr(r, "conditions", ""), getattr(r, "temperature", "")) for r in rs])
'@
$smokePath = Join-Path $root "chemhub_v9_2_smoke_test.py"
Set-Content -Path $smokePath -Value $smoke -Encoding UTF8
docker cp $smokePath "$apiName`:/tmp/chemhub_v9_2_smoke_test.py"
docker compose exec -T api python /tmp/chemhub_v9_2_smoke_test.py
Remove-Item $smokePath -Force -ErrorAction SilentlyContinue

Write-Host "Patch v9.2.1 installed successfully." -ForegroundColor Green
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173" -ForegroundColor Cyan
