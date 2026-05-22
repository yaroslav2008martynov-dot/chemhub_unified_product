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

PERIODIC_GROUP = {}
for group_num, elements in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for element in elements:
        PERIODIC_GROUP[element] = group_num

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные металлы": ALKALI, "щелочные": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "щелочноземельные": ALKALINE_EARTH,
    "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "halogens": HALOGENS, "hal": HALOGENS, "гал": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "элементы 13 группы": GROUP_13, "group 13": GROUP_13,
    "14 группа": GROUP_14, "элементы 14 группы": GROUP_14, "group 14": GROUP_14,
    "15 группа": GROUP_15, "элементы 15 группы": GROUP_15, "group 15": GROUP_15,
    "16 группа": GROUP_16, "элементы 16 группы": GROUP_16, "group 16": GROUP_16,
    "17 группа": GROUP_17, "элементы 17 группы": GROUP_17, "group 17": GROUP_17,
}

TEMPLATE_VARS = ["Hal", "Me", "M", "X", "E", "Э"]
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(Hal|Me|M|X|E|Э)(?![a-zа-я])")
FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%−]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
BAD_DATA_RE = re.compile(r"\b(pK[ab]|pKa|pKb|ПР|Кsp|Ksp)\b", re.I)
ELECTRODE_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|электрод)\b|[eē]\s*[−\-+]|\d+\s*[eē]\b", re.I)
COMMENT_DROP_RE = re.compile(r"^(?:оксид|оксиды|пероксид|пероксиды|надпероксид|надпероксиды|карбид|карбиды|фосфид|фосфиды|гидрид|гидриды|галогенид|галогениды|сульфид|сульфиды|нитрид|нитриды|силицид|силициды|самовозгорание|без горения|горит|бурная реакция|взрыв|ядовитый газ)$", re.I)
REACTION_NAME_RE = re.compile(r"(синтез\s+Рашига|метод\s+Байера|процесс\s+Габера\s*-?\s*Боша|Габера\s*-?\s*Боша|синтез\s+аммиака|магическая\s+кислота|основание\s+Миллона|термитная\s+смесь|синтез\s*-?\s*газ)", re.I)

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
    repl = {
        "⟶": "→", "-->": "→", "->": "→", "=>": "→",
        "<->": "⇌", "<=>": "⇌", "↔": "⇌", "⇄": "⇌",
        "∙": "·", "−": "-", "–": "-", "—": "-",
        "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
        "⁺": "+", "⁻": "-", "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"[;,.]\s*$", "", text)
    return text.strip()


def _protect_brackets(text: str):
    protected = []
    def repl(m):
        protected.append(m.group(0))
        return f"§B{len(protected)-1}§"
    return re.sub(r"\[[^\]]+\]", repl, text), protected


def _restore_brackets(text: str, protected: list[str]) -> str:
    for i, chunk in enumerate(protected):
        text = text.replace(f"§B{i}§", chunk)
    return text


def _strip_oxidation_outside_brackets(text: str) -> str:
    work, protected = _protect_brackets(text)
    # Remove textbook oxidation states outside complex brackets only.
    # Keep normal formula indices: O2, H2SO4, N2, Li2O must not be touched.
    work = re.sub(r"(?<![A-Za-z])(\d*H2)\s*\^?\s*0\b", r"\1", work)
    work = re.sub(r"(?<![A-Za-z])(\d*H2)\s*\^?\s*[+-]\s*1\b", r"\1", work)
    work = re.sub(r"\b([A-Z][a-z]?\d+)\s*[+]\s*1\b", r"\1", work)
    work = re.sub(r"\b([A-Z][a-z]?\d+)\s*[-]\s*1\b", r"\1", work)
    work = re.sub(r"(?<![A-Za-z])(\d*)([A-Z][a-z]?)\s*\^?\s*0\b(?=\s*(?:\+|→|⇌|≠|$))", lambda m: (m.group(1) or "") + m.group(2), work)
    work = re.sub(r"\b([A-Z][a-z]?)\s*\^?\s*[+]\s*\d+\b", r"\1", work)
    work = re.sub(r"\b([A-Z][a-z]?)\s*\^?\s*[-]\s*\d+\b", r"\1", work)
    work = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*(\d+)(?=\()", r"\1", work)
    # Oxygen-state zero after H2 is not oxygen.
    work = re.sub(r"\bH2\s*\^?0\b", "H2", work)
    # OCR: H20 can mean H2^0 when followed by another reagent/product, but water in common cases remains H2O.
    work = re.sub(r"\bH20\b(?=\s*\+\s*(?:S|CuO|Ca|Li|N2|O2|Cl2|Br2|I2))", "H2", work)
    work = re.sub(r"\bH20\b", "H2O", work)
    return _restore_brackets(work, protected)

def _join_plus(text: str) -> str:
    work, protected = _protect_brackets(text)
    work = re.sub(r"\s*\+\s*", " + ", work)
    work = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", work)
    work = _restore_brackets(work, protected)
    return _clean_spaces(work)

def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    tr = str.maketrans({"А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X"})
    text = text.translate(tr)
    text = text.replace("H₂O", "H2O").replace("H₂", "H2").replace("Н20", "H2O")
    text = re.sub(r"O2\s*\^", "O2↑", text)
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV](?=\s|$|\+)", r"\1↓", text)
    text = re.sub(r"H2\+1([A-Z])", r"H2\1", text)
    text = _strip_oxidation_outside_brackets(text)
    text = _fix_known_oxidation_equations(text)
    text = _join_plus(text)
    text = re.sub(r"([A-Z][a-z]?\d*) \+ 1(?=\s*(?:$|\+|→|⇌))", r"\1", text)
    text = _fix_known_oxidation_equations(text)
    return _join_plus(text)


def _fix_known_oxidation_equations(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"H2\+2Li→2Li\+H", compact) or re.fullmatch(r"2Li\+H2→2Li\+H", compact):
        return "2Li + H2 → 2LiH"
    if re.fullmatch(r"H2\+Ca→CaH2?", compact) or re.fullmatch(r"H2\+Ca→Ca\+H2?", compact):
        return "Ca + H2 → CaH2"
    if re.fullmatch(r"H2\+Ca→Ca", compact):
        return "Ca + H2 → CaH2"
    if re.fullmatch(r"H2\+Ca→Ca\+?2?H2?(?:-?1)?", compact):
        return "Ca + H2 → CaH2"
    if re.fullmatch(r"H2\+2Li→2Li\+?1?H(?:-?1)?", compact):
        return "2Li + H2 → 2LiH"
    return text


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation).lower()
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else ("≠" if "≠" in eq else ""))
    if not arrow:
        return re.sub(r"\s+", "", eq)
    left, right = [x.strip() for x in eq.split(arrow, 1)]
    def norm_side(side):
        parts = [re.sub(r"\s+", "", p) for p in side.split("+") if p.strip()]
        parts = [re.sub(r"^\d+", "", p) for p in parts]
        return "+".join(sorted(parts))
    a, b = norm_side(left), norm_side(right)
    if arrow == "→":
        ordered = sorted([a, b])
        return f"{ordered[0]}={ordered[1]}"
    return f"{a}{arrow}{b}"


def normalize_condition(cond: str) -> dict:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "arrow_conditions": []}
    if not cond:
        return data
    cond = cond.replace("o C", "°C").replace("oC", "°C")
    data["arrow_conditions"].append(cond)
    c_low = cond.lower()
    for m in re.finditer(r"\b\d{2,5}\s*[\-–]\s*\d{2,5}\s*°\s*C\b|\b\d{1,5}\s*°\s*C\b|\b\d{2,5}\s*K\b", cond, re.I):
        data["temperature"].append(re.sub(r"\s*°\s*C", " °C", m.group(0)))
    if re.search(r"(^|[,\s])(t|Δ|hv|hν|нагрев)([,\s]|$)", cond, re.I):
        data["conditions"].append("t" if re.search(r"(^|[,\s])t([,\s]|$)", cond) else "нагревание")
    if "электролиз" in c_low or "эл. ток" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе h2" in c_low:
        data["conditions"].append("в токе H2")
    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "NaF"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2 ж", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in c_low or solv in cond:
            if solv == "H2O":
                continue
            data["solvents"].append(solv)
    for p in re.finditer(r"\b(?:p|\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa))\b", cond, re.I):
        data["pressure"].append(p.group(0))
    return data


def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "arrow_conditions": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _extract_name(text: str) -> tuple[str, str]:
    name = ""
    m = REACTION_NAME_RE.search(text)
    if m:
        name = m.group(0).strip()
    # Parenthetical names at end.
    m2 = re.search(r"\(([^()]*)\)\s*$", text)
    if m2 and REACTION_NAME_RE.search(m2.group(1)):
        name = m2.group(1).strip()
        text = text[:m2.start()].strip()
    return text, name


def _strip_trailing_comment(right: str) -> tuple[str, str]:
    m = re.search(r"\(([^()]*)\)\s*$", right)
    if not m:
        return right, ""
    inner = m.group(1).strip()
    if re.fullmatch(r"\s*[A-Z][a-z]?(?:\s*,\s*[A-Z][a-z]?)*\s*", inner):
        return right, ""
    if REACTION_NAME_RE.search(inner):
        return right[:m.start()].strip(), inner
    if COMMENT_DROP_RE.search(inner):
        return right[:m.start()].strip(), ""
    # Keep important formula/state annotations.
    if re.search(r"конц|разб|%|красн|бел|ромб|монокл|ж|тв|газ|aq|s|l|g|расплав", inner, re.I):
        return right, ""
    if re.search(r"[A-Za-zА-Яа-я]{3,}", inner):
        return right[:m.start()].strip(), ""
    return right, ""


def split_equation_and_conditions(line: str) -> tuple[str | None, dict, str, bool]:
    raw = _clean_spaces(line)
    raw, name = _extract_name(raw)
    if BAD_DATA_RE.search(raw) or ELECTRODE_RE.search(raw):
        return None, normalize_condition(""), "", False
    if "≠" in raw:
        left = raw.split("≠", 1)[0].strip()
        if FORMULA_TOKEN_RE.search(left):
            return fix_ocr_formula(f"{left} ≠"), normalize_condition(""), name, True
        return None, normalize_condition(""), "", False
    line = fix_ocr_formula(raw)
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), "", False
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) else "→"
        eq = fix_ocr_formula(f"{left} {arrow} {right}")
        return eq, normalize_condition(middle), name, False
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    right, name2 = _strip_trailing_comment(right)
    if name2 and not name:
        name = name2
    return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(""), name, False


def _free_ion_reject(eq: str) -> bool:
    # Reject only explicit free ions outside complex brackets, not plus signs used as separators.
    compact = re.sub(r"\s+", "", eq)
    no_brackets, _prot = _protect_brackets(compact)
    # H+, Cl-, Mg2+, SO4^2- etc. outside brackets.
    return bool(re.search(r"(?:^|[+→⇌])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)(?:\^?\d?[+-])(?=$|[+→⇌])", no_brackets))

def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq or not ("→" in eq or "⇌" in eq or "≠" in eq):
        return False
    if BAD_DATA_RE.search(eq) or ELECTRODE_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if eq.endswith("+") or re.search(r"(→|⇌)\s*[^+→⇌]*\+\s*$", eq):
        return False
    if "≠" in eq:
        return True
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if _free_ion_reject(eq):
        return False
    # Reject obviously lost-product / no-change reactions.
    if canonical_equation(eq) in {"h2o+o2=h2o", "h2o=h2o"}:
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs: dict[str, list[str]] = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "гал" in key or "hal" in key:
                defs["X"] = values
                defs["Hal"] = values
    for m in re.finditer(r"(?<![A-Za-zА-Яа-я])(M|X|Hal|Me|E|Э)(?![a-zа-я])\s*(?:=|->|→|:)\s*([^;)\n]+)", text):
        var, raw = m.group(1), m.group(2)
        vals = []
        for part in re.split(r"[,;\s]+", raw):
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
    # Examples: GeI4 (Sn), S + 3F2 -> SF6 (Se, Te), 2S + Cl2 -> S2Cl2 (Br)
    # and template definition: Na[Al(OH)4] ... (Al = Al, Ga, In)
    any_m = re.search(r"\(([^()]*)\)\s*$", eq)
    if any_m:
        inner_any = any_m.group(1).strip()
        base_any = eq[:any_m.start()].strip()
        dm = re.match(r"\s*([A-Z][a-z]?)\s*(?:=|->|→)\s*(.+)$", inner_any)
        if dm:
            src = dm.group(1)
            vals = [x.strip() for x in re.split(r"[,;\s]+", dm.group(2)) if re.fullmatch(r"[A-Z][a-z]?", x.strip())]
            if vals:
                return list(dict.fromkeys([fix_ocr_formula(re.sub(rf"\b{src}\b", v, base_any)) for v in vals]))
    m = re.search(r"\((\s*[A-Z][a-z]?(?:\s*,\s*[A-Z][a-z]?)*\s*)\)\s*$", eq)
    if not m:
        return [eq]
    inner = m.group(1).strip()
    base = eq[:m.start()].strip()
    alternatives = [x.strip() for x in inner.split(",")]
    elements = re.findall(r"[A-Z][a-z]?", base)
    out = [base]
    for alt in alternatives:
        group = PERIODIC_GROUP.get(alt)
        candidates = [e for e in elements if PERIODIC_GROUP.get(e) == group and e != alt]
        if not candidates:
            continue
        target = candidates[-1]
        out.append(re.sub(rf"\b{target}\b", alt, base))
    return list(dict.fromkeys(out))

def expand_templates(eq: str, context: str) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found = []
    for v in TEMPLATE_VARS:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append(v)
            elif v in ("Me", "M") and "M" in defs:
                defs[v] = defs["M"]
                vars_found.append(v)
            else:
                return []
    base = re.sub(r"\([^)]*(?:=|->|→|:)[^)]*\)", "", eq).strip()
    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def _join_wrapped_lines(lines: Iterable[str]) -> list[str]:
    out = []
    buf = ""
    for raw in lines:
        line = _clean_spaces(raw)
        if not line:
            continue
        if buf:
            if buf.endswith("+") or line.startswith("+"):
                buf = _clean_spaces(buf.rstrip("+").strip() + " + " + line.lstrip("+").strip())
                continue
            out.append(buf)
            buf = ""
        if line.endswith("+"):
            buf = line
        else:
            out.append(line)
    if buf and not buf.endswith("+"):
        out.append(buf)
    return out


def _meta_to_text(meta: dict, key: str) -> str:
    return "; ".join(dict.fromkeys(meta.get(key, [])))


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = str(text or "").splitlines()
    lines = _join_wrapped_lines(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+4)])
        eq, meta, name, is_negative = split_equation_and_conditions(raw)
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
                    conditions="не реагируют между собой", confidence_score=0.95,
                    reaction_name=name, review_reason="does_not_react"
                ))
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            arrow_conditions = meta.get("arrow_conditions", [])
            conditions = list(meta.get("conditions", []))
            # Keep exact above-arrow text as the primary site-visible condition.
            if arrow_conditions:
                conditions = arrow_conditions + [x for x in conditions if x not in arrow_conditions]
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(), products=right.strip(),
                conditions="; ".join(dict.fromkeys(conditions)),
                catalysts=_meta_to_text(meta, "catalysts"),
                solvents=_meta_to_text(meta, "solvents"),
                temperature=_meta_to_text(meta, "temperature"),
                pressure=_meta_to_text(meta, "pressure"),
                states="", confidence_score=0.92,
                reaction_name=name,
            ))
    # Deduplicate using order-insensitive canonical form; keep more informative record.
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        score = len(r.conditions or "") + len(r.temperature or "") + len(r.catalysts or "") + len(r.reaction_name or "") + len(r.equation or "")
        old = dedup.get(key)
        old_score = -1 if old is None else len(old.conditions or "") + len(old.temperature or "") + len(old.catalysts or "") + len(old.reaction_name or "") + len(old.equation or "")
        if old is None or score > old_score:
            dedup[key] = r
    return list(dedup.values())
