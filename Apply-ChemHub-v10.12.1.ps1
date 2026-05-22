$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.12.1 global oxidation cleanup patch"

$Root = Get-Location
$Extractor = Join-Path $Root "apps\api\app\extractor.py"
if (!(Test-Path $Extractor)) {
  throw "Cannot find apps\api\app\extractor.py. Run this script from C:\chemhub_unified_product"
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v10_12_1_$Stamp"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item $Extractor (Join-Path $Backup "extractor.py") -Force
Write-Host "Backup created: $Backup"

$PatchPy = Join-Path $Root "chemhub_v10_12_1_apply.py"
@'
from pathlib import Path
import re

path = Path("apps/api/app/extractor.py")
text = path.read_text(encoding="utf-8")

start = "# --- CHEMHUB V10.12.1 GLOBAL OXIDATION CLEANUP START ---"
end = "# --- CHEMHUB V10.12.1 GLOBAL OXIDATION CLEANUP END ---"
if start in text and end in text:
    text = text[:text.index(start)] + text[text.index(end) + len(end):]

block = r
'@
