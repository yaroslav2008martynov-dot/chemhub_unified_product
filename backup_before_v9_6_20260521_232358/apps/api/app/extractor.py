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
for group_num, elements in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI,
    "щелочные металлы": ALKALI,
    "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH,
    "щелочноземельные металлы": ALKALINE_EARTH,
    "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS,
    "hal": HALOGENS,
    "halogens": HALOGENS,
    "гал": HALOGENS,
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

TEMPLATE_VARS = ["M", "X", "Hal", "Me", "E", "Э"]
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(M|X|Hal|Me|E|Э)(?![a-zа-я])")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%−]*)")
REJECT_WORDS_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|баланс|также)\b", re.I)
ELECTRON_RE = re.compile(r"(?:^|\s|\+)(?:e|ē|е)\s*(?:[-−]|\^?[-−+]|⁻)", re.I)
PK_RE = re.compile(r"\b(?:pKa|pKb|pKа|pKб|pH|ПР|Ksp|pK)\b|pKa\s*=|pKb\s*=|ПР\s*=", re.I)
FREE_ION_RE = re.compile(r"(?<![A-Za-z0-9\]])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|MnO4|Cr2O7|[A-Z][a-z]?\d*)(?:\^?\d?[+\-−]|[⁺⁻])(?:\b|\s|$)")

DESCRIPTIVE_PARENS = {
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "гидрид", "гидриды", "сульфид", "сульфиды",
    "нитрид", "нитриды", "карбид", "карбиды", "фосфид", "фосфиды",
    "силицид", "силициды", "самовозгорание", "без горения", "горит", "взрыв",
    "бурная реакция", "ядовитый газ", "осадок", "газ", "кислота", "основание", "соль",
}
REACTION_NAME_HINTS = ["синтез", "метод", "реакция", "процесс", "основание", "магическая кислота"]
POLYMER_ALIAS_HINTS = ["тефлон", "полиэтилен", "капрон"]
KEEP_PARENS_HINTS = ["конц", "разб", "%", "красн", "бел", "черн", "ж", "тв", "газ", "р-р", "расплав", "ромб"]

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
    validation_status: str = "ready"
    impossible_note: str = ""


def _protect_brackets(text: str) -> tuple[str, list[str]]:
    protected: list[str] = []
    def repl(m: re.Match) -> str:
        protected.append(m.group(0))
        return f"@@BR{len(protected)-1}@@"
    return re.sub(r"\[[^\]]+\](?:\d*[+\-−])?", repl, text), protected


def _restore_brackets(text: str, protected: list[str]) -> str:
    for i, value in enumerate(protected):
        text = text.replace(f"@@BR{i}@@", value)
    return text


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    text = text.replace("⟶", "→").replace("=>", "→").replace("->", "→")
    text = text.replace("<=>", "⇌").replace("<->", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("∙", "·").replace("−", "-")
    text = text.replace("° С", "°C").replace("° C", "°C").replace("o C", "°C").replace("oC", "°C")
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def _normalize_cyrillic_elements(text: str) -> str:
    # Replace look-alike letters only in likely formula fragments. Avoid corrupting Russian names such as "Миллона".
    mapping = str.maketrans({"А": "A", "В": "B", "С": "C", "Е": "E", "К": "K", "Н": "H", "О": "O", "Р": "P", "Т": "T", "Х": "X"})
    def repl(m: re.Match) -> str:
        return m.group(0).translate(mapping)
    return re.sub(r"(?<![А-Яа-я])(?:[АВСКЕНРОТХ][a-zа-я]?\d*|[A-Z][а-я]\d*)(?:[0-9A-Za-zА-Яа-я()\[\]+\-^]*)", repl, text)


def _remove_oxidation_outside_brackets(text: str) -> str:
    text = re.sub(r"\[([A-Z][a-z]?)\s*\+\s*\d+\s*(\([^\]]+\)\d*)\]", r"[\1\2]", text)
    tmp, protected = _protect_brackets(text)
    # H2^0 / H2⁰ / H20 in textbook oxidation-state notation means H2, not H2O.
    tmp = re.sub(r"\bH2\s*(?:\^?0|⁰)\b", "H2", tmp)
    tmp = re.sub(r"\bH20\b", "H2", tmp)
    # Common OCR oxidations attached to products.
    tmp = re.sub(r"H2\s*\+\s*1\s*([A-Z])", r"H2\1", tmp)
    tmp = re.sub(r"H2\+1([A-Z])", r"H2\1", tmp)
    # Element oxidation states outside complexes: Al+3, Ga + 3, Ca0, H-1.
    tmp = re.sub(r"\b([A-Z][a-z]?)(?:\s*\+\s*\d+|\+\d+|\s*-\s*\d+|-\d+|\^\d+[+\-]|\^?0|[⁰¹²³⁴⁵⁶⁷⁸⁹]+)\b(?=\s*(?:\+|→|⇌|$|[A-Z(]))", r"\1", tmp)
    tmp = re.sub(r"([A-Z][a-z]?\d+(?:[A-Z][a-z]?\d*)*)-\d+(?=\s|$|\+|→|⇌)", r"\1", tmp)
    return _restore_brackets(tmp, protected)


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    text = _normalize_cyrillic_elements(text)
    text = text.replace("H₂O", "H2O").replace("H₂", "H2")
    text = text.replace("O₂", "O2").replace("Cl₂", "Cl2")
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)
    text = _remove_oxidation_outside_brackets(text)
    # Space plus signs only outside bracketed complex ions so charges like [S8^2+] survive.
    tmp, protected = _protect_brackets(text)
    tmp = re.sub(r"\s*\+\s*", " + ", tmp)
    tmp = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", tmp)
    tmp = re.sub(r"\s+", " ", tmp).strip()
    text = _restore_brackets(tmp, protected)
    return _clean_spaces(text)


def _join_unique(values: list[str]) -> str:
    out: list[str] = []
    for v in values:
        v = _clean_spaces(v)
        if v and v not in out:
            out.append(v)
    return "; ".join(out)


def normalize_condition(cond: str) -> dict[str, list[str]]:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "states": []}
    if not cond:
        return data
    c_low = cond.lower()
    # Keep original arrow-condition text exactly enough for site display.
    for m in re.finditer(r"\b\d{2,4}\s*[–-]\s*\d{2,4}\s*°?\s*C\b", cond, flags=re.I):
        data["temperature"].append(re.sub(r"\s*°?\s*C\b", " °C", m.group(0), flags=re.I).replace("-", "–"))
    range_spans = []
    for m in re.finditer(r"\b\d{2,4}\s*[–-]\s*\d{2,4}\s*°?\s*C\b", cond, flags=re.I):
        range_spans.append(m.span())
    for m in re.finditer(r"\b\d{1,4}\s*(?:°\s*C|°C|C)\b", cond, flags=re.I):
        if any(a <= m.start() and m.end() <= b for a,b in range_spans):
            continue
        val = re.sub(r"\s*(?:°\s*C|°C|C)\b", " °C", m.group(0), flags=re.I)
        data["temperature"].append(val)
    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))
    if re.search(r"(^|\s|,)(t|heat|delta|Δ|нагрев)(\s|,|$)", cond, flags=re.I):
        data["conditions"].append("t" if re.search(r"(^|\s|,)t(\s|,|$)", cond, flags=re.I) else "нагревание")
    if "электролиз" in c_low or "эл. ток" in c_low or "electric" in c_low or "elec" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе" in c_low:
        m = re.search(r"в токе\s*[A-ZА-Я][A-Za-zА-Яа-я0-9]*", cond, flags=re.I)
        data["conditions"].append(m.group(0) if m else "в токе")
    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "CrO3", "HNO3", "NaF"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in c_low or solv in cond:
            data["solvents"].append(solv)
    if "so2 ж" in c_low or "so2 жид" in c_low:
        data["conditions"].append("SO2 ж")
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b|\bp\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))
    # Anything written above the arrow but not classified must still be shown above the arrow.
    stripped = cond
    stripped = re.sub(r"\b\d{2,4}\s*[–-]\s*\d{2,4}\s*°?\s*C\b", " ", stripped, flags=re.I)
    stripped = re.sub(r"\b\d{1,4}\s*(?:°\s*C|°C|C)\b", " ", stripped, flags=re.I)
    stripped = re.sub(r"\b\d{2,5}\s*K\b", " ", stripped)
    for key in ["catalysts", "solvents", "pressure", "conditions"]:
        for v in data[key]:
            stripped = stripped.replace(v, "")
    stripped = re.sub(r"[,;\s]+", " ", stripped).strip(" ,;")
    if stripped and stripped.lower() not in {"ж", "тв", "г", "газ", "liq"} and not PK_RE.search(stripped):
        data["conditions"].append(stripped)
    return data


def merge_meta(*metas: dict[str, list[str]]) -> dict[str, list[str]]:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "states": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _extract_trailing_parenthetical(right: str) -> tuple[str, str, str]:
    """Return cleaned right, reaction_name, alias."""
    name = ""
    alias = ""
    m = re.search(r"\(([^()]*)\)\s*$", right)
    if not m:
        return right, name, alias
    inner = m.group(1).strip()
    low = inner.lower()
    if any(h in low for h in REACTION_NAME_HINTS):
        name = inner
        right = right[:m.start()].strip()
    elif any(h in low for h in POLYMER_ALIAS_HINTS):
        alias = inner
        right = right[:m.start()].strip()
    elif low in DESCRIPTIVE_PARENS or any(w in low for w in DESCRIPTIVE_PARENS):
        right = right[:m.start()].strip()
    elif re.fullmatch(r"[A-Z][a-z]?(?:\s*,\s*[A-Z][a-z]?)*", inner):
        # handled later as parenthetical element substitution
        pass
    elif any(h in low for h in KEEP_PARENS_HINTS):
        pass
    elif re.search(r"[А-Яа-я]{3,}|кч\s*=|форма", inner, re.I):
        right = right[:m.start()].strip()
    return right, name, alias


def split_equation_and_conditions(line: str) -> tuple[str | None, dict[str, list[str]], str]:
    line = fix_ocr_formula(line)
    if not line:
        return None, normalize_condition(""), ""
    if "≠" in line:
        left = line.split("≠", 1)[0].strip()
        return f"{left} ≠", {**normalize_condition(""), "conditions": ["не реагируют"]}, ""
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), ""
    reaction_name = ""
    # A -> condition -> B
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if any(a.group(1) == "⇌" for a in arrows[:2]) or re.search(r"\bp\b|кат", middle, re.I) else "→"
        right, name, alias = _extract_trailing_parenthetical(right)
        reaction_name = name or alias
        return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(middle), reaction_name
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    right, name, alias = _extract_trailing_parenthetical(right)
    reaction_name = name or alias
    return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(""), reaction_name


def _strip_bracketed_for_ion_check(eq: str) -> str:
    tmp, _ = _protect_brackets(eq)
    return tmp


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq or not ("→" in eq or "⇌" in eq or "≠" in eq):
        return False
    if PK_RE.search(eq) or REJECT_WORDS_RE.search(eq) or ELECTRON_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        # keep polymerization examples such as nC2F4 -> (-C2F4-)n
        if "(-" not in eq and "−" not in eq:
            return False
    if "≠" in eq:
        return bool(FORMULA_TOKEN_RE.search(eq.split("≠", 1)[0]))
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if right.strip().endswith("+") or left.strip().endswith("+"):
        return False
    # Free ions are skipped; bracketed coordination compounds and special clusters are allowed.
    ion_check = _strip_bracketed_for_ion_check(eq)
    if FREE_ION_RE.search(ion_check):
        return False
    if re.search(r"(?:^|\s|\+)H\s*\+\s*\+", eq):
        return False
    # Reject obvious lost-product/mass nonsense from OCR.
    if canonical_side(left) == canonical_side(right):
        return False
    if re.fullmatch(r"2?H2O\s*\+\s*O2", left.strip()) and "H2O" in right and "H2" not in right:
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs: dict[str, list[str]] = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            if "M" not in defs:
                defs["M"] = values
            if "hal" in key or "гал" in key:
                defs["X"] = values
                defs["Hal"] = values
    for m in re.finditer(r"(?<![А-Яа-яA-Za-z])(M|X|Hal|Me|E|Э)\s*(?:=|->|→)\s*([^;)]+)", text):
        var, raw = m.group(1), m.group(2)
        vals: list[str] = []
        for part in re.split(r"[,;\s]+", raw):
            p = part.strip(" .()")
            if p in GROUP_ALIASES:
                vals.extend(GROUP_ALIASES[p])
            elif re.fullmatch(r"[A-Z][a-z]?", p):
                vals.append(p)
        if vals:
            defs[var] = list(dict.fromkeys(vals))
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
        candidates = [e for e in elements if PERIODIC_GROUP.get(e) == group and e != alt]
        if candidates:
            out.append(re.sub(rf"\b{candidates[-1]}\b", alt, base))
    return list(dict.fromkeys(out))


def expand_templates(eq: str, context: str) -> list[str]:
    # Never expand letters inside Russian reaction names such as "основание Миллона".
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found: list[str] = []
    for v in TEMPLATE_VARS:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append(v)
            elif v == "Me" and "M" in defs:
                defs["Me"] = defs["M"]
                vars_found.append(v)
            else:
                return []
    base = re.sub(r"\([^)]*(?:=|->|→)[^)]*\)", "", eq).strip()
    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def canonical_token(token: str) -> str:
    token = _clean_spaces(token).lower()
    token = token.translate(str.maketrans({"₀":"0","₁":"1","₂":"2","₃":"3","₄":"4","₅":"5","₆":"6","₇":"7","₈":"8","₉":"9","⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9","⁺":"+","⁻":"-"}))
    token = token.replace(" ", "")
    token = re.sub(r"^[0-9]+", "", token)  # ignore coefficients for duplicate matching
    return token


def canonical_side(side: str) -> str:
    parts = [canonical_token(p) for p in re.split(r"\s*\+\s*", side) if canonical_token(p)]
    return "+".join(sorted(parts))


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation)
    if "≠" in eq:
        return "no_reaction:" + canonical_side(eq.split("≠", 1)[0])
    if "⇌" in eq:
        left, right = eq.split("⇌", 1)
    elif "→" in eq:
        left, right = eq.split("→", 1)
    else:
        return canonical_token(eq)
    sides = sorted([canonical_side(left), canonical_side(right)])
    return "↔".join(sides)


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while cur.rstrip().endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt.startswith("+"):
                cur = cur.rstrip() + " " + nxt[1:].strip()
            else:
                cur = cur.rstrip() + " " + nxt
            i += 1
        merged.append(cur)
        i += 1
    return merged


def _score_reaction(r: ExtractedReaction) -> int:
    return len(r.equation or "") + 6 * bool(r.temperature) + 6 * bool(r.conditions) + 6 * bool(r.catalysts) + 6 * bool(r.solvents) + 10 * bool(r.reaction_name)


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_wrapped_lines(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx - 5): min(len(lines), idx + 4)])
        eq, meta, name = split_equation_and_conditions(raw)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate):
                continue
            if "≠" in candidate:
                left = candidate.split("≠", 1)[0].strip()
                reactions.append(ExtractedReaction(
                    equation=f"{left} ≠",
                    reactants=left,
                    products="",
                    conditions="не реагируют",
                    confidence_score=0.95,
                    reaction_name=name,
                    validation_status="does_not_react",
                    impossible_note="не реагируют между собой",
                ))
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(),
                products=right.strip(),
                conditions=_join_unique(meta["conditions"]),
                catalysts=_join_unique(meta["catalysts"]),
                solvents=_join_unique(meta["solvents"]),
                temperature=_join_unique(meta["temperature"]),
                pressure=_join_unique(meta["pressure"]),
                states=_join_unique(meta["states"]),
                confidence_score=0.92,
                reaction_name=name,
            ))
    # De-duplicate and keep the most informative version.
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _score_reaction(r) > _score_reaction(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
