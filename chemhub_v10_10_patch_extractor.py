from pathlib import Path
import re

path = Path("apps/api/app/extractor.py")
s = path.read_text(encoding="utf-8")
orig = s

# 1) OCR rule: Hв‚‚вЃ° is often read as H20. Include O2 and other elementary reagents.
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
        return f"{left_coef}H2 + O2 в†’ {right_coef}H2O"

    text = re.sub(
        r"\b(\d*)H2O\s*\+\s*O2\s*в†’\s*(\d*)H2O\b",
        _fix_h2_o2,
        text,
    )

    # Earlier textbook cases with H2^0 read as H2O.
    text = re.sub(r"\bH2O\s*\+\s*S\s*в†’\s*H2S\b", "H2 + S в†’ H2S", text)
    text = re.sub(r"\bH2O\s*\+\s*CuO\s*в†’\s*Cu\s*\+\s*H2O\b", "H2 + CuO в†’ Cu + H2O", text)
    text = re.sub(r"\bH2O\s*\+\s*Ca\s*в†’\s*CaH2\b", "H2 + Ca в†’ CaH2", text)

    # Remove any leftover oxidation-state fragments that survived OCR normalization.
    text = re.sub(r"([A-Z][a-z]?\d*)\s*\+\s*1(?=[A-Z])", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?\d*)\s*-\s*\d+(?=($|[\s+в†’в‡Њв‰ ),]))", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?\d*)\s*\+\s*\d+(?=($|[\s+в†’в‡Њв‰ ),]))", r"\1", text)
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
