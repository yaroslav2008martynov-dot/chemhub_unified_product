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
for _n, _els in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for _e in _els:
        PERIODIC_GROUP[_e] = _n

GROUP_ALIASES = {
    "щм": ALKALI, "щелочные металлы": ALKALI, "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH, "щелочноземельные металлы": ALKALINE_EARTH, "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS, "гал": HALOGENS, "hal": HALOGENS, "halogens": HALOGENS,
    "халькогены": CHALCOGENS, "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS, "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13, "14 группа": GROUP_14, "15 группа": GROUP_15, "16 группа": GROUP_16, "17 группа": GROUP_17,
    "group 13": GROUP_13, "group 14": GROUP_14, "group 15": GROUP_15, "group 16": GROUP_16, "group 17": GROUP_17,
}

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%−]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-z])(M|X|Hal|Me|E|Э)(?![a-z])")
ELECTRON_RE = re.compile(r"(?:\be\s*[-−]?|ē|электрон)", re.I)
BAD_LINE_RE = re.compile(r"\b(катод|анод|полуреакц|электронный\s+баланс|также)\b", re.I)
NAMED_RE = re.compile(r"\(([^)]*(?:синтез|метод|реакция|процесс)[^)]*)\)\s*$", re.I)
COMMENT_WORDS_RE = re.compile(r"^(?:оксид|оксиды|пероксид|пероксиды|надпероксид|надпероксиды|галогенид|галогениды|карбид|карбиды|фосфид|фосфиды|гидрид|гидриды|сульфид|сульфиды|нитрид|нитриды|силицид|силициды|самовозгорание|без\s+горения|бурная\s+реакция|взрыв|со\s+взрывом|ядовитый\s+газ)$", re.I)
KEEP_PAREN_RE = re.compile(r"^(?:конц\.?|разб\.?|\d+\s*%|расплав|красный|белый|ромбическая|моноклинная|аморфный|крист\.?|газ|ж|тв|aq|s|l|g)$", re.I)
CONDITION_HINT_RE = re.compile(r"(\d+\s*[–\-]\s*\d+\s*(?:°\s*C|°C|o\s*C|C|K)|\d+\s*(?:°\s*C|°C|o\s*C|C|K)|\bt\b|кат\.?|p\b|давл|электролиз|ток|SO2\s*ж|CrO3|HNO3|желатин|ацетон|NaF|F2|Ni|Fe|Pt|Pd|Rh|V2O5|MnO2|AlCl3|FeCl3|hv|hν|Δ|в\s+токе)", re.I)

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
    hidden: bool = False
    impossible_note: str = ""


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    trans = str.maketrans({"А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X","а":"a","с":"c","е":"e","о":"o","р":"p","х":"x"})
    text = text.translate(trans)
    text = text.replace("⟶", "→").replace("->", "→").replace("=>", "→")
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("∙", "·").replace("−", "-").replace("⁻", "-").replace("⁺", "+")
    text = re.sub(r"[‐‑‒–—]", "-", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("конц..", "конц.").replace("разб..", "разб.").replace("кат..", "кат.")
    text = re.sub(r"[;,.]\s*$", "", text)
    return text.strip()


def _protect_brackets(text: str):
    saved = []
    def repl(m):
        saved.append(m.group(0))
        return f"§BR{len(saved)-1}§"
    return re.sub(r"\[[^\]]+\](?:\d*[+-])?", repl, text), saved


def _restore_brackets(text: str, saved: list[str]) -> str:
    for i, val in enumerate(saved):
        text = text.replace(f"§BR{i}§", val)
    return text


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    protected, saved = _protect_brackets(text)
    # H2 with printed oxidation state 0: H20/H2^0/H2⁰ must be H2, not water.
    protected = protected.replace("H₂⁰", "H2").replace("H2^0", "H2").replace("H2 0", "H2")
    protected = re.sub(r"\bH20\b(?=\s*\+)", "H2", protected)
    # Water OCR elsewhere.
    protected = protected.replace("H₂O", "H2O").replace("Н20", "H2O")
    protected = re.sub(r"\bH20\b", "H2O", protected)
    # Gas/precipitate markers.
    protected = protected.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    protected = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", protected)
    protected = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", protected)
    # Remove printed oxidation states outside bracketed complexes/clusters.
    protected = re.sub(r"(?<!\[)([A-Z][a-z]?\d*)\s*(?:\^?0|\+\s*\d+|-\s*\d+)(?=\s|\+|→|⇌|$|[A-Z(])", r"\1", protected)
    protected = re.sub(r"([A-Z][a-z]?\d*)\+\d+(?=[A-Z(])", r"\1", protected)
    protected = re.sub(r"\[\s*([A-Z][a-z]?)\s*[+\-]\s*\d+\s*(\([^\]]+)\]", r"[\1\2]", protected)
    protected = re.sub(r"\[\s*([A-Z][a-z]?)\s*\+\s*\d+\s*(\([^\]]+)\]", r"[\1\2]", protected)
    protected = re.sub(r"H2\+1([A-Z])", r"H2\1", protected)
    protected = re.sub(r"H\+1", "H", protected)
    protected = _restore_brackets(protected, saved)
    protected = re.sub(r"\s*\+\s*", " + ", protected)
    protected = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", protected)
    return _clean_spaces(protected)


def normalize_condition(cond: str) -> dict:
    original = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "arrow_conditions": []}
    if not original:
        return data
    original = original.replace("o C", "°C").replace("oC", "°C")
    original = re.sub(r"(\d)\s*°\s*C", r"\1 °C", original)
    original = re.sub(r"(\d)\s*K\b", r"\1 K", original)
    data["arrow_conditions"].append(original)
    for m in re.finditer(r"\b\d{2,5}\s*K\b", original):
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}\s*(?:[-–]\s*\d{1,4}\s*)?°\s*C\b", original, flags=re.I):
        data["temperature"].append(re.sub(r"\s+", " ", m.group(0).replace("-", "–")))
    if re.search(r"(^|[,\s])t($|[,\s])", original, flags=re.I):
        data["conditions"].append("t")
    low = original.lower()
    for phrase in ["электролиз", "эл. ток", "в токе h2", "в токе H2", "расплав", "so2 ж", "SO2 ж"]:
        if phrase.lower() in low and phrase not in data["conditions"]:
            data["conditions"].append(phrase)
    for cat in ["Rh/Pt", "Rh / Pt", "Pt", "Pd", "Ni", "Fe", "Rh", "MnO2", "V2O5", "AlCl3", "FeCl3", "CrO3", "HNO3"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", original):
            data["catalysts"].append(cat)
    for solv in ["желатин", "ацетон", "CCl4", "SO2", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in low:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa)\b|(^|[,\s])p($|[,\s])", original, flags=re.I):
        val = p.group(0).strip(" ,")
        if val:
            data["pressure"].append(val)
    return data


def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": [], "arrow_conditions": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                if val and val not in out[key]:
                    out[key].append(val)
    return out


def _strip_trailing_comment(right: str) -> tuple[str, str]:
    name = ""
    m = re.search(r"\(([^()]*)\)\s*$", right)
    if not m:
        return right, name
    inner = _clean_spaces(m.group(1))
    low = inner.lower()
    if NAMED_RE.search("(" + inner + ")"):
        name = inner
        right = right[:m.start()].strip()
    elif COMMENT_WORDS_RE.match(low):
        right = right[:m.start()].strip()
    elif KEEP_PAREN_RE.match(low):
        pass
    elif re.search(r"[А-Яа-я]{3,}", inner):
        # Material aliases such as teflon are useful as names, not equation text.
        if low in ["тефлон", "полиэтилен", "капрон"]:
            name = inner
        right = right[:m.start()].strip()
    return right, name


def split_equation_and_conditions(line: str, prev_condition: str = "") -> tuple[str | None, dict, str, bool]:
    line = fix_ocr_formula(line)
    if "≠" in line:
        left = line.split("≠", 1)[0].strip()
        if FORMULA_TOKEN_RE.search(left):
            return left + " ≠", normalize_condition(prev_condition), "", True
        return None, normalize_condition(""), "", False
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), "", False
    name = ""
    # A -> condition -> B
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        right, nm = _strip_trailing_comment(right)
        name = nm
        arrow = "⇌" if "⇌" in [a.group(1) for a in arrows] else "→"
        if re.search(r"\bt\s*,?\s*p\s*,?\s*кат\.?\s*\(?Fe\)?", middle, re.I):
            arrow = "⇌"
        return fix_ocr_formula(f"{left} {arrow} {right}"), merge_meta(normalize_condition(prev_condition), normalize_condition(middle)), name, False
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    right, name = _strip_trailing_comment(right)
    return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(prev_condition), name, False


def _is_free_ionic(eq: str) -> bool:
    if BAD_LINE_RE.search(eq) or ELECTRON_RE.search(eq):
        return True
    if "[" in eq:
        return False
    return bool(re.search(r"(?:^|\s|\+)(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(?:\^?\d?[+\-]|[+\-])(?:\s|\+|$)", eq))


def _split_lr(eq: str):
    if "⇌" in eq:
        return eq.split("⇌", 1), "⇌"
    if "→" in eq:
        return eq.split("→", 1), "→"
    return [eq, ""], ""


def looks_like_reaction(eq: str) -> bool:
    eq = _clean_spaces(eq)
    if not eq:
        return False
    if "≠" in eq:
        return FORMULA_TOKEN_RE.search(eq) is not None
    if not ("→" in eq or "⇌" in eq):
        return False
    if BAD_LINE_RE.search(eq) or ELECTRON_RE.search(eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq) and not re.search(r"\([^)]*\)n", eq):
        return False
    (left, right), _ = _split_lr(eq)
    if not right or right.strip().endswith("+") or left.strip().endswith("+"):
        return False
    if not FORMULA_TOKEN_RE.search(left) or not FORMULA_TOKEN_RE.search(right):
        return False
    if _is_free_ionic(eq):
        return False
    # Reject obvious OCR-loss no-op reactions.
    if canonical_equation(eq).split("→")[0:1] == canonical_equation(eq).split("→")[1:2]:
        return False
    if re.match(r"^\s*2?H2O\s*\+\s*O2\s*→\s*2?H2O\s*$", eq):
        return False
    return True


def parse_definitions(text: str) -> dict[str, list[str]]:
    defs = {}
    low = text.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "hal" in key or "гал" in key:
                defs["X"] = values; defs["Hal"] = values
    for m in re.finditer(r"\b(M|X|Hal|Me|E|Э)\s*(?:=|->|→)\s*([^;)]+)", text):
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
        if group and candidates:
            out.append(re.sub(rf"\b{candidates[-1]}\b", alt, base))
    return list(dict.fromkeys(out))


def expand_templates(eq: str, context: str) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found = []
    for v in ["M", "X", "Hal", "Me", "E", "Э"]:
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
            cur = re.sub(rf"(?<![A-Za-z]){re.escape(v)}(?![a-z])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def canonical_equation(eq: str) -> str:
    eq = fix_ocr_formula(eq).lower()
    eq = eq.replace("⇌", "→").replace("=", "→")
    if "≠" in eq:
        side = eq.split("≠", 1)[0]
        return "+".join(sorted(_clean_species(side))) + "≠"
    if "→" not in eq:
        return re.sub(r"\s+", "", eq)
    left, right = eq.split("→", 1)
    l = "+".join(sorted(_clean_species(left)))
    r = "+".join(sorted(_clean_species(right)))
    # Treat reverse reaction as duplicate too.
    return "→".join(sorted([l, r]))


def _clean_species(side: str) -> list[str]:
    parts = []
    for p in side.split("+"):
        p = re.sub(r"^\s*\d+(?:[,.]\d+)?\s*", "", p.strip())
        p = re.sub(r"\s+", "", p)
        if p:
            parts.append(p)
    return parts


def _merge_broken_lines(lines: list[str]) -> list[str]:
    out = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while cur.rstrip().endswith("+") and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt.startswith("+"):
                cur = cur.rstrip() + " " + nxt[1:].strip()
                i += 1
            else:
                break
        out.append(cur)
        i += 1
    return out


def _condition_like(line: str) -> bool:
    line = _clean_spaces(line)
    return bool(line and len(line) <= 80 and CONDITION_HINT_RE.search(line) and not FORMULA_TOKEN_RE.search(line.replace("H2", "")))


def _score(r: ExtractedReaction) -> int:
    return sum(len(str(x or "")) for x in [r.conditions, r.catalysts, r.solvents, r.temperature, r.pressure, r.reaction_name]) + len(r.equation)


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_broken_lines(raw_lines)
    reactions: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        prev = lines[idx - 1] if idx > 0 and _condition_like(lines[idx - 1]) else ""
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+4)])
        eq, meta, name, negative = split_equation_and_conditions(raw, prev)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate):
                continue
            if "≠" in candidate:
                left = candidate.split("≠", 1)[0].strip()
                reactions.append(ExtractedReaction(
                    equation=candidate, reactants=left, products="", conditions="; ".join(meta["arrow_conditions"] or meta["conditions"]),
                    confidence_score=0.95, hidden=True, impossible_note="не реагируют между собой", reaction_name=name,
                ))
                continue
            (left, right), arrow = _split_lr(candidate)
            arrow_conditions = ", ".join(meta["arrow_conditions"])
            conditions = "; ".join(dict.fromkeys([*meta["conditions"], arrow_conditions] if arrow_conditions else meta["conditions"]))
            reactions.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}", reactants=left.strip(), products=right.strip(),
                conditions=conditions, catalysts="; ".join(meta["catalysts"]), solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]), pressure="; ".join(meta["pressure"]),
                states="", confidence_score=0.92, reaction_name=name,
            ))
    dedup: dict[str, ExtractedReaction] = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _score(r) > _score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())
