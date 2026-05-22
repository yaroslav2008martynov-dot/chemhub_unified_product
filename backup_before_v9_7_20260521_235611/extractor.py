from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from typing import Iterable

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
    "щм": ALKALI, "щелочные металлы": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS, "гал": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

NAMED_REACTION_HINTS = ["синтез", "метод", "процесс", "реакция", "основание", "магическая кислота", "габер", "бош", "байер", "рашиг"]
COMMENT_WORDS = [
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды", "гидрид", "гидриды",
    "галогенид", "галогениды", "сульфид", "сульфиды", "нитрид", "нитриды", "карбид", "карбиды",
    "фосфид", "фосфиды", "силицид", "силициды", "самовозгорание", "без горения", "горит", "бурная реакция",
    "взрыв", "ядовитый газ", "осадок", "газ", "соль", "кислота", "основание",
]
KEEP_PAREN_HINTS = ["конц", "разб", "%", "красн", "бел", "ж", "тв", "газ", "aq", "s", "l", "g", "ромб", "аморф", "крист"]

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%⁺⁻−]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-z])(M|X|Hal|Me|E|Э)(?![a-z])")
ION_OR_ELECTRON_RE = re.compile(r"(^|\s|\+)(e|ē|электрон|катод|анод|полуреакц)(\s|\+|$)", re.I)
PK_PR_RE = re.compile(r"\b(pK[ab]|pKa|pKb|рК[аб]|ПР)\b|pK\s*[ab]|pKа|pKб", re.I)

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
    confidence_score: float = 0.9
    impossible_note: str = ""
    hidden: bool = False


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    replacements = {
        "⟶": "→", "->": "→", "=>": "→", "=": "→",
        "<->": "⇌", "<=>": "⇌", "↔": "⇌", "⇄": "⇌",
        "∙": "·", "⋅": "·", "−": "-", "—": "-", "–": "-",
        "⁺": "+", "⁻": "-", "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    }
    # Reversible arrows first, otherwise <-> can be partially converted by ->.
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    for src, dst in replacements.items():
        if src in ["<->", "<=>", "↔", "⇄"]:
            continue
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"[;,.]\s*$", "", text)
    return text.strip()


def _protect_brackets(text: str) -> tuple[str, list[str]]:
    parts: list[str] = []
    def repl(m: re.Match) -> str:
        parts.append(m.group(0))
        return f"§BR{len(parts)-1}§"
    return re.sub(r"\[[^\]]+\]", repl, text), parts


def _restore_brackets(text: str, parts: list[str]) -> str:
    for i, value in enumerate(parts):
        text = text.replace(f"§BR{i}§", value)
    return text


def _space_plus_outside_brackets(text: str) -> str:
    protected, brackets = _protect_brackets(text)
    protected = re.sub(r"\s*\+\s*", " + ", protected)
    return _restore_brackets(protected, brackets)


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    # Cyrillic look-alikes in element symbols. Do not run this on reaction names separately.
    tr = str.maketrans({"А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X"})
    text = text.translate(tr)

    protected, brackets = _protect_brackets(text)

    # Oxidation states near H2 must not become water.
    protected = re.sub(r"(\d*)H2\s*(?:\^?0|0)\b", r"\1H2", protected)
    protected = re.sub(r"\bH20\b", "H2O", protected)  # only plain H20 remains water OCR.
    protected = protected.replace("H₂O", "H2O").replace("H₂", "H2")
    protected = re.sub(r"H2\s*\+\s*1\s*O", "H2O", protected)
    protected = re.sub(r"H2\s*\+\s*1\s*S", "H2S", protected)

    # Gas/precipitate OCR markers.
    protected = re.sub(r"\bO2\s*\^\b", "O2↑", protected)
    protected = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", protected)
    protected = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", protected)

    # Remove printed oxidation states outside complexes/brackets.
    protected = re.sub(r"\b([A-Z][a-z]?\d*)\s*\^?0\b", r"\1", protected)
    protected = re.sub(r"\b([A-Z][a-z]?\d*)\s*\+\s*([1-7])(?=\s*\(|\s|\+|→|⇌|$)", r"\1", protected)
    protected = re.sub(r"\b([A-Z][a-z]?\d*)\s*-\s*([1-7])(?=\s*\(|\s|\+|→|⇌|$)", r"\1", protected)
    protected = re.sub(r"(\d*[A-Z][a-z]?\d*)\+([1-7])\b", r"\1", protected)
    protected = re.sub(r"(\d*[A-Z][a-z]?\d*)-([1-7])\b", r"\1", protected)
    protected = re.sub(r"H2-[1-7]\b", "H2", protected)
    protected = re.sub(r"\b([A-Z][a-z]?\d*)\+\d+(?=[A-Z])", r"\1", protected)
    protected = re.sub(r"\b([A-Z][a-z]?\d*)-\d+(?=[A-Z])", r"\1", protected)

    # Inside complexes from OCR: [Al + 3(OH)4] -> [Al(OH)4]
    text = _restore_brackets(protected, brackets)
    text = re.sub(r"\[\s*([A-Z][a-z]?)\s*[+\-]\s*\d+\s*([^\]]+?)\s*\]", r"[\1\2]", text)
    text = _space_plus_outside_brackets(text)
    text = re.sub(r"([A-Z][A-Za-z0-9()]*?)\s+\+\s+\+", r"\1+ +", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _clean_spaces(text)


def normalize_condition(cond: str) -> dict[str, list[str]]:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    c_low = cond.lower()
    raw_cond = cond

    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}\s*(?:-|–)\s*\d{1,4}\s*(?:°\s*C|°C|o\s*C|C)\b", cond, flags=re.I):
        val = re.sub(r"o\s*C|C\b", "°C", m.group(0), flags=re.I).replace("-", "–")
        data["temperature"].append(val)
    for m in re.finditer(r"\b\d{1,4}\s*(?:°\s*C|°C|o\s*C)\b", cond, flags=re.I):
        val = re.sub(r"o\s*C", "°C", m.group(0), flags=re.I)
        data["temperature"].append(val)

    if re.search(r"(^|[\s,])(t|Δ|hv|hν|нагрев)([\s,]|$)", cond, flags=re.I):
        data["conditions"].append("t" if re.search(r"(^|[\s,])t([\s,]|$)", cond, flags=re.I) else "нагревание")
    if "электролиз" in c_low or "electric" in c_low or "elec" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе" in c_low:
        data["conditions"].append(raw_cond)
    if "so2" in c_low and ("ж" in c_low or "жид" in c_low):
        data["conditions"].append("SO2 ж")
    if "crO3".lower() in c_low or "hno3" in c_low:
        if "или" in c_low or "cro3" in c_low:
            data["conditions"].append(raw_cond)

    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "NaF"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    if re.search(r"кат\.?.*Fe", cond, re.I) and "Fe" not in data["catalysts"]:
        data["catalysts"].append("Fe")
    if re.search(r"(^|[\s,])p([\s,]|$)", cond):
        data["pressure"].append("p")
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))

    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO", "бензол", "толуол"]:
        if solv.lower() in c_low or solv in cond:
            data["solvents"].append(solv)

    # Preserve the exact arrow label when it has chemistry words not captured elsewhere.
    # Preserve exactly what was printed above the arrow for site rendering.
    if raw_cond:
        data["conditions"] = [raw_cond]

    for key in data:
        data[key] = list(dict.fromkeys([x.strip() for x in data[key] if x and x.strip()]))
    return data


def merge_meta(*metas: dict[str, list[str]]) -> dict[str, list[str]]:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def extract_reaction_name(text: str) -> tuple[str, str]:
    reaction_name = ""
    def repl(m: re.Match) -> str:
        nonlocal reaction_name
        inner = m.group(1).strip()
        low = inner.lower()
        if any(h in low for h in NAMED_REACTION_HINTS) and not any(w in low for w in COMMENT_WORDS if w != "основание"):
            reaction_name = inner
            return ""
        if low in ["тефлон", "магическая кислота"]:
            reaction_name = inner
            return ""
        return m.group(0)
    cleaned = re.sub(r"\(([^()]*)\)\s*$", repl, text)
    return _clean_spaces(cleaned), reaction_name


def _fold_ru_lookalikes(value: str) -> str:
    return value.lower().translate(str.maketrans({"a":"а","o":"о","c":"с","e":"е","p":"р","x":"х","k":"к","m":"м","h":"н","t":"т","y":"у"}))

def strip_trailing_comments(eq: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        low = _fold_ru_lookalikes(inner)
        if any(k in low for k in KEEP_PAREN_HINTS):
            return m.group(0)
        if any(w in low for w in COMMENT_WORDS):
            return ""
        return m.group(0)
    return _clean_spaces(re.sub(r"\(([^()]*)\)\s*$", repl, eq))


def split_equation_and_conditions(line: str) -> tuple[str | None, dict[str, list[str]], str, bool]:
    raw = _clean_spaces(line)
    if not raw:
        return None, normalize_condition(""), "", False
    if PK_PR_RE.search(raw):
        return None, normalize_condition(""), "", False
    raw, reaction_name = extract_reaction_name(raw)
    raw = fix_ocr_formula(raw)

    # Negative reaction: A + B ≠
    if "≠" in raw:
        left = raw.split("≠", 1)[0].strip()
        if FORMULA_TOKEN_RE.search(left):
            return f"{left} ≠", normalize_condition(""), reaction_name, True
        return None, normalize_condition(""), reaction_name, False

    arrows = list(re.finditer(r"(⇌|→)", raw))
    if not arrows:
        return None, normalize_condition(""), reaction_name, False

    # A -> condition -> B
    if len(arrows) >= 2:
        left = raw[:arrows[0].start()].strip()
        middle = raw[arrows[0].end():arrows[1].start()].strip()
        right = raw[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) or re.search(r"кат\.?\s*\(?Fe\)?", middle, re.I) else "→"
        eq = strip_trailing_comments(f"{left} {arrow} {right}")
        return fix_ocr_formula(eq), normalize_condition(middle), reaction_name, False

    arrow = arrows[0].group(1)
    left = raw[:arrows[0].start()].strip()
    right = raw[arrows[0].end():].strip()
    right = strip_trailing_comments(right)
    eq = fix_ocr_formula(f"{left} {arrow} {right}")
    return eq, normalize_condition(""), reaction_name, False


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq:
        return False
    if "≠" in eq:
        return bool(FORMULA_TOKEN_RE.search(eq.split("≠", 1)[0]))
    if not ("→" in eq or "⇌" in eq):
        return False
    if re.search(r"\b(катод|анод|электрон|полуреакц|также)\b", eq, re.I):
        return False
    if ION_OR_ELECTRON_RE.search(eq):
        return False
    if PK_PR_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        # allow polymer notation nC2F4 -> (-C2F4-)n
        if "n" not in eq or "(" not in eq:
            return False
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if right.strip().endswith("+") or left.strip().endswith("+"):
        return False
    polymer_ok = bool(re.search(r"^\s*n?[A-Z][A-Za-z0-9]*", left) and re.search(r"\)\s*n\b", right))
    if not polymer_ok and (not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right)):
        return False
    # Free ions: reject except bracketed complex/cluster reactions and magic acid exception.
    if "[" not in eq:
        if re.search(r"(^|\s|\+)\s*(H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(\^?\d?[+\-])\s*(\+|→|⇌|$)", eq):
            return False
    # obvious lost/massless reactions
    if canonical_side(left) == canonical_side(right):
        return False
    if re.search(r"2H2O\s*\+\s*O2\s*→\s*2H2O", eq):
        return False
    return True


def canonical_side(side: str) -> str:
    tokens = [re.sub(r"^\d+(?:[,.]\d+)?", "", t.strip()).lower() for t in re.split(r"\s*\+\s*", side) if t.strip()]
    return "+".join(sorted(tokens))


def canonical_equation(eq: str) -> str:
    eq = fix_ocr_formula(eq)
    if "≠" in eq:
        return canonical_side(eq.split("≠", 1)[0]) + "≠"
    arrow = "⇌" if "⇌" in eq else "→"
    if arrow not in eq:
        return re.sub(r"\s+", "", eq.lower())
    left, right = eq.split(arrow, 1)
    a, b = canonical_side(left), canonical_side(right)
    # reversible/dedup tolerant: A+B->C+D and C+D->A+B have the same key.
    return "⇄".join(sorted([a, b]))


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs: dict[str, list[str]] = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "hal" in key or "гал" in key:
                defs["X"] = values
                defs["Hal"] = values
    for m in re.finditer(r"\b(M|X|Hal|Me|E|Э)\s*(?:=|->|→)\s*([^;)]+)", text):
        var, raw = m.group(1), m.group(2)
        vals: list[str] = []
        for part in re.split(r"[,;\s]+", raw):
            p = part.strip(" .()")
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
    # Do not treat plain letters in reaction names as templates.
    if "основание Миллона" in context or "основание Mиллона" in context:
        context = re.sub(r"основание\s+[МM]иллона", "", context, flags=re.I)
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
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


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        # Join line continuations ending with + or next line starting with +.
        while i + 1 < len(lines) and (cur.endswith("+") or lines[i + 1].lstrip().startswith("+")):
            nxt = lines[i + 1].strip()
            if cur.endswith("+") and nxt.startswith("+"):
                cur = cur + " " + nxt[1:].strip()
            elif cur.endswith("+"):
                cur = cur + " " + nxt
            else:
                cur = cur + " + " + nxt[1:].strip()
            cur = re.sub(r"\s*\+\s*", " + ", cur)
            i += 1
        merged.append(cur)
        i += 1
    return merged


def _combined_conditions(meta: dict[str, list[str]]) -> str:
    if meta.get("conditions"):
        return "; ".join(dict.fromkeys(meta["conditions"]))
    items = []
    for key in ["temperature", "pressure", "catalysts", "solvents"]:
        for val in meta.get(key, []):
            if val and val not in items:
                items.append(val)
    return "; ".join(items)


def _informativeness(r: ExtractedReaction) -> int:
    return sum(len(str(x or "")) for x in [r.conditions, r.catalysts, r.solvents, r.temperature, r.pressure, r.reaction_name]) + len(r.equation)


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_wrapped_lines(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx - 6): min(len(lines), idx + 4)])
        eq, meta, reaction_name, negative = split_equation_and_conditions(raw)
        if not eq:
            continue
        if negative:
            left = eq.split("≠", 1)[0].strip()
            reactions.append(ExtractedReaction(
                equation=eq, reactants=left, products="", conditions="", reaction_name=reaction_name,
                impossible_note="не реагируют между собой", hidden=True, confidence_score=0.95,
            ))
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate):
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            # Special correction from textbook oxidation OCR: H2 + Ca -> Ca + 2H2-1 is CaH2.
            if re.fullmatch(r"H2\s*\+\s*Ca", left.strip()) and re.search(r"Ca\s*\+\s*2H2", right):
                right = "CaH2"
            if re.fullmatch(r"H2\s*\+\s*2Li", left.strip()) and re.search(r"2Li\s*\+\s*H", right):
                right = "2LiH"
            right = re.sub(r"\s*\+\s*[1-7]$", "", right.strip())
            equation = f"{left.strip()} {arrow} {right.strip()}"
            if not looks_like_reaction(equation):
                continue
            reactions.append(ExtractedReaction(
                equation=equation,
                reactants=left.strip(),
                products=right.strip(),
                conditions=_combined_conditions(meta),
                catalysts="; ".join(meta["catalysts"]),
                solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]),
                pressure="; ".join(meta["pressure"]),
                states="",
                reaction_name=reaction_name,
                confidence_score=0.93,
            ))
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _informativeness(r) > _informativeness(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
