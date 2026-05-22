import re
from dataclasses import replace, is_dataclass

ARROW_RE = re.compile(r"\s*(→|⇌|->|=>|<->|<=>)\s*")
GROUP1 = {"Li","Na","K","Rb","Cs"}
GROUP2 = {"Be","Mg","Ca","Sr","Ba"}

_SUP = str.maketrans({
    "⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9",
    "⁺":"+","⁻":"-","−":"-","–":"-","—":"-",
})

def _protect_brackets(s: str):
    saved = []
    def repl(m):
        saved.append(m.group(0))
        return f"@@BR{len(saved)-1}@@"
    return re.sub(r"\[[^\]]+\](?:\s*(?:\^?\s*[+-]?\d*[+-]|[+-]?\d*[+-]))?", repl, s), saved

def _restore_brackets(s: str, saved):
    for i, val in enumerate(saved):
        s = s.replace(f"@@BR{i}@@", val)
    return s

def strip_oxidation_marks(text: str) -> str:
    """Remove oxidation-state annotations everywhere except protected complex/cluster brackets."""
    if not text:
        return text
    s = str(text).translate(_SUP)
    s = s.replace("^+", "+").replace("^-", "-")
    s, saved = _protect_brackets(s)

    # OCR oxidation marks over/after simple species: H2^0, Ca0, Li0, Al+3, H-1, +1H, etc.
    s = re.sub(r"\b([A-Z][a-z]?)(\d*)\s*\^\s*0\b", r"\1\2", s)
    s = re.sub(r"\b([A-Z][a-z]?)(\d*)0(?=\s*(?:\+|→|⇌|->|=>|$|\)))", r"\1\2", s)
    s = re.sub(r"\b([A-Z][a-z]?)(\d*)\s*\^?\s*[+-]\s*\d+\b", r"\1\2", s)
    s = re.sub(r"\b([A-Z][a-z]?)(\d*)\s*\^?\s*\d+\s*[+-]\b", r"\1\2", s)
    # Prefix oxidation state before element, e.g. +1H, -1Cl.
    s = re.sub(r"(?<![A-Za-z0-9])(?:[+-]\s*\d+|\d+\s*[+-])\s*([A-Z][a-z]?)(\d*)", r"\1\2", s)
    # OCR split: Al + 3(OH)4 -> Al(OH)4; Ga + 3(OH)4 -> Ga(OH)4.
    s = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*\d+\s*(?=\()", r"\1", s)
    # Remove remaining oxidation attached to terminal H like H-1, H+1.
    s = re.sub(r"\bH\s*[+-]\s*\d+\b", "H", s)

    s = _restore_brackets(s, saved)
    s = re.sub(r"\s*([+])\s*", r" + ", s)
    s = re.sub(r"\s*(→|⇌)\s*", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip(" ;,.")
    return s

def _split_eq(eq: str):
    eq = eq.replace("->", "→").replace("=>", "→").replace("<->", "⇌").replace("<=>", "⇌")
    m = re.search(r"(→|⇌)", eq)
    if not m:
        return None
    return eq[:m.start()].strip(), m.group(1), eq[m.end():].strip()

def _metal_coeff(side: str, metal: str):
    m = re.search(rf"(?:^|\+)\s*(\d*)\s*{re.escape(metal)}\b", side)
    if not m:
        return None
    return int(m.group(1) or "1")

def repair_simple_hydride_ocr(eq: str) -> str:
    """Fix OCR products where oxidation states turned hydrides into M + H annotations."""
    parts = _split_eq(eq)
    if not parts:
        return eq
    left, arrow, right = parts
    # Only if H2 is a reactant and right side contains a bare metal plus bare H.
    if not re.search(r"(?:^|\+)\s*H2\b", left):
        return eq
    for metal in sorted(GROUP1 | GROUP2, key=len, reverse=True):
        if not re.search(rf"(?:^|\+)\s*{re.escape(metal)}\b", left):
            continue
        if not re.search(rf"(?:^|\+)\s*\d*\s*{re.escape(metal)}\b", right):
            continue
        if not re.search(r"(?:^|\+)\s*\d*\s*H\b", right):
            continue
        if metal in GROUP1:
            return f"2{metal} + H2 {arrow} 2{metal}H"
        return f"{metal} + H2 {arrow} {metal}H2"
    return eq

def normalize_reaction_equation(eq: str) -> str:
    eq = strip_oxidation_marks(eq)
    eq = repair_simple_hydride_ocr(eq)
    eq = strip_oxidation_marks(eq)
    return eq

def patch_extractor_module(mod):
    if getattr(mod, "_strict_oxidation_layer_applied", False):
        return
    base = mod.extract_reactions_from_text
    def wrapped_extract_reactions_from_text(text):
        rows = base(text)
        out = []
        for r in rows:
            eq = normalize_reaction_equation(getattr(r, "equation", ""))
            parts = _split_eq(eq)
            if not parts:
                continue
            left, arrow, right = parts
            try:
                r.equation = eq
                r.reactants = left
                r.products = right
            except Exception:
                if is_dataclass(r):
                    r = replace(r, equation=eq, reactants=left, products=right)
            out.append(r)
        return out
    mod.extract_reactions_from_text = wrapped_extract_reactions_from_text
    mod._strict_oxidation_layer_applied = True
