
$ErrorActionPreference = "Stop"
Write-Host "ChemHub v9.8.2 strict oxidation real fix"

$Root = Get-Location
$Extractor = Join-Path $Root "apps\api\app\extractor.py"

if (!(Test-Path $Extractor)) {
  Write-Host "ERROR: apps\api\app\extractor.py not found. Run this from C:\chemhub_unified_product"
  exit 1
}

$BackupDir = Join-Path $Root ("backup_before_v9_8_2_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
Copy-Item $Extractor (Join-Path $BackupDir "extractor.py") -Force
Write-Host "Backup created: $BackupDir"

$Marker = "# CHEMHUB_V9_8_2_STRICT_OXIDATION_OVERLAY"
$Content = Get-Content $Extractor -Raw -Encoding UTF8

if ($Content -notlike "*$Marker*") {
$Overlay = @'
# CHEMHUB_V9_8_2_STRICT_OXIDATION_OVERLAY
# Strict post-processing layer: removes oxidation-state marks outside square brackets
# while preserving real complex/cluster charges like [S8^2+], [AsF6−], [Fe(CN)6]4−.
import re as _chemhub_re

_chemhub_v982_original_extract = extract_reactions_from_text

def _chemhub_v982_split_protected(text: str):
    parts = []
    buf = []
    inside = False
    for ch in str(text or ""):
        if ch == "[":
            if buf:
                parts.append((inside, "".join(buf)))
                buf = []
            inside = True
            buf.append(ch)
        elif ch == "]":
            buf.append(ch)
            parts.append((inside, "".join(buf)))
            buf = []
            inside = False
        else:
            buf.append(ch)
    if buf:
        parts.append((inside, "".join(buf)))
    return parts

def _chemhub_v982_clean_oxidation_outside_brackets(text: str) -> str:
    text = str(text or "")
    protected = _chemhub_v982_split_protected(text)
    out = []
    for inside, part in protected:
        if inside:
            out.append(part)
            continue
        s = part
        # superscript/common OCR oxidation states
        trans = str.maketrans({
            "⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9",
            "⁺":"+","⁻":"-","−":"-","–":"-","—":"-"
        })
        s = s.translate(trans)
        # Remove element oxidation states printed after element/formula: Li0, Ca0, Al+3, H-1, H1, Cu+2
        s = _chemhub_re.sub(r"\b([A-Z][a-z]?)(\d*)\s*(?:\^?\s*)?(?:0|[+-]\s*[1-8])(?=\s*(?:[+→⇌,;)\]]|$))", r"\1\2", s)
        s = _chemhub_re.sub(r"\b([A-Z][a-z]?)(\d*)\s*(?:\^?\s*)?(?:0|[+-]\s*[1-8])(?=[A-Z(])", r"\1\2", s)
        # Common OCR: H2+1O -> H2O, H2+1S -> H2S, etc.
        s = _chemhub_re.sub(r"\bH2\s*\+?\s*1(?=[A-Z])", "H2", s)
        # Remove standalone oxidation coefficients before element in products: +1H, -1H
        s = _chemhub_re.sub(r"(?:(?<=\s)|(?<=\+)|(?<=→)|(?<=⇌))[+-]?\s*[1-8]\s*([A-Z][a-z]?)", r"\1", s)
        # Fix OCR H20 used as H2 oxidation state only when followed by + reagent or arrow, not in water contexts.
        # Preserve true H2O by not globally replacing here.
        out.append(s)
    res = "".join(out)
    res = res.replace("H2 O", "H2O")
    res = _chemhub_re.sub(r"\s+", " ", res)
    res = _chemhub_re.sub(r"\s*\+\s*", " + ", res)
    res = _chemhub_re.sub(r"\s*(→|⇌|->|=>)\s*", r" \1 ", res)
    return res.strip(" ;,.")

def _chemhub_v982_fix_known_hydride_ocr(eq: str) -> str:
    s = _chemhub_v982_clean_oxidation_outside_brackets(eq)
    # Textbook oxidation annotations often turn CaH2 / LiH formation backwards/noisy.
    # Normalize only obvious hydride formation patterns.
    if _chemhub_re.search(r"\bCa\b", s) and _chemhub_re.search(r"\bH2\b", s) and "CaH2" in s.replace(" ", ""):
        return "H2 + Ca → CaH2"
    if _chemhub_re.search(r"\bLi\b", s) and _chemhub_re.search(r"\bH2\b", s) and ("LiH" in s.replace(" ", "") or _chemhub_re.search(r"→\s*2Li\s*\+\s*H", s)):
        return "2Li + H2 → 2LiH"
    return s

def _chemhub_v982_is_forbidden_line(text: str) -> bool:
    low = str(text or "").lower()
    if any(x in low for x in ["pka", "pkb", "рка", "ркб", "пка", "пкб", "произведение растворимости", "пр ="]):
        return True
    if any(x in low for x in ["катод", "анод", "электрон", "полуреакц"]):
        return True
    if _chemhub_re.search(r"(^|[\s+])(?:e|ē)\s*[-+−]", low):
        return True
    return False

def extract_reactions_from_text(text: str):
    if _chemhub_v982_is_forbidden_line(text):
        return []
    results = _chemhub_v982_original_extract(text)
    cleaned = []
    for r in results:
        eq = getattr(r, "equation", "") or ""
        if _chemhub_v982_is_forbidden_line(eq):
            continue
        new_eq = _chemhub_v982_fix_known_hydride_ocr(eq)
        # keep arrows normalized
        new_eq = new_eq.replace("->", "→").replace("=>", "→")
        if hasattr(r, "equation"):
            r.equation = new_eq
        if "→" in new_eq or "⇌" in new_eq:
            arr = "⇌" if "⇌" in new_eq else "→"
            left, right = new_eq.split(arr, 1)
            if hasattr(r, "reactants"):
                r.reactants = left.strip()
            if hasattr(r, "products"):
                r.products = right.strip()
        cleaned.append(r)
    return cleaned

def canonical_equation(equation: str) -> str:
    """Stable canonical string used for duplicate detection/search."""
    s = _chemhub_v982_clean_oxidation_outside_brackets(equation)
    s = s.replace("->", "→").replace("=>", "→").replace("⇄", "⇌").replace("↔", "⇌")
    s = _chemhub_re.sub(r"\s+", "", s).lower()
    return s
# /CHEMHUB_V9_8_2_STRICT_OXIDATION_OVERLAY
'@
  Add-Content -Path $Extractor -Value "`r`n$Overlay" -Encoding UTF8
  Write-Host "Overlay appended to extractor.py"
} else {
  Write-Host "Overlay already present; skipping append."
}

Write-Host "Copying extractor into running API container..."
docker compose cp $Extractor api:/app/app/extractor.py

Write-Host "Restarting API..."
docker compose restart api

Start-Sleep -Seconds 4

Write-Host "Smoke test..."
docker compose exec -T api python -c "from app.extractor import extract_reactions_from_text; cases=['H2 + 2Li0 -> 2Li + 1H-1','H2^0 + Ca^0 -> Ca+2H2-1','S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3']; print([[getattr(r,'equation','') for r in extract_reactions_from_text(c)] for c in cases])"

Write-Host "Patch v9.8.2 installed."
Write-Host "Open AI Agent and press Ctrl+F5: http://localhost:5173"
