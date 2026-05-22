$ErrorActionPreference = "Stop"
Write-Host "ChemHub v10.10 H2 oxidation-state OCR repair + strict superscript cleanup"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root "backup_before_v10_10_$ts"
New-Item -ItemType Directory -Force -Path $backup | Out-Null
Copy-Item ".\apps\api\app\extractor.py" (Join-Path $backup "extractor.py") -Force
Write-Host "Backup created: $backup"

$patchPy = Join-Path $root "chemhub_v10_10_patch_extractor.py"
@'
from pathlib import Path
import re

path = Path("apps/api/app/extractor.py")
s = path.read_text(encoding="utf-8")
orig = s

# 1) OCR rule: H₂⁰ is often read as H20. Include O2 and other elementary reagents.
s = s.replace(
    r'\bH20(?=\s*\+\s*(?:S|CuO|Ca|Li|Na|K|Rb|Cs)\b)',
    r'\bH20(?=\s*\+\s*(?:O2|S|CuO|Ca|Li|Na|K|Rb|Cs|F2|Cl2|Br2|I2|N2)\b)'
)

helper = r'''
def _repair_common_oxidation_ocr_misreads(text: str) -> str:
    """Repair common OCR cases where oxidation states were read as formula atoms.

    Examples:
    2H2^0 + O2 -> 2H2^+1O must become 2H2 + O2 -> 2H2O.
    This function is deliberately narrow: it fixes known oxidation-state OCR artifacts
    without changing normal H2O reactions.
    """
    text = _clean_spaces(text)

    # Water self-reaction artifact from H2^0/O^-2 notation:
    # 2H2O + O2 -> 2H2O  should be  2H2 + O2 -> 2H2O
    def _fix_h2_o2(m: re.Match) -> str:
        left_coef = m.group(1) or ""
        right_coef = m.group(2) or ""
        return f"{left_coef}H2 + O2 → {right_coef}H2O"

    text = re.sub(
        r"\b(\d*)H2O\s*\+\s*O2\s*→\s*(\d*)H2O\b",
        _fix_h2_o2,
        text,
    )

    # Earlier textbook cases with H2^0 read as H2O.
    text = re.sub(r"\bH2O\s*\+\s*S\s*→\s*H2S\b", "H2 + S → H2S", text)
    text = re.sub(r"\bH2O\s*\+\s*CuO\s*→\s*Cu\s*\+\s*H2O\b", "H2 + CuO → Cu + H2O", text)
    text = re.sub(r"\bH2O\s*\+\s*Ca\s*→\s*CaH2\b", "H2 + Ca → CaH2", text)

    # Remove any leftover oxidation-state fragments that survived OCR normalization.
    text = re.sub(r"([A-Z][a-z]?\d*)\s*\+\s*1(?=[A-Z])", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?\d*)\s*-\s*\d+(?=($|[\s+→⇌≠),]))", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?\d*)\s*\+\s*\d+(?=($|[\s+→⇌≠),]))", r"\1", text)
    return _clean_spaces(text)
'''

if "def _repair_common_oxidation_ocr_misreads" not in s:
    marker = "\ndef canonical_equation"
    if marker in s:
        s = s.replace(marker, helper + marker, 1)
    else:
        # Fallback for minified file: insert before canonical_equation token.
        s = s.replace(" def canonical_equation", helper + "\ndef canonical_equation", 1)

# 2) Ensure fix_ocr_formula calls the repair helper before returning.
if "_repair_common_oxidation_ocr_misreads(text)" not in s:
    m = re.search(r"def fix_ocr_formula\(text: str\) -> str:(.*?)\ndef canonical_equation", s, flags=re.S)
    if not m:
        raise SystemExit("Could not locate fix_ocr_formula block; extractor.py layout is unexpected")
    block = m.group(1)
    new_block = re.sub(
        r"\n\s*return _clean_spaces\(text\)\s*$",
        "\n    text = _repair_common_oxidation_ocr_misreads(text)\n    return _clean_spaces(text)",
        block,
        count=1,
        flags=re.S,
    )
    if new_block == block:
        raise SystemExit("Could not patch return in fix_ocr_formula")
    s = s[:m.start(1)] + new_block + s[m.end(1):]

# 3) If the file has the old strict H20 -> H2O fallback, keep it after the special H20 cases.
# Nothing else is changed.

if s == orig:
    print("No textual change was needed; extractor already contains v10.10 logic.")
else:
    path.write_text(s, encoding="utf-8", newline="\n")
    print("extractor.py patched for v10.10")
'@ | Set-Content $patchPy -Encoding UTF8

python $patchPy

Write-Host "Checking local Python syntax..."
python -m py_compile .\apps\api\app\extractor.py
Write-Host "Local syntax OK."

Write-Host "Copying extractor into running API container..."
docker cp .\apps\api\app\extractor.py chemhub_unified_product-api-1:/app/app/extractor.py

Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 3

$smoke = Join-Path $root "chemhub_v10_10_smoke.py"
@'
from app.extractor import extract_reactions_from_text, fix_ocr_formula
cases = [
    "2H20 + O2 -> 2H2+1O",
    "2H2^0 + O2 -> 2H2^+1O",
    "H20 + S -> H2+1S",
    "H20 + CuO -> Cu + H2O",
    "H20 + Ca -> Ca+2H2-1",
    "CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O",
    "2Tl + S -> 300 °C, в токе H2 -> Tl2S",
]
for c in cases:
    rs = extract_reactions_from_text(c)
    print("CASE:", c)
    print([(r.equation, r.conditions, r.temperature) for r in rs])
'@ | Set-Content $smoke -Encoding UTF8

docker cp $smoke chemhub_unified_product-api-1:/tmp/chemhub_v10_10_smoke.py
Write-Host "Running smoke tests inside API container..."
docker compose exec -T -w /app api python /tmp/chemhub_v10_10_smoke.py

Write-Host "Patch v10.10 installed. Open AI Agent and press Ctrl+F5: http://localhost:5173"
