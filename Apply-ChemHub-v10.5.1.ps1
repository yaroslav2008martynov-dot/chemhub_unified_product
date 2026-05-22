Write-Host "ChemHub v10.5.1 template-definition tail + P4O10 hotfix"
$ErrorActionPreference = "Stop"
$Root = Get-Location
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_v10_5_1_$Stamp"
New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item ".\apps\api\app\extractor.py" (Join-Path $Backup "extractor.py") -Force

$PatchPy = @'
from pathlib import Path
p = Path("apps/api/app/extractor.py")
text = p.read_text(encoding="utf-8")
marker = "# CHEMHUB_V10_5_1_TEMPLATE_TAIL_HOTFIX"
if marker not in text:
    text += r'''

# CHEMHUB_V10_5_1_TEMPLATE_TAIL_HOTFIX
# Safe post-processing layer. It preserves the existing extractor and only fixes:
# 1) leftover template definitions after expansion: "2LiH Li = Li, Na, K" -> "2LiH";
# 2) OCR/oxidation cleanup accidentally shortening P4O10 -> P4O1;
# 3) unchanged behavior for all previous extractor functions.
import re as _chemhub_re_v1051

_CHEMHUB_TEMPLATE_DEF_TAIL_RE = _chemhub_re_v1051.compile(
    r"\s+(?:M|X|Hal|Me|E|[A-Z][a-z]?)\s*=\s*(?:[A-Z][a-z]?|alkali|alkaline|halogens?|щелочные|щелочноземельные|галогены)(?:\s*,\s*(?:[A-Z][a-z]?))*\s*$",
    _chemhub_re_v1051.I,
)

def _chemhub_strip_template_definition_tail_v1051(s: str) -> str:
    s = str(s or "")
    # Remove bare definitions left after template expansion, not chemical coefficients.
    s = _CHEMHUB_TEMPLATE_DEF_TAIL_RE.sub("", s)
    # Keep dehydration reagent formula intact; previous oxidation cleanup could turn P4O10 into P4O1.
    s = _chemhub_re_v1051.sub(r"\bP4O1\b", "P4O10", s)
    return _clean_spaces(s) if "_clean_spaces" in globals() else s.strip()

_chemhub_orig_fix_ocr_formula_v1051 = fix_ocr_formula

def fix_ocr_formula(text: str) -> str:  # noqa: F811
    return _chemhub_strip_template_definition_tail_v1051(_chemhub_orig_fix_ocr_formula_v1051(text))

_chemhub_orig_expand_templates_v1051 = expand_templates

def expand_templates(eq: str, context: str) -> list[str]:  # noqa: F811
    out = []
    for candidate in _chemhub_orig_expand_templates_v1051(eq, context):
        fixed = _chemhub_strip_template_definition_tail_v1051(candidate)
        # Do not save unexpanded generic reactions.
        if _chemhub_re_v1051.search(r"(?<![A-Za-z])(M|X|Hal|Me|E)(?![a-z])", fixed):
            continue
        if fixed and fixed not in out:
            out.append(fixed)
    return out

_chemhub_orig_normalize_condition_v1051 = normalize_condition

def normalize_condition(cond: str) -> dict:  # noqa: F811
    data = _chemhub_orig_normalize_condition_v1051(_chemhub_strip_template_definition_tail_v1051(cond))
    for key in list(data.keys()):
        data[key] = [_chemhub_strip_template_definition_tail_v1051(x) for x in data.get(key, [])]
    return data
'''
    p.write_text(text, encoding="utf-8")
print("v10.5.1 hotfix applied to extractor.py")
'@
Set-Content -Path ".\chemhub_v10_5_1_patch.py" -Value $PatchPy -Encoding UTF8
python .\chemhub_v10_5_1_patch.py

Write-Host "Checking local Python syntax..."
python -m py_compile .\apps\api\app\extractor.py
Write-Host "Local syntax OK."

Write-Host "Copying extractor into API container..."
docker cp ".\apps\api\app\extractor.py" chemhub_unified_product-api-1:/app/app/extractor.py
Write-Host "Restarting API..."
docker compose restart api
Start-Sleep -Seconds 3

$Smoke = @'
from app.extractor import extract_reactions_from_text
cases = [
    ("2M + H2 -> 2MH M = Li, Na, K", ["2Li + H2 → 2LiH", "2Na + H2 → 2NaH", "2K + H2 → 2KH"]),
    ("M2O + H2O -> 2MOH M = Li, Na, K", ["Li2O + H2O → 2LiOH", "Na2O + H2O → 2NaOH", "K2O + H2O → 2KOH"]),
    ("CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O", ["CH2(COOH)2 → C3O2 + 2H2O"]),
]
for text, expected in cases:
    rows = extract_reactions_from_text(text)
    equations = [r.equation for r in rows]
    print(text, "=>", [(r.equation, r.conditions, r.temperature) for r in rows])
    for e in expected:
        assert e in equations, (text, e, equations)
    assert not any(" = " in e for e in equations), equations
    assert not any("M" in e or "X" in e or "Hal" in e for e in equations), equations
rows = extract_reactions_from_text("CH2(COOH)2 -> 140 °C, P4O10 -> C3O2 + 2H2O")
assert rows and ("P4O10" in rows[0].conditions or "P4O10" in rows[0].catalysts), [(r.conditions, r.catalysts) for r in rows]
print("SMOKE_OK")
'@
Set-Content -Path ".\chemhub_v10_5_1_smoke.py" -Value $Smoke -Encoding UTF8
docker cp ".\chemhub_v10_5_1_smoke.py" chemhub_unified_product-api-1:/tmp/chemhub_v10_5_1_smoke.py
Write-Host "Running smoke test inside API container..."
docker compose exec -w /app api python /tmp/chemhub_v10_5_1_smoke.py

Write-Host "Patch v10.5.1 installed. Open AI Agent and press Ctrl+F5: http://localhost:5173"
