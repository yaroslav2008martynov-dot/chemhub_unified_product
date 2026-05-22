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

PERIODIC_GROUP = {}
for n, els in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for e in els:
        PERIODIC_GROUP[e] = n

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные металлы": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "гал": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-z])(M|X|Hal|Me|E|Э|Al)(?![a-z])")
ELECTRODE_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|electron|cathode|anode)\b|\b(e|ē)\s*[-+]", re.I)
LIST_RE = re.compile(r"^\s*(также|например|минералы|свойства|методы|реагент|таблица)\b", re.I)

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
    reaction_name: str = ""
    reaction_kind: str = ""
    review_reason: str = ""
    confidence_score: float = 0.9


def _uniq(values):
    out = []
    for v in values:
        v = str(v or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    text = text.replace("⟶", "→").replace("⎯→", "→").replace("->", "→").replace("=>", "→")
    text = re.sub(r"\((M|X|Hal|Me|E|Э|Al)\s*→", r"(\1 =", text)
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("∙", "·").replace("−", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    # Cyrillic lookalikes that OCR often inserts into formulas.
    tr = str.maketrans({"А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X","а":"a","с":"c","е":"e","о":"o","р":"p","х":"x"})
    text = text.translate(tr)
    text = text.replace("H20", "H2O").replace("Н20", "H2O").replace("H₂O", "H2O").replace("H₂", "H2")
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)
    # Remove printed oxidation states from normal formula text, preserve bracketed complex charges.
    text = re.sub(r"H2\+1O", "H2O", text)
    text = re.sub(r"H2\+1S", "H2S", text)
    text = re.sub(r"(?<!\[)([A-Z][a-z]?)(?:0|[+-]\d+)(?=[A-Z(\s+]|$)", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?\d*)\+\d+(?=[A-Z])", r"\1", text)
    text = re.sub(r"([A-Za-z0-9)\]])\+1\b", r"\1", text)
    text = re.sub(r"([A-Za-z0-9)\]])\^0\b", r"\1", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"\s*(→|⇌)\s*", r" \1 ", text)
    return _clean_spaces(text)


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    low = cond.lower()
    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):  # only number + K is kelvin; K alone is potassium
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}\s*(?:°\s*C|°C|o\s*C|C)\b", cond, flags=re.I):
        val = m.group(0).replace("o C", "°C").replace("oC", "°C")
        data["temperature"].append(val)
    if re.search(r"(^|\s|,)(t|heat|delta|Δ|нагрев|кипяч)($|\s|,)", cond, flags=re.I):
        data["conditions"].append("нагревание")
    if re.search(r"\bp\b", cond) or "давлен" in low:
        data["pressure"].append("p")
    if "электролиз" in low or "electric" in low or "elec" in low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in low or "melt" in low:
        data["conditions"].append("расплав")
    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    # H2O is not solvent when it appears as reagent. Only explicit media/solvents are stored.
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO", "жидк. NH3", "жидкий NH3"]:
        if solv.lower() in low or solv in cond:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))
    for key in data:
        data[key] = _uniq(data[key])
    return data


def extract_reaction_name(context: str) -> str:
    ctx = context.lower()
    names = []
    for phrase in ["синтез аммиака", "процесс габера", "процесс габера-боша", "синтез-газ", "термитная смесь", "синтез рашинга", "метод байера"]:
        if phrase in ctx:
            names.append(phrase)
    return "; ".join(_uniq(names))


def split_equation_and_conditions(line: str) -> tuple[str | None, dict]:
    line = fix_ocr_formula(line)
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition("")
    # A -> condition -> B: condition is above/inside arrow, not part of products.
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) else "→"
        if re.search(r"\bt\b", middle, re.I) and re.search(r"\bp\b", middle, re.I):
            arrow = "⇌"  # common notation for Haber-like equilibrium over arrow.
        return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(middle)
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    # Remove nonchemical notes after products, but keep concentrations and real formula state notes.
    meta = normalize_condition("")
    m = re.search(r"\(([^()]*)\)\s*$", right)
    if m:
        inner = m.group(1).strip()
        if re.search(r"кч\s*=|координац|орто-форма|мета|назв|использ", inner, re.I):
            right = right[:m.start()].strip()
    return fix_ocr_formula(f"{left} {arrow} {right}"), meta


def is_free_ionic_equation(eq: str) -> bool:
    if "[" in eq and "]" in eq and re.search(r"[A-Z][a-z]?\d*\[", eq):
        return False  # salts with complex ions are allowed
    if re.search(r"(^|\s|\+)(H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)(\^?\d?[+-]|[⁺⁻])(?=\s|\+|→|⇌|$)", eq):
        return True
    if re.search(r"\]\s*(\^?\d?[+-]|[⁺⁻])", eq):
        return True
    return False


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq or not ("→" in eq or "⇌" in eq):
        return False
    if LIST_RE.search(eq) or ELECTRODE_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if is_free_ionic_equation(eq):
        return False
    try:
        left, right = re.split(r"→|⇌", eq, maxsplit=1)
    except ValueError:
        return False
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if len(left) < 1 or len(right) < 1:
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs = {}
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
            if p.lower() in GROUP_ALIASES:
                vals.extend(GROUP_ALIASES[p.lower()])
            elif re.fullmatch(r"[A-Z][a-z]?", p):
                vals.append(p)
        if vals:
            defs[var] = _uniq(vals)
    return defs



def replace_element_symbol(text: str, old: str, new: str) -> str:
    return re.sub(rf"(?<![A-Za-z]){re.escape(old)}(?=[A-Z0-9(\[]|\b)", new, text)

def replace_template_symbol(text: str, var: str, val: str) -> str:
    if var in {"Hal", "Me", "Al"}:
        return replace_element_symbol(text, var, val)
    # Template variables may appear inside formula fragments like MOH, MX, X2.
    return re.sub(rf"(?<![a-z]){re.escape(var)}", val, text)

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
            out.append(replace_element_symbol(base, candidates[-1], alt))
    return _uniq(out)


def expand_templates(eq: str, context: str) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found = []
    for v in ["Hal", "X", "Me", "E", "Э", "Al", "M"]:
        if re.search(rf"(?<![A-Za-z]){re.escape(v)}(?![a-z])", eq):
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
            cur = replace_template_symbol(cur, v, val)
        expanded.append(fix_ocr_formula(cur))
    return _uniq(expanded)


def classify_reaction(eq: str) -> str:
    low = eq.lower()
    if "электролиз" in low or "⚡" in eq:
        return "electrolysis"
    if "⇌" in eq:
        return "equilibrium"
    if "↓" in eq:
        return "precipitation"
    if "↑" in eq:
        return "gas_evolution"
    if any(x in eq for x in ["O2", "Cl2", "Br2", "HNO3", "KMnO4", "K2Cr2O7"]):
        return "redox_candidate"
    return "chemical_reaction"


def canonical_equation(eq: str) -> str:
    return re.sub(r"\s+", "", fix_ocr_formula(eq).replace("⇌", "→")).lower()


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    reactions = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+4)])
        eq, meta = split_equation_and_conditions(raw)
        if not eq:
            continue
        reaction_name = extract_reaction_name(context)
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate):
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            equation = f"{left.strip()} {arrow} {right.strip()}"
            confidence = 0.9
            review = ""
            if TEMPLATE_VARS_RE.search(equation):
                confidence = 0.4; review = "unresolved_template"
            reactions.append(ExtractedReaction(
                equation=equation,
                reactants=left.strip(), products=right.strip(),
                conditions="; ".join(meta["conditions"]),
                catalysts="; ".join(meta["catalysts"]),
                solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]),
                pressure="; ".join(meta["pressure"]),
                states="", reaction_name=reaction_name,
                reaction_kind=classify_reaction(equation),
                review_reason=review, confidence_score=confidence,
            ))
    dedup = {}
    for r in reactions:
        dedup[canonical_equation(r.equation)] = r
    return list(dedup.values())
