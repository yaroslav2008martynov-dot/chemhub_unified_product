from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

ARROW = "→"
REV_ARROW = "⇌"
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
    (1, ALKALI),
    (2, ALKALINE_EARTH),
    (13, GROUP_13),
    (14, GROUP_14),
    (15, GROUP_15),
    (16, GROUP_16),
    (17, GROUP_17),
]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI,
    "щелочные": ALKALI,
    "щелочные металлы": ALKALI,
    "alkali": ALKALI,
    "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH,
    "щелочноземельные": ALKALINE_EARTH,
    "щелочноземельные металлы": ALKALINE_EARTH,
    "alkaline earth": ALKALINE_EARTH,
    "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS,
    "галоген": HALOGENS,
    "гал": HALOGENS,
    "hal": HALOGENS,
    "halogen": HALOGENS,
    "halogens": HALOGENS,
    "халькогены": CHALCOGENS,
    "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS,
    "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13,
    "14 группа": GROUP_14,
    "15 группа": GROUP_15,
    "16 группа": GROUP_16,
    "17 группа": GROUP_17,
    "group 13": GROUP_13,
    "group 14": GROUP_14,
    "group 15": GROUP_15,
    "group 16": GROUP_16,
    "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(
    r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+↑↓%]*)"
)
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(Hal|Me|M|X|E|Э)(?![a-zа-я])")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b")
BAD_CONTEXT_RE = re.compile(
    r"\b(катод|анод|электрон|полуреакц|электронн|баланс|также|pka|pkb|пка|пкб|пр\s*=|ПР\s*=)\b|[ē]",
    re.I,
)
BAD_METADATA_RE = re.compile(r"\b(pka\d*|pkb\d*|пка\d*|пкб\d*|пр\s*=|ПР\s*=|lg\s*\(|lg\s*[A-Za-zА-Яа-я]?\s*=|кч\s*=)", re.I)
FREE_ION_RE = re.compile(
    r"(^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(?:\^?\d*[+\-]|[⁺⁻])\s*(?=(?:[+→⇌]|$))"
)

# Words in parentheses that are explanations, not reaction equations.
EXPLANATION_WORDS = [
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "карбид", "карбиды", "фосфид", "фосфиды",
    "гидрид", "гидриды", "сульфид", "сульфиды", "нитрид", "нитриды", "силицид", "силициды",
    "самовозгорание", "без горения", "горит", "бурная реакция", "взрыв", "ядовитый газ",
    "форма", "кислота", "примесь", "также",
]
NAME_WORDS = [
    "синтез рашиг", "метод байер", "габер", "бош", "магическая кислота",
    "основание миллона", "тефлон", "процесс", "реакция",
]


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


def _unique_join(items: list[str]) -> str:
    out: list[str] = []
    for item in items:
        item = _clean_spaces(item)
        if item and item not in out:
            out.append(item)
    return "; ".join(out)


def _fix_mojibake(text: str) -> str:
    """Repair common cp866/UTF-8 mojibake that appears after OCR/export."""
    text = str(text or "")
    repl = {
        "тЖТ": "→",
        "тЖТ": "→",
        "тЖУ": "↓",
        "тЖС": "↑",
        "тЙа": "≠",
        "╨║╨╛╨╜╤Ж.": "конц.",
        "╨║o╨╜╤Ж.": "конц.",
        "pa╨╖╨▒.": "разб.",
        "╤А╨░╨╖╨▒.": "разб.",
        "╨╢.": "ж.",
        "╨│.": "г.",
        "╤В╨▓.": "тв.",
        "┬╖": "·",
        "╬▒": "α",
        "╬▓": "β",
        "╨Ч": "",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    return text


def _clean_spaces(text: str) -> str:
    text = _fix_mojibake(str(text or ""))
    text = text.replace("\ufeff", "")
    text = text.replace("⟶", "→").replace("⟹", "→").replace("=>", "→").replace("->", "→")
    text = text.replace("<=>", "⇌").replace("<->", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("∙", "·").replace("⋅", "·")
    text = text.replace("оС", "°C").replace("oC", "°C").replace("o C", "°C")
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def _translate_lookalikes(text: str) -> str:
    # Do not translate Cyrillic М globally in prose such as "основание Миллона";
    # this function is applied only to formula-like strings.
    tr = str.maketrans(
        {
            "А": "A", "В": "B", "С": "C", "Е": "E", "К": "K", "Н": "H", "О": "O", "Р": "P", "Т": "T", "Х": "X",
            "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
            "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
            "⁺": "+", "⁻": "-",
        }
    )
    return text.translate(tr)


def strip_oxidation_states(text: str) -> str:
    """Remove printed oxidation-state marks. Keep normal formula indices."""
    text = _clean_spaces(_translate_lookalikes(text))
    # H2^0 / Ca0 / Al+3 / H-1 are oxidation states, not formula indices.
    # Remove explicit oxidation notation. Be careful not to damage valid indices like P4O10.
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*\^\s*(?:0|[+-]\s*\d+)(?=($|[\s+→⇌),]))", r"\1", text)
    text = re.sub(r"(?<![A-Za-z])([A-Z][a-z]?)0\b", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*[+-]\s*\d+(?=($|[\s+→⇌),]))", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?)(?:[+-]\s*\d+)(?=[A-Z(\[])", r"\1", text)
    text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*\d+\s*(?=\()", r"\1", text)  # Al + 3(OH)4 -> Al(OH)4
    text = re.sub(r"(?<=[+→⇌]\s)\d+\s*H(?=($|[\s+]))", "H", text)
    text = re.sub(r"\bH(\d*)\s*-\s*\d+\b", r"H\1", text)
    text = re.sub(r"\bH(\d*)\+\s*\d+\b", r"H\1", text)
    # User asked: no superscript charges in final equations either.
    # Remove only compact charges like ^2+ or 2+ at the end of a bracketed complex token,
    # never the plus signs that separate reagents.
    text = re.sub(r"(\[[^\]]+\])\^?\d*[+-](?=\s|$|,)", r"\1", text)
    return _clean_spaces(text)


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    text = strip_oxidation_states(text)
    text = text.replace("H20", "H2O").replace("H₂O", "H2O").replace("H₂", "H2")
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
    return _clean_spaces(text)


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

    a, b = norm_side(left), norm_side(right)
    return "||".join(sorted([a, b]))


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    # Conditions must be exact text over the arrow. Do not move "конц.", "разб.", "ж." from formulas.
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    if BAD_METADATA_RE.search(cond):
        return data
    data["conditions"].append(cond)
    return data


def parse_reaction_name_and_strip_explanations(line: str) -> tuple[str, str]:
    reaction_name = ""
    m = re.search(r"\(([^()]*)\)\s*$", line)
    if not m:
        return line, reaction_name
    inner = _clean_spaces(m.group(1))
    ilow = inner.lower()
    if BAD_METADATA_RE.search(inner):
        return line[:m.start()].strip(), reaction_name
    if any(w in ilow for w in NAME_WORDS):
        return line[:m.start()].strip(), inner
    if any(w in ilow for w in EXPLANATION_WORDS):
        return line[:m.start()].strip(), reaction_name
    return line, reaction_name


def split_equation_and_conditions(line: str) -> tuple[str | None, dict, str]:
    line = fix_ocr_formula(line)
    line, reaction_name = parse_reaction_name_and_strip_explanations(line)
    if BAD_CONTEXT_RE.search(line) or BAD_METADATA_RE.search(line):
        return None, normalize_condition(""), reaction_name
    if "≠" in line:
        left = line.split("≠", 1)[0].strip()
        return fix_ocr_formula(f"{left} ≠"), normalize_condition(""), reaction_name

    arrow_pat = r"(⇌|→)"
    arrows = list(re.finditer(arrow_pat, line))
    if not arrows:
        return None, normalize_condition(""), reaction_name

    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if any(a.group(1) == "⇌" for a in arrows[:2]) else "→"
        if re.search(r"кат\.?\s*\(?Fe\)?", middle, flags=re.I) and "N2" in left and "NH3" in right:
            arrow = "⇌"
            reaction_name = reaction_name or "Синтез аммиака (процесс Габера-Боша)"
        eq = fix_ocr_formula(f"{left} {arrow} {right}")
        return eq, normalize_condition(middle), reaction_name

    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(""), reaction_name


def looks_like_reaction(eq: str) -> bool:
    eq = fix_ocr_formula(eq)
    if not eq or not ("→" in eq or "⇌" in eq or "≠" in eq):
        return False
    if BAD_CONTEXT_RE.search(eq) or BAD_METADATA_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if FREE_ION_RE.search(eq) and "[" not in eq:
        return False
    if re.search(r"\b(e|ē)\s*[-+]|\be[-+]\b", eq):
        return False
    if "→" in eq or "⇌" in eq:
        left, right = re.split(r"→|⇌", eq, maxsplit=1)
        if left.strip().endswith("+") or right.strip().endswith("+"):
            return False
        if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
            return False
        if len(right.strip()) < 2:
            return False
    else:
        left = eq.split("≠", 1)[0]
        if not FORMULA_TOKEN_RE.search(left):
            return False
    if TEMPLATE_VARS_RE.search(eq) or re.search(r"(?<![a-zА-Яа-я])(M|X|Hal|Me|E|Э)(?![a-zа-я])", eq):
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
    for m in re.finditer(r"(?<![A-Za-zА-Яа-я])(Hal|Me|M|X|E|Э)\s*(?:=|->|→|-|—)\s*([^;)\n]+)", text_norm):
        var, raw = m.group(1), m.group(2)
        vals: list[str] = []
        raw_low = raw.lower()
        for key, values in GROUP_ALIASES.items():
            if key in raw_low:
                vals.extend(values)
        for part in re.split(r"[,;\s]+", raw):
            p = part.strip(" .()")
            if re.fullmatch(r"[A-Z][a-z]?", p) and p not in {"M", "X", "E"}:
                vals.append(p)
        if vals:
            defs[var] = list(dict.fromkeys(vals))
    return defs


def _strip_definition_tail(eq: str) -> str:
    # Remove "M = Li, Na, K" or "X = Cl" that OCR may place after the equation.
    return re.sub(r"\s+(?:Hal|Me|M|X|E|Э)\s*(?:=|->|→|-|—)\s*[^;)\n]+$", "", eq).strip()


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
        if not candidates:
            continue
        target = candidates[-1]
        out.append(re.sub(rf"\b{target}\b", alt, base))
    return list(dict.fromkeys(out))


def _replace_template_var(cur: str, var: str, val: str) -> str:
    if var == "X":
        # Replace X both as a token and inside products such as KX.
        return re.sub(r"(?<![a-zА-Яа-я])X(?![a-zа-я])", val, cur)
    if var == "M":
        return re.sub(r"(?<![A-Za-zА-Яа-я])M(?![a-zа-я])", val, cur)
    if var == "Me":
        return re.sub(r"(?<![A-Za-zА-Яа-я])Me(?![a-zа-я])", val, cur)
    if var == "Hal":
        return re.sub(r"(?<![A-Za-zА-Яа-я])Hal(?![a-zа-я])", val, cur)
    if var in ("E", "Э"):
        return re.sub(rf"(?<![A-Za-zА-Яа-я]){var}(?![a-zа-я])", val, cur)
    return cur


def expand_templates(eq: str, context: str) -> list[str]:
    eq = fix_ocr_formula(eq).replace("М", "M").replace("Х", "X")
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)

    vars_found: list[str] = []
    for v in ["Hal", "Me", "M", "X", "E", "Э"]:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq) or (v == "X" and "X" in eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append("X")
            elif v == "Me" and "M" in defs:
                defs["Me"] = defs["M"]
                vars_found.append("Me")
            else:
                return []

    base = _strip_definition_tail(eq)
    base = re.sub(r"\([^)]*(?:=|->|→|-|—)[^)]*\)", "", base).strip()
    expanded: list[str] = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = _replace_template_var(cur, v, val)
        expanded.append(fix_ocr_formula(cur))
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
    return sum(
        len(getattr(r, f, "") or "")
        for f in ["equation", "conditions", "catalysts", "solvents", "temperature", "pressure", "states", "reaction_name"]
    )


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_broken_lines(raw_lines)
    reactions: list[ExtractedReaction] = []

    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx - 5): min(len(lines), idx + 6)])
        eq, meta, reaction_name = split_equation_and_conditions(raw)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            candidate = re.sub(r"\b2(Li|Na|K|Rb|Cs)\s*\+\s*H2\s*→\s*2\1\s*\+\s*H\b", r"2\1 + H2 → 2\1H", candidate)
            if not looks_like_reaction(candidate):
                continue

            if "≠" in candidate:
                left = candidate.split("≠", 1)[0].strip()
                reactions.append(ExtractedReaction(
                    equation=f"{left} ≠",
                    reactants=left,
                    products="",
                    conditions=_unique_join(meta["conditions"]),
                    catalysts="",
                    solvents="",
                    temperature="",
                    pressure="",
                    states="",
                    confidence_score=0.92,
                    reaction_name=reaction_name,
                ))
                continue

            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            if "N2" in left and "NH3" in right and ("Fe" in _unique_join(meta["conditions"]) or "кат" in raw.lower()):
                arrow = "⇌"
                reaction_name = reaction_name or "Синтез аммиака (процесс Габера-Боша)"
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(),
                products=right.strip(),
                conditions=_unique_join(meta["conditions"]),
                catalysts="",
                solvents="",
                temperature="",
                pressure="",
                states="",
                confidence_score=0.92,
                reaction_name=reaction_name,
            ))

    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _score(r) > _score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
