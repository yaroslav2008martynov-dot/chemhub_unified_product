import itertools
import re
from dataclasses import dataclass

ARROW = "→"
REV_ARROW = "⇌"
UP = "↑"
DOWN = "↓"
NOT_REACT = "≠"

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

PERIODIC_GROUP = {}
for group_num, elements in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI,
    "щелочные металлы": ALKALI,
    "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH,
    "щелочноземельные металлы": ALKALINE_EARTH,
    "щелочно-земельные металлы": ALKALINE_EARTH,
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

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:n|\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|\([^)]*[A-Z][^)]*\)n?|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-z])(M|X|Hal|Me|E|Э)(?![a-z])")

# Explanations in parentheses that must not become part of equation.
CLASSIFICATION_WORDS = [
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "гидрид", "гидриды", "сульфид", "сульфиды",
    "нитрид", "нитриды", "карбид", "карбиды", "фосфид", "фосфиды", "силицид", "силициды",
    "соль", "соли", "кислота", "основание", "осадок", "газ",
    "самовозгорание", "без горения", "бурная реакция", "взрыв", "ядовитый газ",
]
NAME_HINTS = ["синтез", "метод", "процесс", "реакция", "рашиг", "байер", "габер", "бош", "магическая кислота", "тефлон"]
KEEP_PAREN_HINTS = ["конц", "разб", "%", "расплав", "красн", "бел", "черн", "ромб", "монок", "α", "β", "γ"]

SUPERSCRIPTS = str.maketrans({
    "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9", "⁺": "+", "⁻": "-",
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
})
CYR_FORMULA = str.maketrans({"А":"A", "В":"B", "С":"C", "Е":"E", "К":"K", "М":"M", "Н":"H", "О":"O", "Р":"P", "Т":"T", "Х":"X"})

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


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    text = text.translate(SUPERSCRIPTS)
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("⟶", "→").replace("⟼", "→").replace("->", "→").replace("=>", "→")
    text = text.replace("∙", "·").replace("−", "-").replace("—", "-").replace("–", "-")
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def _protect_brackets(text: str):
    protected = []
    def repl(m):
        protected.append(m.group(0))
        return f"§BR{len(protected)-1}§"
    return re.sub(r"\[[^\]]+\]", repl, text), protected


def _restore_brackets(text: str, protected: list[str]) -> str:
    for i, value in enumerate(protected):
        text = text.replace(f"§BR{i}§", value)
    return text


def _normalize_bracket_content(text: str) -> str:
    # Remove oxidation-state annotations inside complexes such as [Al + 3(OH)4] -> [Al(OH)4]
    def fix(m):
        inner = m.group(1)
        inner = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*[123456]\s*(?=\()", r"\1", inner)
        inner = re.sub(r"\b([A-Z][a-z]?)\s*\^?\s*[+-]\s*[123456]\s*(?=\()", r"\1", inner)
        inner = re.sub(r"\s+", "", inner)
        return f"[{inner}]"
    return re.sub(r"\[([^\]]+)\]", fix, text)


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    text = text.translate(CYR_FORMULA)
    text = _normalize_bracket_content(text)

    # Gas / precipitate markers.
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)

    # H2 with oxidation state zero must not become H2O.
    text = re.sub(r"\b(\d*)H2\^?0\b", lambda m: (m.group(1) or "") + "H2", text)
    # OCR often writes H2^0 as H20 in redox sections. If it is a reagent, prefer H2.
    text = re.sub(r"\b(\d*)H20(?=\s*\+|\s*→|\s*⇌)", lambda m: (m.group(1) or "") + "H2", text)
    text = re.sub(r"\bH20\b", "H2O", text)
    text = text.replace("H₂O", "H2O").replace("H₂", "H2")

    # Printed oxidation states attached to usual formulas.
    text = re.sub(r"H2\+1(?=O|S|Se|Te|F|Cl|Br|I|N)", "H2", text)
    text = re.sub(r"\b([A-Z][a-z]?)(?:\^?0)\b", r"\1", text)
    text = re.sub(r"\b([A-Z][A-Za-z0-9()]*)[+-]\d+(?=$|\s|\+|→|⇌|\))", r"\1", text)

    # Do not remove charges inside bracketed complexes/clusters.
    text2, br = _protect_brackets(text)
    # Remove oxidation states before ordinary formula continuation, not before '[' (e.g. C+24[HSO4]- is preserved).
    text2 = re.sub(r"\b([A-Z][a-z]?\d*)\+\d+(?=\()", r"\1", text2)
    text2 = re.sub(r"\b([A-Z][a-z]?\d*)\+\d+(?=[A-Z])", r"\1", text2)
    text2 = re.sub(r"\b([A-Z][a-z]?\d*)-\d+(?=[A-Z])", r"\1", text2)
    text = _restore_brackets(text2, br)

    # Keep charge plus signs such as C+24 and H2SO3F+ intact; only normalize separator pluses that already have surrounding spaces.
    text = re.sub(r"\s+\+\s+", " + ", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _clean_spaces(text)


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    data = {"raw": [], "conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    cond = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", cond, flags=re.I)
    cond = re.sub(r"(\d+)\s*-\s*(\d+)\s*(?:°\s*C|°C|o\s*C|C)\b", r"\1–\2 °C", cond, flags=re.I)
    cond = re.sub(r"(\d+)\s*(?:°\s*C|°C|o\s*C|C)\b", r"\1 °C", cond, flags=re.I)
    cond = re.sub(r"\s*,\s*", ", ", cond).strip(" ,")
    if cond:
        data["raw"].append(cond)

    low = cond.lower()
    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}(?:–\d{1,4})?\s*°C\b", cond, flags=re.I):
        data["temperature"].append(m.group(0))
    if re.fullmatch(r"t", cond.strip(), flags=re.I) or re.search(r"(^|[,\s])(t|heat|delta|Δ|нагрев)($|[,\s])", cond, flags=re.I):
        data["conditions"].append("t" if re.search(r"(^|[,\s])t($|[,\s])", cond, flags=re.I) else "нагревание")
    if re.search(r"(^|[,\s])p($|[,\s])", cond, flags=re.I):
        data["pressure"].append("p")
    if "электролиз" in low or "эл. ток" in low or "эл ток" in low or "electric" in low or "elec" in low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in low or "melt" in low:
        data["conditions"].append("расплав")
    if "в токе" in low:
        m = re.search(r"в\s+токе\s+[A-Za-z0-9]+", cond, flags=re.I)
        data["conditions"].append(m.group(0) if m else "в токе")
    for cat in ["Rh / Pt", "Rh/Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "CrO3", "AlCl3", "FeCl3", "NaF", "F2"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["желатин", "ацетон", "CCl4", "SO2", "SO2 ж", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in low or solv in cond:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))
    return data


def _unique_join(values: list[str]) -> str:
    out = []
    for v in values:
        v = _clean_spaces(v)
        if v and v not in out:
            out.append(v)
    return "; ".join(out)


def merge_meta(*metas: dict) -> dict:
    out = {"raw": [], "conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "reaction_name": []}
    for meta in metas:
        for key in out:
            vals = meta.get(key, []) if isinstance(meta.get(key, []), list) else [meta.get(key)]
            for val in vals:
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def extract_parenthetical_metadata(eq: str) -> tuple[str, dict, list[str] | None]:
    """Return equation without trailing human notes, metadata, and substitution alternatives."""
    meta = {"reaction_name": []}
    alternatives = None
    eq = _clean_spaces(eq)
    m = re.search(r"\(([^()]*)\)\s*$", eq)
    if not m:
        return eq, meta, alternatives
    inner = m.group(1).strip()
    low = inner.lower()
    if re.fullmatch(r"\s*[A-Z][a-z]?(?:\s*,\s*[A-Z][a-z]?)*\s*", inner):
        alternatives = [x.strip() for x in inner.split(",")]
        return eq[:m.start()].strip(), meta, alternatives
    if any(h in low for h in NAME_HINTS):
        meta["reaction_name"].append(inner)
        return eq[:m.start()].strip(), meta, alternatives
    if any(h in low for h in KEEP_PAREN_HINTS):
        return eq, meta, alternatives
    if any(w in low for w in CLASSIFICATION_WORDS) or re.search(r"[А-Яа-я]{4,}", inner):
        return eq[:m.start()].strip(), meta, alternatives
    return eq, meta, alternatives


def split_equation_and_conditions(line: str, previous_condition: str = "") -> tuple[str | None, dict, list[str] | None, bool]:
    line = fix_ocr_formula(line)
    line = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", line, flags=re.I)
    neg = "≠" in line
    if neg:
        left = line.split("≠", 1)[0].strip()
        if FORMULA_TOKEN_RE.search(left):
            meta = normalize_condition(previous_condition)
            meta["conditions"].append("не реагирует")
            return f"{left} ≠", meta, None, True
        return None, {}, None, False

    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(previous_condition), None, False

    # A -> condition -> B
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) else "→"
        meta = merge_meta(normalize_condition(previous_condition), normalize_condition(middle))
        eq, pmeta, alternatives = extract_parenthetical_metadata(f"{left} {arrow} {right}")
        meta = merge_meta(meta, pmeta)
        # Haber-Bosch hint: t,p,kat.(Fe) over reversible arrow.
        if "kat" in middle.lower() or "кат" in middle.lower():
            if re.search(r"\bFe\b", middle):
                meta["catalysts"].append("Fe")
        return fix_ocr_formula(eq), meta, alternatives, False

    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    meta = normalize_condition(previous_condition)
    eq, pmeta, alternatives = extract_parenthetical_metadata(f"{left} {arrow} {right}")
    meta = merge_meta(meta, pmeta)
    return fix_ocr_formula(eq), meta, alternatives, False


def _is_short_condition(line: str) -> bool:
    line = _clean_spaces(line)
    if not line or "→" in line or "⇌" in line or "≠" in line or len(line) > 80:
        return False
    if re.search(r"\d+\s*(?:-|–)?\s*\d*\s*(°\s*C|°C|o\s*C|K)\b", line, re.I):
        return True
    if re.fullmatch(r"(?:t|p|t\s*,\s*p|кат\.?\s*\([^)]*\)|[A-Za-z0-9]+(?:\s+ж)?)(?:\s*,\s*[^,]+)*", line, re.I):
        return True
    if any(x in line.lower() for x in ["желатин", "ацетон", "в токе", "электролиз", "расплав", "или", "кат"]):
        return True
    return False


def looks_like_reaction(eq: str, negative: bool = False) -> bool:
    eq = _clean_spaces(eq)
    if negative:
        return bool(eq and "≠" in eq and FORMULA_TOKEN_RE.search(eq))
    if not eq or not ("→" in eq or "⇌" in eq):
        return False
    # Strict reject for non molecular equations / half reactions.
    if re.search(r"\b(катод|анод|электрон|полуреакц|баланс|также)\b", eq, re.I):
        return False
    if re.search(r"(?:\b|\s)(e|ē)\s*[-+]?", eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if eq.strip().endswith("+"):
        return False
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    # Reject obvious free ions / ionic equations, but allow bracket complexes and cluster charges.
    free_ionic = re.search(r"(?:^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|Mg|Ca|In|Fe|Cu|Ag|Al)\d*(?:\^?\d?[+-]|[+-])(?=\s|\+|$)", eq)
    if free_ionic and "магическая" not in eq.lower():
        return False
    # Reject absurd same-side/lost-product examples.
    if canonical_key(eq).startswith("invalid:"):
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs: dict[str, list[str]] = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "hal" in key or "гал" in key:
                defs["X"] = values
                defs["Hal"] = values
    for m in re.finditer(r"\b(M|X|Hal|Me|E|Э|Al)\s*(?:=|->|→)\s*([^;)]+)", text):
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
    # Common textbook shorthand: (Al -> Al, Ga, In) applies variable Al as family anchor.
    if "Al" in defs and "M" not in defs:
        defs["M"] = defs["Al"]
    return defs


def infer_parenthetical_substitution(eq: str, alternatives: list[str] | None = None) -> list[str]:
    if not alternatives:
        return [eq]
    base = eq.strip()
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


def expand_templates(eq: str, context: str, alternatives: list[str] | None = None) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq, alternatives)
    vars_found = []
    for v in ["M", "X", "Hal", "Me", "E", "Э"]:
        if re.search(rf"(?<![A-Za-z]){re.escape(v)}(?![a-z])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append(v)
            else:
                return []
    base = re.sub(r"\([^)]*(?:=|->|→)[^)]*\)", "", eq).strip()
    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-z]){re.escape(v)}(?![a-z])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def _split_side(side: str) -> list[str]:
    return sorted([re.sub(r"^\d+(?:[,.]\d+)?\s*", "", p.strip()).lower() for p in side.split("+") if p.strip()])


def canonical_key(eq: str) -> str:
    eq = fix_ocr_formula(eq)
    if "≠" in eq:
        return "negative:" + re.sub(r"\s+", "", eq.lower())
    if "→" not in eq and "⇌" not in eq:
        return "invalid:noarrow"
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    lset, rset = _split_side(left), _split_side(right)
    if not lset or not rset:
        return "invalid:empty"
    # Product side should not be a strict subset/same as reactants with extra oxygen/reactant lost.
    if set(rset).issubset(set(lset)):
        return "invalid:lost_product"
    a = "+".join(lset)
    b = "+".join(rset)
    return "⇄".join(sorted([a, b]))


def _metadata_score(r: ExtractedReaction) -> int:
    return sum(len(x or "") for x in [r.conditions, r.catalysts, r.solvents, r.temperature, r.pressure, r.reaction_name]) + len(r.equation)


def _merge_continuation_lines(lines: list[str]) -> list[str]:
    merged = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while cur.rstrip().endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt.startswith("+"):
                cur = cur.rstrip() + " " + nxt.lstrip("+ ")
                i += 1
            else:
                break
        merged.append(cur)
        i += 1
    return merged


def _make_reaction(eq: str, meta: dict, negative: bool = False) -> ExtractedReaction | None:
    eq = fix_ocr_formula(eq)
    if negative:
        reactants = eq.split("≠", 1)[0].strip()
        return ExtractedReaction(equation=eq, reactants=reactants, products="", conditions="не реагирует", confidence_score=0.85, reaction_name="не реагирует")
    if not looks_like_reaction(eq):
        return None
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    arrow = "⇌" if "⇌" in eq else "→"
    raw_conditions = []
    raw_conditions.extend(meta.get("raw", []))
    # conditions displayed above arrow: keep raw arrow text first, plus important extracted conditions not already present.
    for k in ["conditions", "temperature", "pressure", "catalysts", "solvents"]:
        for v in meta.get(k, []):
            if v and not any(v in r for r in raw_conditions):
                raw_conditions.append(v)
    return ExtractedReaction(
        equation=f"{left.strip()} {arrow} {right.strip()}",
        reactants=left.strip(),
        products=right.strip(),
        conditions=_unique_join(raw_conditions or meta.get("conditions", [])),
        catalysts=_unique_join(meta.get("catalysts", [])),
        solvents=_unique_join(meta.get("solvents", [])),
        temperature=_unique_join(meta.get("temperature", [])),
        pressure=_unique_join(meta.get("pressure", [])),
        states="",
        confidence_score=0.92,
        reaction_name=_unique_join(meta.get("reaction_name", [])),
    )


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_continuation_lines(lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        prev = lines[idx - 1] if idx > 0 and _is_short_condition(lines[idx - 1]) else ""
        context = " ".join(lines[max(0, idx - 5): min(len(lines), idx + 4)])
        eq, meta, alternatives, negative = split_equation_and_conditions(raw, prev)
        if not eq:
            continue
        if negative:
            r = _make_reaction(eq, meta, negative=True)
            if r:
                reactions.append(r)
            continue
        for candidate in expand_templates(eq, context, alternatives):
            candidate = fix_ocr_formula(candidate)
            r = _make_reaction(candidate, meta)
            if r:
                reactions.append(r)

    # Deduplicate by canonical sides, including reversed equations; keep the richest item.
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_key(r.equation)
        if key.startswith("invalid:"):
            continue
        if key not in dedup or _metadata_score(r) > _metadata_score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
