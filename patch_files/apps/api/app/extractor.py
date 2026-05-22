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

PERIODIC_GROUP = {}
for n, arr in [(1,ALKALI),(2,ALKALINE_EARTH),(13,GROUP_13),(14,GROUP_14),(15,GROUP_15),(16,GROUP_16),(17,GROUP_17)]:
    for e in arr:
        PERIODIC_GROUP[e] = n

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
    confidence_score: float = 0.92
    reaction_name: str = ""

_FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-↑↓%]*)")
_TEMPLATE_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(Hal|Me|M|X|E|Э)(?![a-zа-я])")
_ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b")
_BAD_CONTEXT_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|электронн|баланс|pka|pkb|pkа|pkб|пка|пкб|пр\s*=)\b|[ē]", re.I)
_FREE_ION_RE = re.compile(r"(^|[\s+])(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|[A-Z][a-z]?\d*)\s*(?:\^?\d*[+\-]|[⁺⁻])\s*(?=(?:[+→⇌]|$))")
_EXPLANATION_WORDS = [
    "оксид","оксиды","пероксид","пероксиды","надпероксид","надпероксиды","галогенид","галогениды","карбид","карбиды",
    "фосфид","фосфиды","гидрид","гидриды","сульфид","сульфиды","нитрид","нитриды","силицид","силициды",
    "самовозгорание","без горения","горит","бурная реакция","взрыв","ядовитый газ"
]
_NAME_WORDS = ["синтез рашиг", "метод байер", "габер", "бош", "магическая кислота", "основание миллона", "тефлон"]

def _clean_spaces(text: str) -> str:
    text = str(text or "")
    replacements = {
        "⟶":"→", "⟹":"→", "->":"→", "=>":"→",
        "<=>":"⇌", "<->":"⇌", "↔":"⇌", "⇄":"⇌",
        "−":"-", "–":"-", "—":"-", "∙":"·", "⋅":"·",
        "↑":"↑", "↓":"↓",
        "в†’":"→", "в‡Њ":"⇌", "в†‘":"↑", "в†“":"↓", "в‰ ":"≠",
        "В°":"°", "Р°":"а", "Рє":"к", "Рѕ":"о", "РЅ":"н", "С†":"ц"
    }
    for a,b in replacements.items():
        text = text.replace(a,b)
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"[;,.]\s*$", "", text)

def _translate_lookalikes(text: str) -> str:
    tr = str.maketrans({
        "А":"A","В":"B","С":"C","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","Т":"T","Х":"X",
        "а":"a","с":"c","е":"e","о":"o","р":"p","х":"x",
        "₀":"0","₁":"1","₂":"2","₃":"3","₄":"4","₅":"5","₆":"6","₇":"7","₈":"8","₉":"9",
        "⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9",
        "⁺":"+","⁻":"-"
    })
    return text.translate(tr)

def strip_oxidation_states(text: str) -> str:
    """Remove all oxidation-state / superscript charge marks from equation text."""
    text = _clean_spaces(_translate_lookalikes(text))
    # H2^0 / H20 on boundary must become H2, not H2O.
    text = re.sub(r"\bH2\s*\^?\s*0\b", "H2", text)
    text = re.sub(r"\bH20(?=\s*(?:[+→⇌]|$))", "H2", text)
    # common OCR water variants
    text = text.replace("H₂O", "H2O").replace("H₂", "H2").replace("H20", "H2O")
    # remove charge/oxidation from bracketed complexes too: [S8^2+] -> [S8], [AsF6-] -> [AsF6]
    text = re.sub(r"\[([^\]]*?)\s*\^\s*\d*[+-]\]", r"[\1]", text)
    text = re.sub(r"\[([^\]]*?[A-Za-z0-9)])\s*\d*[+-]\]", r"[\1]", text)
    # element oxidation states outside brackets: Ca0, Al+3, H-1
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?(?:\([^)]*\)\d*)?)\s*\^?\s*(?:0|[+-]\s*\d+)(?=($|[\s+→⇌),]))", r"\1", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+)?)(?:[+-]\s*\d+)(?=[A-Z(\[])", r"\1", text)
    # Al + 3(OH)4 -> Al(OH)4 inside OCR formula
    text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*\d+\s*(?=\()", r"\1", text)
    # + 1H -> + H, trailing H-1/H+1 -> H
    text = re.sub(r"(?<=[+→⇌]\s)\d+\s*H(?=($|[\s+]))", "H", text)
    text = re.sub(r"\bH(\d*)\s*[+-]\s*\d+\b", r"H\1", text)
    return _clean_spaces(text)

def fix_ocr_formula(text: str) -> str:
    text = strip_oxidation_states(text)
    text = text.replace("O2^", "O2↑").replace("O2 ^", "O2↑")
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV]\b", r"\1↓", text)
    text = re.sub(r"H2\+1O", "H2O", text)
    text = re.sub(r"H2\+1S", "H2S", text)
    # hydride OCR repairs
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
    def norm_side(side):
        return "+".join(sorted(re.sub(r"^\d+(?:[,.]\d+)?", "", t) for t in side.split("+") if t))
    return "||".join(sorted([norm_side(left), norm_side(right)]))

def _normalize_condition_text(cond: str) -> str:
    cond = _clean_spaces(cond)
    cond = cond.replace("o C", "°C").replace("oC", "°C")
    cond = re.sub(r"(\d)\s*°\s*C", r"\1 °C", cond)
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
    if re.search(r"(^|[\s,])p([\s,]|$)|давлен|pressure", cond, flags=re.I):
        data["pressure"].append("p" if re.search(r"(^|[\s,])p([\s,]|$)", cond) else cond)
    if any(x in low for x in ["электролиз", "эл. ток", "эл ток", "electric", "⚡"]):
        data["conditions"].append("электролиз")
    if "расплав" in low or "melt" in low:
        data["conditions"].append("расплав")
    # preserve full arrow label
    if cond and cond not in data["conditions"]:
        data["conditions"].append(cond)
    for cat in ["Pt","Pd","Ni","Fe","Rh","Rh/Pt","MnO2","V2O5","AlCl3","FeCl3"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4","SO2","ацетон","желатин","EtOH","MeOH","DMSO"]:
        if solv.lower() in low:
            data["solvents"].append(solv)
    return data

def _unique_join(items):
    out = []
    for item in items:
        item = _clean_spaces(item)
        if item and item not in out:
            out.append(item)
    return "; ".join(out)

def merge_meta(*metas: dict) -> dict:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    for meta in metas:
        for key in out:
            for val in meta.get(key, []):
                val = _clean_spaces(val)
                if val and val not in out[key]:
                    out[key].append(val)
    return out

def _looks_like_condition_only(line: str) -> bool:
    s = _clean_spaces(line)
    if not s or any(a in s for a in ["→", "⇌", "≠", "+"]):
        return False
    if len(s) > 80:
        return False
    return bool(re.search(r"(^|[\s,])(t|p|Δ)([\s,]|$)|°\s*C|\b\d{2,5}\s*K\b|кат|Fe|Ni|Pt|P4O10|SO2|CrO3|HNO3|F2|NaF|желатин|ацетон|в токе", s, re.I))

def split_equation_and_conditions(line: str):
    line = fix_ocr_formula(line)
    reaction_name = ""
    if "≠" in line:
        return None, normalize_condition(""), ""
    m = re.search(r"\(([^()]*)\)\s*$", line)
    if m:
        inner = m.group(1).strip()
        ilow = inner.lower()
        if any(w in ilow for w in _NAME_WORDS):
            reaction_name = inner
            line = line[:m.start()].strip()
        elif any(w in ilow for w in _EXPLANATION_WORDS):
            line = line[:m.start()].strip()
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), reaction_name
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if any(a.group(1) == "⇌" for a in arrows[:2]) else "→"
        eq = fix_ocr_formula(f"{left} {arrow} {right}")
        if re.search(r"кат\.?\s*\(?Fe\)?", middle, flags=re.I) and "N2" in left and "NH3" in right:
            arrow = "⇌"
            eq = fix_ocr_formula(f"{left} {arrow} {right}")
            reaction_name = reaction_name or "Синтез аммиака (процесс Габера-Боша)"
        return eq, normalize_condition(middle), reaction_name
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(""), reaction_name

def looks_like_reaction(eq: str) -> bool:
    eq = fix_ocr_formula(eq)
    if not eq or not ("→" in eq or "⇌" in eq):
        return False
    if _BAD_CONTEXT_RE.search(eq):
        return False
    if _ORGANIC_TEMPLATE_RE.search(eq):
        return False
    if _FREE_ION_RE.search(eq) and "[" not in eq:
        return False
    if re.search(r"\b(e|ē)\s*[-+]|\be[-+]\b", eq):
        return False
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    if left.strip().endswith("+") or right.strip().endswith("+"):
        return False
    if not _FORMULA_TOKEN_RE.search(left) or not _FORMULA_TOKEN_RE.search(right):
        return False
    if len(right.strip()) < 2:
        return False
    return True

def parse_definitions(text: str) -> dict[str, list[str]]:
    defs = {}
    text_norm = _clean_spaces(text).replace("М", "M").replace("Х", "X")
    low = text_norm.lower()
    for key, values in GROUP_ALIASES.items():
        if key in low:
            defs.setdefault("M", values)
            if "гал" in key or "hal" in key:
                defs["X"] = values
                defs["Hal"] = values
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
        candidates = [e for e in elements if PERIODIC_GROUP.get(e) == group and e != alt]
        if candidates:
            out.append(re.sub(rf"\b{candidates[-1]}\b", alt, base))
    return list(dict.fromkeys(out))

def expand_templates(eq: str, context: str) -> list[str]:
    eq = fix_ocr_formula(eq).replace("М", "M").replace("Х", "X")
    defs = parse_definitions(eq + " " + context)
    if not _TEMPLATE_RE.search(eq):
        return infer_parenthetical_substitution(eq)
    vars_found = []
    for v in ["Hal", "Me", "M", "X", "E", "Э"]:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]; vars_found.append("X")
            elif v == "Me" and "M" in defs:
                defs["Me"] = defs["M"]; vars_found.append("Me")
            else:
                return []
    base = re.sub(r"\([^)]*(?:=|->|→|-|—)[^)]*\)", "", eq).strip()
    expanded = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            
            if v in ["M", "X", "E", "Э"]:
                # In formulas variables can be embedded in a token: KX -> KCl, MH -> NaH.
                # Do not replace before lowercase letters, so Mg is not treated as M + g.
                pattern = rf"(?<![a-zа-я]){re.escape(v)}(?![a-zа-я])"
            else:
                pattern = rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![a-zа-я])"
            cur = re.sub(pattern, val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))

def _merge_broken_lines(lines: list[str]) -> list[str]:
    merged = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        while cur.endswith("+") and i + 1 < len(lines):
            i += 1
            cur = cur + " " + lines[i].strip().lstrip("+ ").strip()
        merged.append(cur)
        i += 1
    return merged

def _score(r: ExtractedReaction) -> int:
    return sum(len(getattr(r, f, "") or "") for f in ["equation","conditions","catalysts","solvents","temperature","pressure","states","reaction_name"])

def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = _merge_broken_lines(raw_lines)
    reactions = []
    for idx, raw in enumerate(lines):
        if _BAD_CONTEXT_RE.search(raw):
            continue
        context = " ".join(lines[max(0, idx-5): min(len(lines), idx+5)])
        eq, meta, reaction_name = split_equation_and_conditions(raw)
        if not eq:
            continue
        # condition-only line immediately before a reaction is treated as arrow label from PDF layout
        if not any(meta.values()) and idx > 0 and _looks_like_condition_only(lines[idx-1]):
            meta = merge_meta(meta, normalize_condition(lines[idx-1]))
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            candidate = re.sub(r"\b2(Li|Na|K|Rb|Cs)\s*\+\s*H2\s*→\s*2\1\s*\+\s*H\b", r"2\1 + H2 → 2\1H", candidate)
            if not looks_like_reaction(candidate):
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
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
    dedup = {}
    for r in reactions:
        key = canonical_equation(r.equation)
        if key not in dedup or _score(r) > _score(dedup[key]):
            dedup[key] = r
    return list(dedup.values())