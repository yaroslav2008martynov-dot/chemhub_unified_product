import itertools
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

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

PERIODIC_GROUP: Dict[str, int] = {}
for group_num, elements in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные металлы": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS, "гал": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%−]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(M|X|Hal|Me|E|Э)(?![a-zа-я])")

# Reject obvious non-reaction / ionic / constants.
REJECT_LINE_RE = re.compile(
    r"(?:\bкатод\b|\bанод\b|полуреакц|электрон|электрод|pK[ab]|pKa|pKb|рК[аб]|рКа|рКб|ПР\s*=|Ksp|solubility product|констант)",
    re.IGNORECASE,
)
FREE_ELECTRON_RE = re.compile(r"(^|[\s+])(e|ē|e⁻|e-)\b|(?:\b(e|ē)\s*[-+])", re.IGNORECASE)
FREE_ION_RE = re.compile(
    r"(^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|NH4|[A-Z][a-z]?\d*)\s*(?:\^?\d?\s*[+-]|[⁺⁻]|[+-])(?=\s|$|\+)",
)

CLASS_COMMENT_RE = re.compile(
    r"^\s*(?:"
    r"оксид(?:ы)?|пероксид(?:ы)?|надпероксид(?:ы)?|озонид(?:ы)?|"
    r"галогенид(?:ы)?|хлорид(?:ы)?|фторид(?:ы)?|бромид(?:ы)?|иодид(?:ы)?|"
    r"гидрид(?:ы)?|сульфид(?:ы)?|нитрид(?:ы)?|карбид(?:ы)?|фосфид(?:ы)?|борид(?:ы)?|силицид(?:ы)?|"
    r"кислот[аы]?|основани[ея]|соль|соли|газ|осадок|"
    r"самовозгорание|без\s+горения|бурная\s+реакция|взрыв|ядовитый\s+газ"
    r")\s*$",
    re.IGNORECASE,
)
NAMED_REACTION_RE = re.compile(r"(синтез|метод|реакция|процесс|основание\s+Миллона|магическая\s+кислота)", re.IGNORECASE)

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
    review_reason: str = ""


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    replacements = {
        "⟶": "→", "->": "→", "=>": "→",
        "<->": "⇌", "<=>": "⇌", "↔": "⇌", "⇄": "⇌",
        "∙": "·", "–": "-", "—": "-", "−": "-", "⁻": "-", "⁺": "+",
        "℃": "°C",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([А-Яа-яA-Za-z])\.\.", r"\1.", text)
    return text


def _protect_brackets(text: str) -> Tuple[str, List[str]]:
    chunks = []
    def repl(m):
        chunks.append(m.group(0))
        return f"§BR{len(chunks)-1}§"
    return re.sub(r"\[[^\]]+\]", repl, text), chunks


def _restore_brackets(text: str, chunks: List[str]) -> str:
    for i, chunk in enumerate(chunks):
        text = text.replace(f"§BR{i}§", chunk)
    return text


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    # Cyrillic look-alikes in common element symbols only. Do not translate whole Russian names.
    tr = str.maketrans({
        "А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X",
        "а":"a","с":"c","е":"e","о":"o","р":"p","х":"x",
    })
    # Apply transliteration mostly to formula-looking substrings.
    text = re.sub(r"(?<![А-Яа-я])([АВСЕКМНОРТХасеорхA-Za-z0-9\[\]\(\)\+\-\^·]+)(?![А-Яа-я])", lambda m: m.group(1).translate(tr), text)

    # Preserve + between substances.
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)

    # H2 with printed oxidation state must be H2, not H2O.
    text = re.sub(r"\bH[₂2][\^⁰0](?=\s*(?:\+|→|⇌|$))", "H2", text)
    text = re.sub(r"\bH20(?=\s*\+\s*(?:S|CuO|Ca|N2|F2|Cl2|Br2|I2)\b)", "H2", text)
    text = re.sub(r"\bH20\b", "H2O", text)
    text = text.replace("Н20", "H2O").replace("H₂O", "H2O").replace("H₂", "H2")

    # Gas / precipitate markers.
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)

    protected, chunks = _protect_brackets(text)
    # Remove printed oxidation states outside complex brackets.
    protected = re.sub(r"(?<!\[)(\b[A-Z][a-z]?\d*)\s*(?:\^?0|\+ ?[1-8]|- ?[1-8])(?=\b|[A-Z(\s+→⇌]|$)", r"\1", protected)
    protected = re.sub(r"\bH2\+1(?=[A-Z])", "H2", protected)
    protected = re.sub(r"([A-Z][a-z]?\d*)\+\d+(?=[A-Z])", r"\1", protected)
    text = _restore_brackets(protected, chunks)

    # Remove oxidation state accidentally placed inside complex formula: [Al + 3(OH)4] -> [Al(OH)4]
    text = re.sub(r"\[([A-Z][a-z]?)\s*\+\s*[1-8]\s*(\([^)]+\)\d*)\]", r"[\1\2]", text)
    text = re.sub(r"\[([A-Z][a-z]?)\+?[1-8](\([^)]+\)\d*)\]", r"[\1\2]", text)

    # Normalize charges inside square brackets but keep them.
    text = re.sub(r"\[([A-Za-z0-9]+)\^?(\d+)([+-])\]", r"[\1^\2\3]", text)
    text = re.sub(r"\[([A-Za-z0-9]+)([+-])\]", r"[\1\2]", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data

    c_low = cond.lower()
    # Keep original condition phrase for above-arrow display as much as possible.
    raw_for_conditions = cond

    # Temperature: supports ranges 120-150 °C and Kelvin with number only.
    for m in re.finditer(r"\b\d{1,4}\s*[-–]\s*\d{1,4}\s*(?:°\s*C|°C|o\s*C|C)\b", cond, flags=re.I):
        val = re.sub(r"o\s*C|C\b", "°C", m.group(0), flags=re.I)
        val = re.sub(r"\s*-\s*", "-", val).replace("° C", "°C")
        data["temperature"].append(val)
    for m in re.finditer(r"\b\d{1,4}\s*(?:°\s*C|°C|o\s*C)\b", cond, flags=re.I):
        val = re.sub(r"o\s*C", "°C", m.group(0), flags=re.I).replace("° C", "°C")
        if val not in data["temperature"]:
            data["temperature"].append(val)
    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))

    if re.fullmatch(r"t|Δ|hv|hν|heat|нагрев(?:ание)?", cond, flags=re.I):
        data["conditions"].append(cond)
    elif re.search(r"(^|\s|,)(t|Δ|hv|hν|heat|нагрев)(\s|,|$)", cond, flags=re.I):
        data["conditions"].append("t" if re.search(r"(^|\s|,)t(\s|,|$)", cond) else "нагревание")

    if "электролиз" in c_low or "эл. ток" in c_low or "electric" in c_low or "elec" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе" in c_low:
        data["conditions"].append(re.search(r"в\s+токе\s+[A-Za-zА-Яа-я0-9]+", cond, re.I).group(0) if re.search(r"в\s+токе\s+[A-Za-zА-Яа-я0-9]+", cond, re.I) else "в токе")

    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "CrO3", "HNO3", "NaF"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2", "SO2 ж", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in c_low or solv in cond:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b|(^|\s)p($|\s|,)", cond, flags=re.I):
        data["pressure"].append(p.group(0).strip())

    # Always keep raw above-arrow label too, except when it is already only a temperature.
    if raw_for_conditions and raw_for_conditions not in data["conditions"] and not (data["temperature"] and raw_for_conditions in data["temperature"]):
        data["conditions"].append(raw_for_conditions)

    return data


def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _strip_comment_from_right(right: str) -> Tuple[str, str]:
    """Remove class/description comments; return right side and reaction_name."""
    right = right.strip()
    reaction_name = ""
    m = re.search(r"\(([^()]*)\)\s*$", right)
    if not m:
        return right, reaction_name
    inner = m.group(1).strip()
    inner_low = inner.lower()

    if NAMED_REACTION_RE.search(inner):
        reaction_name = inner
        right = right[:m.start()].strip()
        return right, reaction_name

    # product alias like (тефлон) should be name/alias, not equation.
    if inner_low in {"тефлон", "полиэтилен", "капрон"}:
        reaction_name = inner
        right = right[:m.start()].strip()
        return right, reaction_name

    # remove classes/comments.
    if CLASS_COMMENT_RE.match(inner) or re.search(r"(ид|аты|иты|оксид|пероксид|карбид|фосфид|гидрид|галогенид)ы?$", inner_low):
        right = right[:m.start()].strip()
        return right, reaction_name

    # Keep color/state/concentration annotations as part of equation for site subnote rendering.
    return right, reaction_name


def _extract_trailing_condition(side: str) -> Tuple[str, dict]:
    """Extract OCR condition accidentally appended before/after arrow."""
    side = side.strip()
    meta = normalize_condition("")
    patterns = [
        r"(.+?)\s+(\d{1,4}\s*[-–]\s*\d{1,4}\s*(?:°\s*C|°C|o\s*C|C))$",
        r"(.+?)\s+(\d{1,4}\s*(?:°\s*C|°C|o\s*C))$",
        r"(.+?)\s+(t|Δ|hv|hν)$",
        r"(.+?)\s+((?:CrO3|HNO3|F2|NaF|желатин|ацетон|SO2\s*ж)(?:\s*,\s*(?:CrO3|HNO3|F2|NaF|желатин|ацетон|SO2\s*ж))*)$",
    ]
    for pat in patterns:
        m = re.match(pat, side, flags=re.I)
        if m and FORMULA_TOKEN_RE.search(m.group(1)):
            return m.group(1).strip(), normalize_condition(m.group(2).strip())
    return side, meta


def split_equation_and_conditions(line: str) -> Tuple[Optional[str], dict, str]:
    line = fix_ocr_formula(line)
    if "≠" in line:
        left = line.split("≠", 1)[0].strip()
        return f"{left} ≠", normalize_condition(""), ""

    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), ""

    # A -> condition -> B
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) else "→"
        right, reaction_name = _strip_comment_from_right(right)
        eq = fix_ocr_formula(f"{left} {arrow} {right}")
        return eq, normalize_condition(middle), reaction_name

    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()

    left, meta_left = _extract_trailing_condition(left)
    right, reaction_name = _strip_comment_from_right(right)
    right, meta_right = _extract_trailing_condition(right)

    return fix_ocr_formula(f"{left} {arrow} {right}"), merge_meta(meta_left, meta_right), reaction_name


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq:
        return False
    if REJECT_LINE_RE.search(eq) or FREE_ELECTRON_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if "≠" in eq:
        return FORMULA_TOKEN_RE.search(eq.split("≠", 1)[0] or "") is not None
    if not ("→" in eq or "⇌" in eq):
        return False

    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if right.strip().endswith("+") or left.strip().endswith("+"):
        return False
    # Free ions are skipped; bracketed complex charges are allowed.
    if FREE_ION_RE.search(eq) and "[" not in eq:
        return False
    # pKa/pKb/PR equations are acid/base ionic notes, not molecular reactions.
    if re.search(r"pK[ab]|pKa|pKb|рК[аб]|ПР|Ksp", eq, re.I):
        return False
    # Reject clearly broken "same product lost" examples.
    compact_left = re.sub(r"\s+|\d+(?=[A-Z\[])", "", left)
    compact_right = re.sub(r"\s+|\d+(?=[A-Z\[])", "", right)
    if compact_right and compact_left.endswith(compact_right) and len(right.strip()) < 8:
        return False
    if re.search(r"\b2H2O\s*\+\s*O2\s*→\s*2H2O\b", eq):
        return False
    return True


def parse_definitions(text: str) -> Dict[str, List[str]]:
    defs: Dict[str, List[str]] = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "hal" in key or "гал" in key:
                defs["X"] = values
                defs["Hal"] = values

    # Only parse variable definitions in formula context. Do not touch names like "основание Миллона".
    for m in re.finditer(r"(?<![А-Яа-яA-Za-z])(M|X|Hal|Me|E|Э)\s*(?:=|->|→)\s*([^;)]+)", text):
        var, raw = m.group(1), m.group(2)
        vals = []
        for part in re.split(r"[,;\s]+", raw):
            p = part.strip(" .()")
            if p in GROUP_ALIASES:
                vals.extend(GROUP_ALIASES[p])
            elif re.fullmatch(r"[A-Z][a-z]?", p):
                vals.append(p)
        if vals:
            defs[var] = list(dict.fromkeys(vals))
    return defs


def infer_parenthetical_substitution(eq: str) -> List[str]:
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


def expand_templates(eq: str, context: str) -> List[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)

    vars_found = []
    for v in ["M", "X", "Hal", "Me", "E", "Э"]:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]; vars_found.append(v)
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


def _merge_wrapped_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        while cur.endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if "→" not in nxt and "⇌" not in nxt and not nxt.startswith(("Свойства", "Методы", "Также")):
                cur = cur.rstrip("+").strip() + " + " + nxt.lstrip("+").strip()
                i += 1
            else:
                break
        out.append(cur)
        i += 1
    return out


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation).lower()
    eq = re.sub(r"\([^)]*(?:оксид|карбид|фосфид|галогенид|самовозгорание|без горения)[^)]*\)", "", eq)
    if "≠" in eq:
        side = eq.split("≠", 1)[0]
        terms = sorted([re.sub(r"\s+", "", x) for x in side.split("+") if x.strip()])
        return "noreact:" + "+".join(terms)
    arrow = "⇌" if "⇌" in eq else "→"
    if arrow not in eq:
        return re.sub(r"\s+", "", eq)
    left, right = eq.split(arrow, 1)
    def norm_side(s: str) -> str:
        # remove leading coefficients only for duplicate detection
        terms = [re.sub(r"^\d+(?=[a-z\[])", "", re.sub(r"\s+", "", t)) for t in s.split("+") if t.strip()]
        return "+".join(sorted(terms))
    a, b = norm_side(left), norm_side(right)
    # A+B -> C+D and C+D -> A+B are duplicates for catalog purposes.
    return "⇄".join(sorted([a, b]))


def extract_reactions_from_text(text: str) -> List[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_wrapped_lines(raw_lines)
    reactions: List[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        if REJECT_LINE_RE.search(raw) or FREE_ELECTRON_RE.search(raw):
            continue
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+4)])
        eq, meta, reaction_name = split_equation_and_conditions(raw)
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
                    reactants=left, products="",
                    conditions="не реагируют между собой",
                    confidence_score=0.88,
                    reaction_name=reaction_name,
                    review_reason="does_not_react",
                ))
                continue

            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            display_conditions = "; ".join(meta["conditions"])
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(), products=right.strip(),
                conditions=display_conditions,
                catalysts="; ".join(meta["catalysts"]),
                solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]),
                pressure="; ".join(meta["pressure"]),
                states="",
                confidence_score=0.92,
                reaction_name=reaction_name,
                review_reason="",
            ))

    # Deduplicate: keep the richer record.
    dedup: Dict[str, ExtractedReaction] = {}
    def score(r: ExtractedReaction) -> int:
        return sum(len(str(getattr(r, field, "") or "")) for field in ["conditions","catalysts","solvents","temperature","pressure","reaction_name"]) + len(r.equation)
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or score(r) > score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
