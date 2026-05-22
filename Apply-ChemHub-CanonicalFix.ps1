$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.2.2 canonical_equation hotfix"

$root = Get-Location
$extractor = Join-Path $root "apps\api\app\extractor.py"
if (!(Test-Path $extractor)) {
  Write-Host "ERROR: apps\api\app\extractor.py not found. Run from C:\chemhub_unified_product" -ForegroundColor Red
  exit 1
}

$backupDir = Join-Path $root ("backup_before_v9_2_2_canonical_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Copy-Item $extractor (Join-Path $backupDir "extractor.py") -Force
Write-Host "Backup created: $backupDir"

$content = Get-Content $extractor -Raw -Encoding UTF8
if ($content -notmatch "def\s+canonical_equation\s*\(") {
  $block = @'

# Compatibility helper required by app.main and DB deduplication.
def canonical_equation(equation: str) -> str:
    """Return a stable normalized key for dedup/search without changing display equation."""
    import re
    text = str(equation or "")
    replacements = {
        "⟶": "→", "->": "→", "=>": "→",
        "<->": "⇌", "<=>": "⇌", "↔": "⇌", "⇄": "⇌",
        "−": "-", "–": "-", "—": "-",
        " ": "", "\t": "", "\n": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[;,.]+$", "", text)
    text = text.lower()
    return text
'@
  Add-Content -Path $extractor -Value $block -Encoding UTF8
  Write-Host "canonical_equation added to local extractor.py"
} else {
  Write-Host "canonical_equation already exists in local extractor.py"
}

Write-Host "Copying fixed extractor into API container..."
docker cp $extractor chemhub_unified_product-api-1:/app/app/extractor.py

Write-Host "Restarting API..."
docker compose up -d api
Start-Sleep -Seconds 4

Write-Host "Testing API import..."
docker compose exec -T api python -c "from app.extractor import canonical_equation, extract_reactions_from_text; print('canonical:', canonical_equation('2K + 2H2O -> 2KOH + H2^')[:80]); print('extractor import ok')"

Write-Host "Done. Open AI Agent and press Ctrl+F5: http://localhost:5173"
