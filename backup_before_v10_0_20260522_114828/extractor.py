
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
for group_num, elements in [
    (1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14),
    (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)
]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные металлы": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS, "гал": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "группа 13": GROUP_13, "группа 14": GROUP_14, "группа 15": GROUP_15, "группа 16": GROUP_16, "группа 17": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(Hal|Me|M|X|E|Э)(?![A-Za-zА-Яа-я])")
CATOD_ANOD_RE = re.compile(r"\b(катод|анод|полуреакц|электронный\s+баланс|электрон)\b|[eē]\s*[−\-+]", re.I)
PK_RE = re.compile(r"\b(pK[ab]?|pKa|pKb|ПР|Ksp)\b|p\s*K|p\s*Ka|p\s*Kb", re.I)
ION_RE = re.compile(r"(?:^|[\\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\\d*)\\s*(?:\\^\\s*\\d?[+-]|[⁺⁻])(?=\\s|$)|(?:^|[\\s+])(?:H|OH|Cl|Br|I)\\s+[+-](?=\\s|\\+|$)", re.I)
COMMENT_DROP_RE = re.compile(
    r"\s*\((?:оксид|оксиды|пероксид|пероксиды|надпероксид|надпероксиды|гидрид|гидриды|"
    r"галогенид|галогениды|карбид|карбиды|фосфид|фосфиды|нитрид|нитриды|сульфид|сульфиды|"
    r"силицид|силициды|самовозгорание|без горения|горит|бурная реакция|взрыв|ядовитый газ)\)\s*$",
    re.I
)

NAMED_REACTION_RE = re.compile(r"\(([^()]*(?:синтез|метод|реакц|процесс|Габер|Бош|Рашиг|Байер|Миллон|магическ|тефлон|капрон|полиэтилен)[^()]*)\)", re.I)

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
    text = text.replace("\ufeff", "")
    text = text.replace("⟶", "→").replace("->", "→").replace("=>", "→")
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("∙", "·").replace("· ", "·")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"[;,.]\s*$", "", text)
    return text


def _protect_brackets(text: str):
    parts = []
    def repl(m):
        parts.append(m.group(0))
        return f"§BR{len(parts)-1}§"
    return re.sub(r"\[[^\]]+\]", repl, text), parts


def _restore_brackets(text: str, parts: list[str]) -> str:
    for i, p in enumerate(parts):
        text = text.replace(f"§BR{i}§", p)
    return text


def strip_oxidation_states(text: str) -> str:
    """Remove printed oxidation states outside square brackets. Keep real cluster/complex charges in brackets."""
    text, brackets = _protect_brackets(text)

    # Superscript-like OCR forms and explicit powers: 3H2^0, Ca^0, H^-1, Al^+3
    text = re.sub(r"\b(\d*\s*[A-Z][a-z]?\d{0,3})\s*\^\s*(?:0|[+-]\d+|\d+[+-])", r"\1", text)
    # Plain zero oxidation after a standalone element symbol: Li0, Ca0. Do not alter C60, C60F46 etc.
    text = re.sub(r"\b(\d*\s*[A-Z][a-z]?)0(?=\b|[+\s→⇌])", r"\1", text)
    # Oxidation after formula: NH3+1, Ca+2, H2-1, CaH2-1
    text = re.sub(r"(^|[^A-Za-z])(\d*\s*[A-Z][A-Za-z0-9()]*)(?:[+-]\d+)(?=\b|[A-Z(→⇌+\s])", r"\1\2", text)
    # Element oxidation before a group: Al+3(OH)4 -> Al(OH)4
    text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*(?:1|2|3|4|5|6|7)\s*(?=\()", r"\1", text)
    text = re.sub(r"\b([A-Z][a-z]?)\s*-\s*(?:1|2|3|4|5|6|7)\s*(?=\()", r"\1", text)
    # Remove leading oxidation coefficient before H in broken hydride products: +1H, 1H-1 => H
    text = re.sub(r"(^|[^A-Za-z])(?:\+?\s*)?1H(?:\s*-\s*1|\s*\^\s*-1)?", r"\1H", text)
    text = re.sub(r"(^|[^A-Za-z])H\s*-\s*1\b", r"\1H", text)

    text = _restore_brackets(text, brackets)
    # Fix oxidation states accidentally inside complex brackets, but preserve charges at bracket end: [S8^2+], [AsF6-]
    text = re.sub(r"\[([A-Z][a-z]?)\s*\+\s*(?:1|2|3|4|5|6|7)\s*(\([^]]+\))\]", r"[\1\2]", text)
    text = re.sub(r"\[([A-Z][a-z]?)(?:\+|-)(?:1|2|3|4|5|6|7)(\([^]]+\))\]", r"[\1\2]", text)
    return text

def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)

    # Translate look-alike Cyrillic letters inside probable formulas only enough for common OCR issues.
    table = str.maketrans({"Н": "H", "О": "O", "С": "C", "В": "B", "К": "K", "Р": "P", "А": "A", "Т": "T", "Х": "X"})
    text = re.sub(r"(?=[A-ZА-Я][A-Za-zА-Яа-я0-9()\[\]^+\-]*\d|H|Н)[A-ZА-Я][A-Za-zА-Яа-я0-9()\[\]^+\-]*",
                  lambda m: m.group(0).translate(table), text)

    text = text.replace("H₂", "H2").replace("O₂", "O2").replace("₀", "0").replace("⁰", "0")
    text = text.replace("⁺", "+").replace("⁻", "-")
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)

    # H20 is often H2 with oxidation state 0 in old textbooks; treat it as H2 when it acts as simple substance.
    text = re.sub(r"(?<![A-Za-z0-9])H20(?=\s*(?:\+|→|⇌))", "H2", text)
    text = re.sub(r"(?<=\+)\s*H20(?=\s*(?:\+|→|⇌))", " H2", text)
    # Real water OCR after products/reagents with O context.
    text = re.sub(r"(?<![A-Za-z0-9])H₂O(?![A-Za-z0-9])", "H2O", text)

    text = strip_oxidation_states(text)

    # Fix hydride products broken by OCR degrees.
    text = re.sub(r"Ca\s*H2", "CaH2", text)
    text = re.sub(r"(?<![A-Za-z])2\s*Li\s*\+\s*H(?![A-Za-z0-9])", "2LiH", text)
    text = re.sub(r"(?<![A-Za-z])2\s*Li\s+H(?![A-Za-z0-9])", "2LiH", text)
    text = re.sub(r"(?<![A-Za-z])Li\s*\+\s*H(?![A-Za-z0-9])", "LiH", text)
    text = re.sub(r"\b([A-Z][a-z]?)\s+\+\s+(\d*H\d*)\b", r"\1\2", text)
    text = re.sub(r"\[([A-Z][a-z]?)\s*\+\s*(?:1|2|3|4|5|6|7)\s*(\([^]]+\))\]", r"[\1\2]", text)

    # Drop purely classificatory comments after equation.
    text = COMMENT_DROP_RE.sub("", text)

    text = re.sub(r"\s*\+\s*", " + ", text)
    # Do not insert spaces around real charges inside square brackets.
    text = re.sub(r"\[([^\]]+)\]", lambda m: "[" + re.sub(r"\s*([+\-])\s*", r"\1", m.group(1)) + "]", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\+\s*$", "+", text)
    return _clean_spaces(text)


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "states": []}
    if not cond:
        return data
    raw = cond
    c_low = cond.lower()

    # keep full arrow label in conditions as written
    if raw and raw not in data["conditions"]:
        data["conditions"].append(raw)

    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}\s*(?:-\s*\d{1,4}\s*)?(?:°\s*C|°C|o\s*C|C)\b", cond, flags=re.I):
        val = re.sub(r"o\s*C|°\s*C|C\b", "°C", m.group(0), flags=re.I)
        val = re.sub(r"\s*-\s*", "–", val)
        data["temperature"].append(val)
    if re.search(r"(^|[\s,])(t|heat|delta|Δ|нагрев)($|[\s,])", cond, flags=re.I):
        if "t" not in data["conditions"] and cond.strip().lower() == "t":
            data["conditions"] = ["t"]
    if "электролиз" in c_low or "эл. ток" in c_low or "electric" in c_low or "elec" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе" in c_low:
        # already kept as full condition
        pass
    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "NaF"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in c_low or solv in cond:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b(?:p|P|\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa))\b", cond):
        data["pressure"].append(p.group(0))
    return data


def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "states": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _extract_name(text: str) -> tuple[str, str]:
    names = []
    def repl(m):
        inner = m.group(1).strip()
        if NAMED_REACTION_RE.search("(" + inner + ")"):
            names.append(inner)
            return ""
        return m.group(0)
    cleaned = re.sub(r"\(([^()]*)\)", repl, text)
    return _clean_spaces(cleaned), "; ".join(dict.fromkeys(names))


def _arrows_outside_parens(line: str):
    out = []
    depth = 0
    for m in re.finditer(r"(⇌|→)", line):
        # Count parentheses before this arrow.
        segment = line[:m.start()]
        depth = segment.count("(") - segment.count(")")
        if depth <= 0:
            out.append(m)
    return out


def split_equation_and_conditions(line: str) -> tuple[str | None, dict, str]:
    line, reaction_name = _extract_name(line)
    line = fix_ocr_formula(line)
    if "≠" in line:
        left = line.split("≠", 1)[0].strip()
        if left:
            meta = normalize_condition("")
            meta["conditions"].append("не реагируют между собой")
            return f"{left} ≠", meta, reaction_name
        return None, normalize_condition(""), reaction_name

    arrow_pat = r"(⇌|→)"
    arrows = _arrows_outside_parens(line)
    if not arrows:
        return None, normalize_condition(""), reaction_name

    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) else "→"
        # Haber-Bosch common OCR: conditions over reversible arrow.
        if re.search(r"\bt\s*,?\s*p\b", middle, re.I) and re.search(r"\bN2\b", left) and re.search(r"\bNH3\b", right):
            arrow = "⇌"
        eq = f"{left} {arrow} {right}"
        return fix_ocr_formula(eq), normalize_condition(middle), reaction_name

    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()

    meta = normalize_condition("")
    # Drop trailing class comments but keep names already extracted.
    right = COMMENT_DROP_RE.sub("", right).strip()
    return fix_ocr_formula(f"{left} {arrow} {right}"), meta, reaction_name


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq or not ("→" in eq or "⇌" in eq or "≠" in eq):
        return False
    if CATOD_ANOD_RE.search(eq):
        return False
    if PK_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq) and "n" not in eq:
        return False
    if eq.endswith("+"):
        return False
    if "≠" in eq:
        return True
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    left_check = re.sub(r"\bn(?=[A-Z])", "", left)
    right_check = re.sub(r"\bn(?=[A-Z])", "", right)
    polymer_like = bool(re.search(r"\bn?[A-Z][A-Za-z0-9]*", left) and re.search(r"\([^)]*[A-Z][^)]*\)\s*n", right))
    if not polymer_like and (not FORMULA_TOKEN_RE.search(left_check) or not FORMULA_TOKEN_RE.search(right_check)):
        return False
    if ION_RE.search(eq) and "[" not in eq:
        return False
    # Reject reactions where the product side is only a subset/copy of reactants:
    # e.g. 2H2O + O2 -> 2H2O means OCR lost a product.
    def species(side: str) -> set[str]:
        vals = set()
        for part in side.split("+"):
            clean = re.sub(r"^\s*\d+(?:[,.]\d+)?\s*", "", part.strip())
            clean = clean.strip()
            if clean:
                vals.add(clean)
        return vals
    left_species, right_species = species(left), species(right)
    if right_species and right_species.issubset(left_species):
        return False

    # Reject obviously missing product only; do not decompose formulas such as KO2 into K + O2.
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

    # M = Li, Na, K; M -> Mg, Ca, Sr, Ba; (Al -> Al, Ga, In) means variable Al stands for list.
    for m in re.finditer(r"\b(M|X|Hal|Me|E|Э|Al|Ga|In)\s*(?:=|->|→)\s*([^;)]+)", text):
        var, raw = m.group(1), m.group(2)
        vals = []
        for part in re.split(r"[,;]\s*|\s+", raw):
            p = part.strip(" .()")
            if not p:
                continue
            if p.lower() in GROUP_ALIASES:
                vals.extend(GROUP_ALIASES[p.lower()])
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
        if not group:
            continue
        candidates = [e for e in elements if PERIODIC_GROUP.get(e) == group and e != alt]
        if not candidates:
            continue
        target = candidates[-1]
        out.append(re.sub(rf"\b{target}\b", alt, base))
    return list(dict.fromkeys(out))


def expand_templates(eq: str, context: str) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    eq_no_defs = re.sub(r"\([^)]*(?:=|->|→)[^)]*\)", "", eq).strip()

    # Special: a concrete element used as variable in trailing definition: Na[Al(OH)4] ... (Al -> Al, Ga, In)
    for var in ["Al", "Ga", "In"]:
        if var in defs and re.search(rf"\b{var}\b", eq_no_defs):
            out = []
            for val in defs[var]:
                out.append(fix_ocr_formula(re.sub(rf"\b{var}\b", val, eq_no_defs)))
            return list(dict.fromkeys(out))

    if not TEMPLATE_VARS_RE.search(eq_no_defs):
        return infer_parenthetical_substitution(eq_no_defs)

    vars_found = []
    for v in ["Hal", "Me", "M", "X", "E", "Э"]:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![A-Za-zА-Яа-я])", eq_no_defs):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append(v)
            else:
                return []

    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = eq_no_defs
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![A-Za-zА-Яа-я])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation).lower()
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else ("≠" if "≠" in eq else ""))
    if not arrow:
        return re.sub(r"\s+", "", eq)
    left, right = [p.strip() for p in eq.split(arrow, 1)]
    def side_key(side: str) -> str:
        parts = [re.sub(r"^\d+", "", p.strip()) for p in side.split("+") if p.strip()]
        return "+".join(sorted(parts))
    a, b = side_key(left), side_key(right)
    if arrow in ["⇌", "≠"]:
        return "⇌".join(sorted([a, b])) if arrow == "⇌" else f"{a}≠"
    # user explicitly asked A+B=C+D and C+D=A+B considered duplicates, so sort sides.
    return "→".join(sorted([a, b]))


def _join_continuations(lines: list[str]) -> list[str]:
    out = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while cur.rstrip().endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if re.match(r"^\+?\s*(?:\d*\s*)?[A-ZА-Я]", nxt):
                cur = cur.rstrip("+ ").strip() + " + " + nxt.lstrip("+ ").strip()
                i += 1
            else:
                break
        out.append(cur)
        i += 1
    return out


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _join_continuations(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        if CATOD_ANOD_RE.search(raw) or PK_RE.search(raw):
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
                    equation=f"{left} ≠", reactants=left, products="",
                    conditions="не реагируют между собой", reaction_name=reaction_name,
                    confidence_score=0.95
                ))
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            if not left.strip() or not right.strip() or right.strip() == "+":
                continue
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(),
                products=right.strip(),
                conditions="; ".join(meta["conditions"]),
                catalysts="; ".join(meta["catalysts"]),
                solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]),
                pressure="; ".join(meta["pressure"]),
                states="; ".join(meta["states"]),
                confidence_score=0.92,
                reaction_name=reaction_name,
            ))

    # Dedup: keep most informative variant.
    dedup: dict[str, ExtractedReaction] = {}
    def score(r: ExtractedReaction) -> int:
        return sum(len(str(getattr(r, f, "") or "")) for f in [
            "equation", "reaction_name", "conditions", "catalysts", "solvents", "temperature", "pressure", "states"
        ])
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or score(r) > score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
