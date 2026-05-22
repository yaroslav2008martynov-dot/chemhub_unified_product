from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

ARROW = "→"
REV_ARROW = "⇌"
NEG_ARROW = "≠"
UP = "↑"
DOWN = "↓"

ALKALI = ["Li", "Na", "K", "Rb", "Cs"]
ALKALINE_EARTH = ["Be", "Mg", "Ca", "Sr", "Ba"]
HALOGENS = ["F", "Cl", "Br", "I"]
CHALCOGENS = ["O", "S", "Se", "Te"]
PNICTOGENS = ["N", "P", "As", "Sb", "Bi"]
GROUP_13 = ["B", "Al", "Ga", "In", "Tl"]
GROUP_14 = ["C", "Si", "Ge", "Sn", "Pb"]
GROUP_15 = PNICTOGENS
GROUP_16 = CHALCOGENS
GROUP_17 = HALOGENS

PERIODIC_GROUP: dict[str, int] = {}
for group_num, elements in [
    (1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14),
    (15, GROUP_15), (16, GROUP_16), (17, GROUP_17),
]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные": ALKALI, "щелочные металлы": ALKALI, "alkali": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH,
    "alkaline earth": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "галоген": HALOGENS, "гал": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(
    r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?|[A-Z])"
    r"(?:[A-Za-z0-9()\[\].·\-+↑↓%]*)"
)
TEMPLATE_VARS_RE = re.compile(r"(Hal|Me|M|X|E|Э)(?![a-z])")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b")
BAD_CONTEXT_RE = re.compile(
    r"\b(катод|анод|электрон|полуреакц|электронн|баланс|pka|pkb|пка|пкб|пр\s*=|кsp|ksp)\b|[ē]",
    re.I,
)
FREE_ION_RE = re.compile(
    r"(^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(?:\^?\d*[+\-]|[⁺⁻])\s*(?=(?:[+→⇌]|$))"
)
EXPLANATION_WORDS = [
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "карбид", "карбиды", "фосфид", "фосфиды",
    "гидрид", "гидриды", "сульфид", "сульфиды", "нитрид", "нитриды", "силицид", "силициды",
    "самовозгорание", "без горения", "ядовитый газ", "также и все",
]
NAME_WORDS = [
    "синтез рашиг", "метод байер", "габер", "бош", "магическая кислота",
    "основание миллона", "тефлон", "процесс габера", "процесс габера-боша",
]
UNWANTED_INFO_RE = re.compile(
    r"\((?:\s*(?:lg|ln|pka|pkb|пка|пкб|пр|кsp|ksp)\s*[\w()]*\s*[=≈~<>].*?)\)"
    r"|(?:\s*(?:lg|ln|pka|pkb|пка|пкб|пр|кsp|ksp)\s*[\w()]*\s*[=≈~<>]\s*[-−]?\d+(?:[,.]\d+)?(?:\s*·\s*10[-−]?\d+)?)",
    re.I,
)
CONDITION_ONLY_RE = re.compile(
    r"(^|[\s,])(t|p|hv|hν|Δ)([\s,]|$)"
    r"|\d{1,4}\s*(?:[-–]\s*\d{1,4}\s*)?(?:°\s*C|°C|o\s*C|C\b)"
    r"|\d{2,5}\s*K\b"
    r"|кат\.?|нагрев|электролиз|расплав|давлен|pressure|токе|водород|H2|желатин|ацетон|SO2\s*ж|CrO3|HNO3|P4O10|F2|NaF|Pt|Pd|Ni|Fe|MnO2|V2O5|AlCl3|FeCl3",
    re.I,
)

@dataclass
class ExtractedReaction:
    equation: str
    reactants: str
    products: str
    conditions: str = ""
    catalysts: str = ""
    solvents: str = ""
    temperature: str = ""
    pressure: str = ""
    states: str = ""
    confidence_score: float = 0.9
    reaction_name: str = ""


def _unique_join(items) -> str:
    out: list[str] = []
    for item in items:
        item = _clean_spaces(item)
        if item and item not in out:
            out.append(item)
    return "; ".join(out)


def _decode_mojibake(text: str) -> str:
    text = str(text or "")
    replacements = {
        "тЖТ": "→", "тЖУ": "↓", "тЖС": "↑", "тЙа": "≠",
        "╨║o╨╜╤Ж.": "конц.", "╨║╨╛╨╜╤Ж.": "конц.", "╨║онц.": "конц.",
        "pa╨╖╨▒.": "разб.", "╤А╨░╨╖╨▒.": "разб.", "╨╢.": "ж.",
        "┬╖": "·", "╬▒": "α", "╬▓": "β", "╨Ч": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _clean_spaces(text: str) -> str:
    text = _decode_mojibake(str(text or ""))
    replacements = {
        "\ufeff": "", "⟶": "→", "⟹": "→", "=>": "→", "->": "→",
        "<=>": "⇌", "<->": "⇌", "↔": "⇌", "⇄": "⇌", "⇔": "⇌",
        "=/=": "≠", "−": "-", "–": "-", "—": "-", "∙": "·", "⋅": "·",
        "оС": "°C", "o C": "°C", "oC": "°C", "Сo": "°C", "Со": "°C",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def _translate_lookalikes(text: str) -> str:
    tr = str.maketrans({
        "А": "A", "В": "B", "С": "C", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "Т": "T", "Х": "X",
        "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
        "⁺": "+", "⁻": "-",
    })
    return text.translate(tr)


def strip_oxidation_states(text: str) -> str:
    """Remove oxidation states / charges / superscript artifacts, keep normal indices."""
    text = _clean_spaces(_translate_lookalikes(text))

    # OCR from H₂⁰ can become H20. In redox reagent positions it is H2, not H2O.
    text = re.sub(r"\bH20(?=\s*(?:\+|→|⇌|$))", "H2", text)
    text = re.sub(r"\bH20(?=\s*[A-Z])", "H2", text)
    text = text.replace("H20", "H2O")

    # Bracket charges and any caret charge markers are not needed in your site database.
    text = re.sub(r"\[([^\]]*?)\s*\^\s*\d*\s*[+-]\]", r"[\1]", text)
    text = re.sub(r"\[([^\]]*?)(?:\d*\s*[+-])\]", r"[\1]", text)

    # Remove oxidation states attached to formulas/elements: H2^0, O2^0, Ca0, Ca+2, H-1, O-2.
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*\^\s*(?:0|[+-]\s*\d+)(?=($|[\s+→⇌≠),]))", r"\1", text)
    text = re.sub(r"\b([A-Z][a-z]?)0(?=($|[\s+→⇌≠),]))", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*[+-]\s*\d+(?=($|[\s+→⇌≠),]))", r"\1", text)

    # Al +3(OH)4 / Ga +3(OH)4 -> Al(OH)4 / Ga(OH)4.
    text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*\d+\s*(?=\()", r"\1", text)
    # + 1H -> + H; H-1 -> H.
    text = re.sub(r"(?<=[+→⇌]\s)\d+\s*H(?=($|[\s+]))", "H", text)
    text = re.sub(r"\bH(\d*)\s*[-+]\s*\d+\b", r"H\1", text)
    text = re.sub(r"\^\s*\d*\s*[+-]?", "", text)
    return _clean_spaces(text)


def _remove_unwanted_info(text: str) -> str:
    text = UNWANTED_INFO_RE.sub("", str(text or ""))
    text = re.sub(r"\(\s*\)", "", text)
    return _clean_spaces(text)


def _repair_known_oxidation_ocr(eq: str) -> str:
    """Fix cases where oxidation-state zero made H2 look like water."""
    eq = _clean_spaces(eq)
    # 2H2O + O2 -> 2H2O caused by H₂⁰ + O₂⁰ -> H₂O.
    eq = re.sub(r"\b2\s*H2O\s*\+\s*O2\s*→\s*2\s*H2O\b", "2H2 + O2 → 2H2O", eq)
    eq = re.sub(r"\bH2O\s*\+\s*S\s*→\s*H2S\b", "H2 + S → H2S", eq)
    eq = re.sub(r"\bH2O\s*\+\s*CuO\s*→\s*Cu\s*\+\s*H2O\b", "H2 + CuO → Cu + H2O", eq)
    eq = re.sub(r"\bH2O\s*\+\s*Ca\s*→\s*CaH2\b", "H2 + Ca → CaH2", eq)
    eq = re.sub(r"\bH2\s*\+\s*2(Li|Na|K|Rb|Cs)\s*→\s*2\1\s*\+\s*H\b", r"2\1 + H2 → 2\1H", eq)
    return eq


def fix_ocr_formula(text: str) -> str:
    text = _remove_unwanted_info(text)
    text = strip_oxidation_states(text)
    text = _repair_known_oxidation_ocr(text)
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)
    text = re.sub(r"H2\+1O", "H2O", text)
    text = re.sub(r"H2\+1S", "H2S", text)
    text = re.sub(r"\bCa\s*\+\s*H2\b", "CaH2", text)
    text = re.sub(r"\b(Mg|Sr|Ba)\s*\+\s*H2\b", r"\1H2", text)
    text = re.sub(r"\b(2\s*)?(Li|Na|K|Rb|Cs)\s*\+\s*H\b", lambda m: (m.group(1) or "") + m.group(2) + "H", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text)
    return _clean_spaces(_repair_known_oxidation_ocr(text))


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation).lower()
    eq = re.sub(r"\s+", "", eq)
    if "→" in eq:
        left, right = eq.split("→", 1)
    elif "⇌" in eq:
        left, right = eq.split("⇌", 1)
    elif "≠" in eq:
        left, right = eq.split("≠", 1)
    else:
        return eq
    def norm_side(side: str) -> str:
        tokens = [re.sub(r"^\d+(?:[,.]\d+)?", "", t) for t in side.split("+") if t]
        return "+".join(sorted(tokens))
    return "||".join(sorted([norm_side(left), norm_side(right)]))


def _normalize_condition_text(cond: str) -> str:
    cond = _remove_unwanted_info(cond)
    cond = _clean_spaces(cond)
    cond = re.sub(r"(\d)\s*°\s*C", r"\1 °C", cond)
    cond = re.sub(r"\bkat\b", "кат.", cond, flags=re.I)
    return cond.strip(" ,;")


def normalize_condition(cond: str) -> dict:
    cond = _normalize_condition_text(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    data["conditions"].append(cond)
    for m in re.finditer(r"\b\d{1,4}\s*-\s*\d{1,4}\s*°\s*C\b|\b\d{1,4}\s*°\s*C\b|\b\d{2,5}\s*K\b", cond, flags=re.I):
        data["temperature"].append(_normalize_condition_text(m.group(0)))
    if re.search(r"(^|[\s,])p([\s,]|$)|давлен|pressure", cond, flags=re.I):
        data["pressure"].append("p" if re.search(r"(^|[\s,])p([\s,]|$)", cond) else cond)
    for cat in ["Pt", "Pd", "Ni", "Fe", "Rh", "Rh/Pt", "Rh / Pt", "MnO2", "V2O5", "AlCl3", "FeCl3"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in cond.lower():
            data["solvents"].append(solv)
    return data


def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                val = _clean_spaces(val)
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _is_visual_condition_line(line: str) -> bool:
    line = _normalize_condition_text(line)
    if not line or len(line) > 90:
        return False
    if "→" in line or "⇌" in line or "≠" in line:
        return False
    if UNWANTED_INFO_RE.search(line):
        return False
    return bool(CONDITION_ONLY_RE.search(line))


def _attach_visual_condition_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = _clean_spaces(lines[i])
        if _is_visual_condition_line(cur) and i + 1 < len(lines):
            nxt = _clean_spaces(lines[i + 1])
            fixed = fix_ocr_formula(nxt)
            arrows = list(re.finditer(r"(→|⇌)", fixed))
            if len(arrows) == 1:
                arrow = arrows[0].group(1)
                left = fixed[:arrows[0].start()].strip()
                right = fixed[arrows[0].end():].strip()
                if left and right:
                    out.append(f"{left} {arrow} {cur} {arrow} {right}")
                    i += 2
                    continue
        out.append(cur)
        i += 1
    return out


def _strip_inline_definitions(text: str) -> str:
    text = re.sub(r"\s*\b(?:M|X|Hal|Me|E|Э)\s*(?:=|->|→|-)\s*[^;]+$", "", text)
    text = re.sub(r"\s*\([^)]*\b(?:M|X|Hal|Me|E|Э)\s*(?:=|->|→|-)[^)]*\)\s*$", "", text)
    return _clean_spaces(text)


def split_equation_and_conditions(line: str) -> tuple[str | None, dict, str]:
    line = fix_ocr_formula(line)
    reaction_name = ""
    if "≠" in line and "→" not in line and "⇌" not in line:
        left = line.split("≠", 1)[0].strip()
        if left:
            return f"{left} ≠", normalize_condition(""), reaction_name
    m = re.search(r"\(([^()]*)\)\s*$", line)
    if m:
        inner = _clean_spaces(m.group(1))
        ilow = inner.lower()
        if UNWANTED_INFO_RE.search(f"({inner})"):
            line = line[:m.start()].strip()
        elif any(w in ilow for w in NAME_WORDS):
            reaction_name = inner
            line = line[:m.start()].strip()
        elif any(w in ilow for w in EXPLANATION_WORDS):
            line = line[:m.start()].strip()
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), reaction_name
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if any(a.group(1) == "⇌" for a in arrows[:2]) else "→"
        eq = fix_ocr_formula(f"{left} {arrow} {right}")
        eq = _strip_inline_definitions(eq)
        return eq, normalize_condition(middle), reaction_name
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = _strip_inline_definitions(line[arrows[0].end():].strip())
    eq = fix_ocr_formula(f"{left} {arrow} {right}")
    eq = _strip_inline_definitions(eq)
    return eq, normalize_condition(""), reaction_name


def looks_like_reaction(eq: str) -> bool:
    eq = fix_ocr_formula(eq)
    if not eq or not ("→" in eq or "⇌" in eq or "≠" in eq):
        return False
    if BAD_CONTEXT_RE.search(eq) or ORGANIC_TEMPLATE_RE.search(eq) or FREE_ION_RE.search(eq):
        return False
    if re.search(r"\b(e|ē)\s*[-+]|\be[-+]\b", eq):
        return False
    if "≠" in eq and ("→" not in eq and "⇌" not in eq):
        return bool(FORMULA_TOKEN_RE.search(eq.split("≠", 1)[0]))
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if left.strip().endswith("+") or right.strip().endswith("+"):
        return False
    if TEMPLATE_VARS_RE.search(eq):
        return False
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if len(right.strip()) < 2:
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs: dict[str, list[str]] = {}
    text_norm = _clean_spaces(text).replace("М", "M").replace("Х", "X")
    low = text_norm.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "гал" in key or "hal" in key:
                defs["X"] = values
                defs["Hal"] = values
    for m in re.finditer(r"\b(M|X|Hal|Me|E|Э)\s*(?:=|->|→|-)\s*([^;)\n]+)", text_norm):
        var, raw = m.group(1), m.group(2)
        vals: list[str] = []
        raw_low = raw.lower()
        for key, values in GROUP_ALIASES.items():
            if key in raw_low:
                vals.extend(values)
        for part in re.split(r"[,;\s]+", raw):
            p = part.strip(" .()")
            if re.fullmatch(r"[A-Z][a-z]?", p):
                vals.append(p)
        if vals:
            defs[var] = list(dict.fromkeys(vals))
    if "Hal" in defs and "X" not in defs:
        defs["X"] = defs["Hal"]
    if "M" in defs and "Me" not in defs:
        defs["Me"] = defs["M"]
    return defs


def infer_parenthetical_substitution(eq: str) -> list[str]:
    m = re.search(r"\((\s*[A-Z][a-z]?(?:\s*,\s*[A-Z][a-z]?)*\s*)\)\s*$", eq)
    if not m:
        return [eq]
    alternatives = [x.strip() for x in m.group(1).split(",")]
    base = eq[:m.start()].strip()
    elements = re.findall(r"[A-Z][a-z]?", base)
    out = [base]
    for alt in alternatives:
        group = PERIODIC_GROUP.get(alt)
        if not group:
            continue
        candidates = [e for e in elements if PERIODIC_GROUP.get(e) == group and e != alt]
        if candidates:
            out.append(re.sub(rf"\b{candidates[-1]}\b", alt, base))
    return list(dict.fromkeys(out))


def _replace_template_var(text: str, var: str, val: str) -> str:
    if var == "Hal":
        return re.sub(r"Hal", val, text)
    return re.sub(rf"{re.escape(var)}(?![a-z])", val, text)


def expand_templates(eq: str, context: str) -> list[str]:
    eq = fix_ocr_formula(eq).replace("М", "M").replace("Х", "X")
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found: list[str] = []
    for v in ["Hal", "Me", "M", "X", "E", "Э"]:
        if re.search(rf"{re.escape(v)}(?![a-z])", eq):
            if v in defs:
                vars_found.append(v)
            else:
                return []
    base = _strip_inline_definitions(re.sub(r"\([^)]*(?:=|->|→|-)[^)]*\)", "", eq).strip())
    expanded: list[str] = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = _replace_template_var(cur, v, val)
        cur = fix_ocr_formula(cur)
        if not TEMPLATE_VARS_RE.search(cur):
            expanded.append(cur)
    return list(dict.fromkeys(expanded))


def _merge_broken_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        while cur.endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            cur = cur + " " + nxt.lstrip("+ ").strip()
            i += 1
        merged.append(cur)
        i += 1
    return merged


def _score(r: ExtractedReaction) -> int:
    return sum(len(getattr(r, f, "") or "") for f in ["equation", "conditions", "catalysts", "solvents", "temperature", "pressure", "states", "reaction_name"])


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _attach_visual_condition_lines(_merge_broken_lines(raw_lines))
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx - 5): min(len(lines), idx + 5)])
        if BAD_CONTEXT_RE.search(raw):
            continue
        eq, meta, reaction_name = split_equation_and_conditions(raw)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate):
                continue
            if "≠" in candidate and "→" not in candidate and "⇌" not in candidate:
                left, right, arrow = candidate.split("≠", 1)[0].strip(), "", "≠"
            else:
                left, right = re.split(r"→|⇌", candidate, maxsplit=1)
                arrow = "⇌" if "⇌" in candidate else "→"
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}".strip(),
                reactants=left.strip(),
                products=right.strip(),
                conditions=_unique_join(meta["conditions"]),
                catalysts=_unique_join(meta["catalysts"]),
                solvents=_unique_join(meta["solvents"]),
                temperature=_unique_join(meta["temperature"]),
                pressure=_unique_join(meta["pressure"]),
                states="",
                confidence_score=0.94,
                reaction_name=reaction_name,
            ))
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _score(r) > _score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
