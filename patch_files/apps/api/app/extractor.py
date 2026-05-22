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
    "щм": ALKALI, "щелочные": ALKALI, "щелочные металлы": ALKALI, "alkali": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH,
    "alkaline earth": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "гал": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

# Formula token intentionally allows brackets, arrows are handled elsewhere.
FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?|[A-Z])(?:[A-Za-z0-9()\[\].·\-+^↑↓%]*)")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(M|X|Hal|Me|E|Э)(?![a-zа-я])")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b")
BAD_CONTEXT_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|электронн|баланс|также|pka|pkb|pkа|pkб|пка|пкб|пр\s*=|ПР\s*=)\b|[ē]", re.I)
FREE_ION_RE = re.compile(r"(^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(?:\^?\d*[+\-]|[⁺⁻])\s*(?=(?:[+→⇌]|$))")
EXPLANATION_WORDS = [
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "карбид", "карбиды", "фосфид", "фосфиды",
    "гидрид", "гидриды", "сульфид", "сульфиды", "нитрид", "нитриды", "силицид", "силициды",
    "самовозгорание", "без горения", "горит", "бурная реакция", "взрыв", "ядовитый газ"
]
NAME_WORDS = ["синтез рашиг", "метод байер", "габер", "бош", "магическая кислота", "основание миллона", "тефлон"]

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

def _unique_join(items):
    out = []
    for item in items:
        item = _clean_spaces(item)
        if item and item not in out:
            out.append(item)
    return "; ".join(out)

def _clean_spaces(text: str) -> str:
    text = str(text or "")
    text = text.replace("\ufeff", "")
    text = text.replace("⟶", "→").replace("⟹", "→").replace("=>", "→").replace("->", "→")
    text = text.replace("<=>", "⇌").replace("<->", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("∙", "·").replace("⋅", "·")
    text = text.replace("↑", UP).replace("^", "^")
    # fix broken OCR for concentration abbreviations
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text

def _translate_lookalikes(text: str) -> str:
    tr = str.maketrans({
        "А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X",
        "а":"a","с":"c","е":"e","о":"o","р":"p","х":"x",
        "₀":"0","₁":"1","₂":"2","₃":"3","₄":"4","₅":"5","₆":"6","₇":"7","₈":"8","₉":"9",
        "⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9",
        "⁺":"+","⁻":"-"
    })
    return text.translate(tr)

def _protect_brackets(text: str):
    parts = []
    protected = []
    last = 0
    for m in re.finditer(r"\[[^\]]+\](?:\d*[+-]?|\^\d*[+-])?", text):
        parts.append(text[last:m.start()])
        token = f"@@BR{len(protected)}@@"
        protected.append(m.group(0))
        parts.append(token)
        last = m.end()
    parts.append(text[last:])
    return "".join(parts), protected

def _restore_brackets(text: str, protected: list[str]) -> str:
    for i, value in enumerate(protected):
        text = text.replace(f"@@BR{i}@@", value)
    return text

def strip_oxidation_states(text: str) -> str:
    """Remove oxidation-state marks outside bracketed complexes. Keep true complex charges."""
    text = _clean_spaces(_translate_lookalikes(text))
    protected_text, protected = _protect_brackets(text)

    # H20 is usually OCR for water, but H20 followed by +/arrow/element in a redox formula can be H2^0.
    # Treat H20 at reagent/product boundary as H2 when it is directly before + or arrow.
    protected_text = re.sub(r"\bH20(?=\s*(?:[+→⇌]|$))", "H2", protected_text)
    protected_text = protected_text.replace("H₂O", "H2O").replace("H₂", "H2")
    protected_text = protected_text.replace("H20", "H2O")

    # Remove oxidation states attached directly to formula fragments: H2^0, Ca0, Al+3, H-1.
    protected_text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*\^?\s*(?:0|[+-]\s*\d+)(?=($|[\s+→⇌),]))", r"\1", protected_text)
    protected_text = re.sub(r"([A-Z][a-z]?(?:\d+)?)(?:[+-]\s*\d+)(?=[A-Z(\[])", r"\1", protected_text)
    # OCR variant: Al + 3(OH)4 inside formula -> Al(OH)4
    protected_text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*\d+\s*(?=\()", r"\1", protected_text)
    # Remove standalone oxidation coefficient before H after plus: + 1H -> + H
    protected_text = re.sub(r"(?<=[+→⇌]\s)\d+\s*H(?=($|[\s+]))", "H", protected_text)
    # Remove trailing -1 etc after hydrogen fragments
    protected_text = re.sub(r"\bH(\d*)\s*-\s*\d+\b", r"H\1", protected_text)
    protected_text = re.sub(r"\bH(\d*)\+\s*\d+\b", r"H\1", protected_text)

    text = _restore_brackets(protected_text, protected)
    return _clean_spaces(text)

def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    text = strip_oxidation_states(text)
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)
    text = re.sub(r"H2\+1O", "H2O", text)
    text = re.sub(r"H2\+1S", "H2S", text)
    # Hydride OCR repairs
    text = re.sub(r"\bCa\s*\+\s*H2\b", "CaH2", text)
    text = re.sub(r"\b(Mg|Sr|Ba)\s*\+\s*H2\b", r"\1H2", text)
    text = re.sub(r"\b(2\s*)?(Li|Na|K|Rb|Cs)\s*\+\s*H\b", lambda m: (m.group(1) or "") + m.group(2) + "H", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text)
    return _clean_spaces(text)

def canonical_equation(equation: str) -> str:
    """Order-insensitive key for duplicate detection. Treat reverse reactions as duplicates."""
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
    def norm_side(side):
        tokens = [re.sub(r"^\d+(?:[,.]\d+)?", "", t) for t in side.split("+") if t]
        return "+".join(sorted(tokens))
    a, b = norm_side(left), norm_side(right)
    return "||".join(sorted([a, b]))

def _normalize_condition_text(cond: str) -> str:
    cond = _clean_spaces(cond)
    cond = cond.replace("o C", "°C").replace("oC", "°C")
    cond = re.sub(r"(\d)\s*°\s*C", r"\1 °C", cond)
    cond = re.sub(r"(\d)\s*K\b", r"\1 K", cond)
    cond = re.sub(r"\bkat\b", "кат.", cond, flags=re.I)
    return cond.strip(" ,;")

def normalize_condition(cond: str) -> dict:
    cond = _normalize_condition_text(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    low = cond.lower()
    for m in re.finditer(r"\b\d{1,4}\s*-\s*\d{1,4}\s*°\s*C\b|\b\d{1,4}\s*°\s*C\b|\b\d{2,5}\s*K\b", cond, flags=re.I):
        data["temperature"].append(_normalize_condition_text(m.group(0)))
    if re.search(r"(^|[\s,])(t|Δ|heat|нагрев)([\s,]|$)", cond, flags=re.I):
        data["conditions"].append("t" if re.search(r"(^|[\s,])t([\s,]|$)", cond) else "нагревание")
    if re.search(r"\bp\b|давлен|pressure", cond, flags=re.I):
        data["pressure"].append("p" if re.search(r"(^|[\s,])p([\s,]|$)", cond) else cond)
    if "электролиз" in low or "эл. ток" in low or "эл ток" in low or "electric" in low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in low or "melt" in low:
        data["conditions"].append("расплав")
    # Keep "в токе H2", SO2 ж, CrO3 или HNO3, F2, NaF etc. exactly as arrow condition.
    if re.search(r"в токе|so2|crO3|hno3|f2|naf|желатин|ацетон", cond, flags=re.I):
        data["conditions"].append(cond)
    for cat in ["Pt", "Pd", "Ni", "Fe", "Rh", "Rh/Pt", "Rh / Pt", "MnO2", "V2O5", "AlCl3", "FeCl3", "P4O10"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            if cat not in data["catalysts"] and (cat != "P4O10"):
                data["catalysts"].append(cat)
            if cond not in data["conditions"]:
                data["conditions"].append(cond)
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in low:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))
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

def split_equation_and_conditions(line: str) -> tuple[str | None, dict, str]:
    """Return equation, metadata, reaction_name. Supports A -> condition -> B."""
    line = fix_ocr_formula(line)
    reaction_name = ""

    if "≠" in line:
        return None, normalize_condition(""), ""

    # Pull reaction names / aliases from final parentheses.
    m = re.search(r"\(([^()]*)\)\s*$", line)
    if m:
        inner = m.group(1).strip()
        ilow = inner.lower()
        if any(w in ilow for w in NAME_WORDS):
            reaction_name = inner
            line = line[:m.start()].strip()
        elif any(w in ilow for w in EXPLANATION_WORDS):
            line = line[:m.start()].strip()

    arrow_pat = r"(⇌|→)"
    arrows = list(re.finditer(arrow_pat, line))
    if not arrows:
        return None, normalize_condition(""), reaction_name

    # A -> condition -> B
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if any(a.group(1) == "⇌" for a in arrows[:2]) else "→"
        # Haber-Bosch case: t,p,кат.(Fe) means reversible synthesis.
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
    if not eq or not ("→" in eq or "⇌" in eq):
        return False
    if BAD_CONTEXT_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if FREE_ION_RE.search(eq) and "[" not in eq:
        return False
    if re.search(r"\b(e|ē)\s*[-+]|\be[-+]\b", eq):
        return False
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if left.strip().endswith("+") or right.strip().endswith("+"):
        return False
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    # reject obviously same/lost product reactions
    if canonical_equation(eq).count("h2o") >= 2 and re.sub(r"^\d+", "", left.replace(" ", "")) == re.sub(r"^\d+", "", right.replace(" ", "")):
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
    # explicit definitions: M = Al, Ga; X -> F, Cl
    for m in re.finditer(r"(?<![A-Za-zА-Яа-я])(M|X|Hal|Me|E|Э)\s*(?:=|->|→|-|—)\s*([^;)]+)", text_norm):
        var, raw = m.group(1), m.group(2)
        vals = []
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
    eq = fix_ocr_formula(eq).replace("М", "M").replace("Х", "X")
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)

    vars_found = []
    for v in ["Hal", "Me", "M", "X", "E", "Э"]:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq):
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
    base = re.sub(r"\([^)]*(?:=|->|→|-|—)[^)]*\)", "", eq).strip()
    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))

def _merge_broken_lines(lines: list[str]) -> list[str]:
    merged = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        # If reaction/product side ends with plus, append next line beginning with plus.
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
    lines = _merge_broken_lines(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+5)])
        if BAD_CONTEXT_RE.search(raw):
            continue
        eq, meta, reaction_name = split_equation_and_conditions(raw)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            # repair common expanded hydrides: 2Na + H2 -> 2NaH
            candidate = re.sub(r"\b2(Li|Na|K|Rb|Cs)\s*\+\s*H2\s*→\s*2\1\s*\+\s*H\b", r"2\1 + H2 → 2\1H", candidate)
            if not looks_like_reaction(candidate):
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            # Ensure equations with Haber pattern are reversible and named.
            if "N2" in left and "NH3" in right and ("Fe" in _unique_join(meta["catalysts"]) or "кат" in raw.lower()):
                arrow = "⇌"
                reaction_name = reaction_name or "Синтез аммиака (процесс Габера-Боша)"
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(),
                products=right.strip(),
                conditions=_unique_join(meta["conditions"]),
                catalysts=_unique_join(meta["catalysts"]),
                solvents=_unique_join(meta["solvents"]),
                temperature=_unique_join(meta["temperature"]),
                pressure=_unique_join(meta["pressure"]),
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
