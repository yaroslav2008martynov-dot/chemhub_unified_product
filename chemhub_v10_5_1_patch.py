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
    r"\s+(?:M|X|Hal|Me|E|[A-Z][a-z]?)\s*=\s*(?:[A-Z][a-z]?|alkali|alkaline|halogens?|С‰РµР»РѕС‡РЅС‹Рµ|С‰РµР»РѕС‡РЅРѕР·РµРјРµР»СЊРЅС‹Рµ|РіР°Р»РѕРіРµРЅС‹)(?:\s*,\s*(?:[A-Z][a-z]?))*\s*$",
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
