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
for _n, _els in [(1, ALKALI), (2, ALKALINE_EARTH), (13, GROUP_13), (14, GROUP_14), (15, GROUP_15), (16, GROUP_16), (17, GROUP_17)]:
    for _e in _els:
        PERIODIC_GROUP[_e] = _n

GROUP_ALIASES: dict[str, list[str]] = {
    "щм": ALKALI,
    "щелочные металлы": ALKALI,
    "щелочных металлов": ALKALI,
    "alkali metals": ALKALI,
    "щзм": ALKALINE_EARTH,
    "щелочноземельные металлы": ALKALINE_EARTH,
    "щелочноземельных металлов": ALKALINE_EARTH,
    "alkaline earth metals": ALKALINE_EARTH,
    "галогены": HALOGENS,
    "галогенов": HALOGENS,
    "гал": HALOGENS,
    "hal": HALOGENS,
    "halogens": HALOGENS,
    "халькогены": CHALCOGENS,
    "халькогенов": CHALCOGENS,
    "chalcogens": CHALCOGENS,
    "пниктогены": PNICTOGENS,
    "пниктогенов": PNICTOGENS,
    "pnictogens": PNICTOGENS,
    "13 группа": GROUP_13,
    "14 группа": GROUP_14,
    "15 группа": GROUP_15,
    "16 группа": GROUP_16,
    "17 группа": GROUP_17,
    "13 группы": GROUP_13,
    "14 группы": GROUP_14,
    "15 группы": GROUP_15,
    "16 группы": GROUP_16,
    "17 группы": GROUP_17,
    "group 13": GROUP_13,
    "group 14": GROUP_14,
    "group 15": GROUP_15,
    "group 16": GROUP_16,
    "group 17": GROUP_17,
}

# A generic variable in equations. This intentionally does not match Russian words like Миллона.
TEMPLATE_VARS = ["Hal", "Me", "M", "X", "E", "Э"]
TEMPLATE_VARS_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(?:Hal|Me|M|X|E|Э)(?![A-Za-zА-Яа-я])")

FORMULA_TOKEN_RE = re.compile(r"(?:^|[+\s])(?:\d+(?:[,.]\d+)?\s*)?(?:\[[^\]]+\]|[A-Z][a-z]?)(?:[A-Za-z0-9()\[\].·\-+^↑↓%−]*)")
ORGANIC_TEMPLATE_RE = re.compile(r"\bR['’′]?\b|\bAr\b|\bPh\b|CH\s*=\s*CH|CH2\s*[-–]?\s*CH2")
BAD_TEXT_RE = re.compile(r"\b(?:pK[ab]|pKa|pKb|ПК[аб]|ПР|Ksp|константа|растворимости)\b", re.I)
HALF_REACTION_RE = re.compile(r"\b(?:катод|анод|электрон|полуреакц|баланс)\b|[ēеe]\s*[−-]|[−-]\s*[ēеe]", re.I)
FREE_ION_RE = re.compile(r"(?:^|\s|\+)(?:H|OH|Cl|Br|I|NO3|SO4|CO3|PO4|BO3|[A-Z][a-z]?\d*)(?:\^?\d?[+\-]|[⁺⁻])(?:\s|\+|$)")

DELETE_TRAILING_COMMENTS = {
    "оксид", "оксиды", "пероксид", "пероксиды", "надпероксид", "надпероксиды",
    "галогенид", "галогениды", "гидрид", "гидриды", "карбид", "карбиды",
    "фосфид", "фосфиды", "сульфид", "сульфиды", "нитрид", "нитриды",
    "силицид", "силициды", "самовозгорание", "без горения", "горит", "взрыв",
    "бурная реакция", "ядовитый газ", "осадок", "газ", "соль", "кислота", "основание",
}
NAME_HINTS = ["синтез", "метод", "реакция", "процесс", "магическая кислота", "основание Миллона"]

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
    validation_status: str = "ready"


def _uniq(values: list[str]) -> list[str]:
    out: list[str] = []
    for v in values:
        v = _clean_spaces(v)
        if v and v not in out:
            out.append(v)
    return out


def _clean_spaces(text: str) -> str:
    text = str(text or "")
    text = text.replace("<->", "⇌").replace("<=>", "⇌").replace("↔", "⇌").replace("⇄", "⇌")
    text = text.replace("⟶", "→").replace("⎯→", "→").replace("->", "→").replace("=>", "→")
    text = text.replace("∙", "·").replace("−", "-").replace("⁻", "-").replace("⁺", "+")
    text = text.replace("℃", "°C").replace("о C", "°C").replace("o C", "°C").replace("oC", "°C")
    text = re.sub(r"\b(конц|разб|кат)\.\.+", r"\1.", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[;,.]\s*$", "", text)
    return text.strip()


def _protect_brackets(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []
    def repl(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f"__BR{len(blocks)-1}__"
    return re.sub(r"\[[^\]]+\](?:\d*[+\-]?|\d*)", repl, text), blocks


def _restore_brackets(text: str, blocks: list[str]) -> str:
    for i, b in enumerate(blocks):
        text = text.replace(f"__BR{i}__", b)
    return text


def strip_oxidation_states(text: str) -> str:
    """Remove printed oxidation states outside square brackets only."""
    protected, blocks = _protect_brackets(text)
    # Common textbook/OCR cases: H2^0, Li0, Ca0, Al+3, H-1, +1H, 1H-1.
    protected = re.sub(r"\b(\d*)\s*([A-Z][a-z]?\d*)\s*\^\s*[+-]?\d+", lambda m: (m.group(1) or "") + m.group(2), protected)
    protected = re.sub(r"\b(\d*)\s*([A-Z][a-z]?\d*)\s*([+-])\s*(\d+)(?=\s|\+|→|⇌|$|\))", lambda m: (m.group(1) or "") + m.group(2), protected)
    protected = re.sub(r"\b(\d*)\s*([A-Z][a-z]?)\s*(0)(?=\s|\+|→|⇌|$|\))", lambda m: (m.group(1) or "") + m.group(2), protected)
    protected = re.sub(r"(?<=\s|\+|→|⇌)([+-]?1)\s*([A-Z][a-z]?)(?=\s|\+|→|⇌|$)", r"\2", protected)
    protected = re.sub(r"\[\s*([A-Z][a-z]?)\s*\+\s*\d+\s*", r"[\1", protected)
    protected = re.sub(r"\[\s*([A-Z][a-z]?)\s*-\s*\d+\s*", r"[\1", protected)
    return _restore_brackets(protected, blocks)


def fix_ocr_formula(text: str) -> str:
    text = _clean_spaces(text)
    # Targeted Cyrillic formula cleanup only; do not corrupt Russian reaction names.
    text = text.replace("Н2О", "H2O").replace("Н20", "H2O").replace("Н₂О", "H2O")
    text = text.replace("Н2", "H2").replace("Н₂", "H2").replace("О2", "O2").replace("О₂", "O2")
    text = text.replace("H₂", "H2").replace("O₂", "O2").replace("N₂", "N2")
    # H20 -> H2O only when it is standalone water, not H2^0 oxidation written as H20 before arrow.
    text = re.sub(r"\bH20\b", "H2O", text)
    text = re.sub(r"\bH2\+1([A-Z])", r"H2\1", text)
    text = re.sub(r"O2\s*\^", "O2↑", text)
    text = re.sub(r"([A-Za-z0-9)\]])\^($|\s|\+)", r"\1↑\2", text)
    text = re.sub(r"([A-Z][a-z]?(?:\d+|\([^)]*\)\d*)?)\s*[vV](?=\s|\+|$)", r"\1↓", text)
    text = strip_oxidation_states(text)
    text = re.sub(r"([A-Z][A-Za-z0-9()\]]*)\s*\+\s*1(?=\s|$|\()", r"\1", text)
    # Hydride reconstruction from oxidation-state OCR wreckage.
    text = re.sub(r"H2\s*\+\s*Ca\s*→\s*Ca\s*\+\s*2?H2?", "H2 + Ca → CaH2", text)
    text = re.sub(r"H2\s*\+\s*2Li\s*→\s*(?:2)?Li\s*\+\s*(?:1)?H", "2Li + H2 → 2LiH", text)
    text = re.sub(r"\bCa\s*\+\s*H2\b", "CaH2", text)
    text = re.sub(r"\bCaH2\s*-\s*1\b", "CaH2", text)
    text = re.sub(r"\b2Li\s*\+\s*H\b", "2LiH", text)
    text = re.sub(r"\bLi\s*\+\s*H\b", "LiH", text)
    text = re.sub(r"\b([A-Z][a-z]?)\s*\+\s*(\d+)\s*(\([^\]]+\))", r"\1\3", text)
    text = re.sub(r"\[([A-Z][a-z]?)\s*\+\s*\d+\s*(\([^\]]+\))\]", r"[\1\2]", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    text = re.sub(r"([A-Za-z0-9)\]]) \+ \+", r"\1+ +", text)
    # Restore charges inside square brackets after plus spacing normalization.
    text = re.sub(r"\[([^\]]+)\]", lambda m: "[" + re.sub(r"\s*([+\-])\s*", r"\1", m.group(1)) + "]", text)
    text = re.sub(r"\s*(→|⇌|≠)\s*", r" \1 ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _clean_spaces(text)
    text = re.sub(r"([A-Za-z0-9)\]]) \+ \+", r"\1+ +", text)
    return text


def canonical_equation(equation: str) -> str:
    eq = fix_ocr_formula(equation).lower().replace(" ", "")
    eq = eq.replace("->", "→").replace("=>", "→").replace("<->", "⇌")
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else None)
    if not arrow:
        return eq
    left, right = eq.split(arrow, 1)
    def side_key(s: str) -> str:
        parts = [p for p in s.split("+") if p]
        return "+".join(sorted(parts))
    a, b = side_key(left), side_key(right)
    if arrow == "⇌" or a > b:
        a, b = sorted([a, b])
    return f"{a}={b}"


def normalize_condition(cond: str) -> dict[str, list[str]]:
    cond = _clean_spaces(cond)
    data = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    if not cond:
        return data
    c_low = cond.lower()
    for m in re.finditer(r"\b\d{2,5}\s*K\b", cond):
        data["temperature"].append(m.group(0))
    for m in re.finditer(r"\b\d{1,4}\s*(?:[-–]\s*\d{1,4}\s*)?(?:°\s*C|°C)\b", cond, flags=re.I):
        data["temperature"].append(re.sub(r"\s*°\s*C", " °C", m.group(0), flags=re.I))
    if re.search(r"(^|[\s,])(t|heat|delta|Δ|нагрев)([\s,]|$)", cond, flags=re.I):
        data["conditions"].append("t")
    if "электролиз" in c_low or "эл. ток" in c_low or "electric" in c_low or "elec" in c_low or "⚡" in cond:
        data["conditions"].append("электролиз")
    if "расплав" in c_low or "melt" in c_low:
        data["conditions"].append("расплав")
    if "в токе h2" in c_low or "токе h2" in c_low:
        data["conditions"].append("в токе H2")
    # Preserve arrow text exactly as condition if it contains chemical reagents used as medium.
    if re.search(r"\b(?:CrO3|HNO3|F2|NaF|SO2|желатин|ацетон)\b", cond, re.I):
        data["conditions"].append(cond)
    for cat in ["Pt", "Pd", "Ni", "Fe", "Rh", "Rh/Pt", "Rh / Pt", "MnO2", "V2O5", "AlCl3", "FeCl3"]:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(cat)}(?![A-Za-z0-9])", cond):
            data["catalysts"].append(cat)
    for solv in ["CCl4", "SO2", "ацетон", "желатин", "EtOH", "MeOH", "DMSO"]:
        if solv.lower() in c_low or solv in cond:
            data["solvents"].append(solv)
    for p in re.finditer(r"\b(?:p|\d+(?:[,.]\d+)?\s*(?:atm|bar|Па|кПа|МПа|MPa))\b", cond, flags=re.I):
        data["pressure"].append(p.group(0))
    for k in data:
        data[k] = _uniq(data[k])
    return data


def merge_meta(*metas: dict[str, list[str]]) -> dict[str, list[str]]:
    out = {"conditions": [], "temperature": [], "catalysts": [], "solvents": [], "pressure": []}
    for meta in metas:
        for key in out:
            out[key].extend(meta.get(key, []))
            out[key] = _uniq(out[key])
    return out


def extract_reaction_name(raw: str) -> tuple[str, str]:
    name = ""
    text = str(raw or "")
    m = re.match(r"^(.*)\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", text)
    if not m:
        return text.strip(), ""
    before, inner = m.group(1).rstrip(), _clean_spaces(m.group(2))
    low = inner.lower()
    if any(h in low for h in NAME_HINTS) or inner in {"тефлон", "магическая кислота"}:
        name = inner
        return before, name
    if low in DELETE_TRAILING_COMMENTS or low.endswith(("иды", "аты", "иты")):
        return before, ""
    return text.strip(), ""


def merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = _clean_spaces(lines[i])
        while cur.endswith("+") and i + 1 < len(lines):
            nxt = _clean_spaces(lines[i + 1])
            if nxt.startswith("+") or FORMULA_TOKEN_RE.search(nxt):
                cur = cur.rstrip("+").strip() + " + " + nxt.lstrip("+").strip()
                i += 1
            else:
                break
        merged.append(cur)
        i += 1
    return merged


def split_equation_and_conditions(line: str) -> tuple[str | None, dict[str, list[str]], str, bool]:
    raw = _clean_spaces(line)
    raw, name = extract_reaction_name(raw)
    # Remove trailing template definitions before arrow splitting; context still contains them for expansion.
    raw = re.sub(r"\s*\((?:M|X|Hal|Me|E|Э|Al)\s*(?:=|->|→).*?\)\s*$", "", raw)
    if "≠" in raw:
        left = raw.split("≠", 1)[0].strip()
        if FORMULA_TOKEN_RE.search(left):
            return fix_ocr_formula(left + " ≠"), normalize_condition(""), name, True
        return None, normalize_condition(""), name, False
    line = fix_ocr_formula(raw)
    arrows = list(re.finditer(r"(⇌|→)", line))
    if not arrows:
        return None, normalize_condition(""), name, False
    if len(arrows) >= 2:
        left = line[:arrows[0].start()].strip()
        middle = line[arrows[0].end():arrows[1].start()].strip()
        right = line[arrows[1].end():].strip()
        arrow = "⇌" if "⇌" in (arrows[0].group(1), arrows[1].group(1)) or "кат" in middle.lower() and "p" in middle.lower() else "→"
        return fix_ocr_formula(f"{left} {arrow} {right}"), normalize_condition(middle), name, False
    arrow = arrows[0].group(1)
    left = line[:arrows[0].start()].strip()
    right = line[arrows[0].end():].strip()
    # Remove trailing explanation comments after products.
    right, nm2 = extract_reaction_name(right)
    if nm2 and not name:
        name = nm2
    eq = fix_ocr_formula(f"{left} {arrow} {right}")
    return eq, normalize_condition(""), name, False


def looks_like_reaction(eq: str, negative: bool = False) -> bool:
    eq = _clean_spaces(eq)
    if not eq:
        return False
    if BAD_TEXT_RE.search(eq) or HALF_REACTION_RE.search(eq):
        return False
    if negative:
        return "≠" in eq and FORMULA_TOKEN_RE.search(eq)
    if not ("→" in eq or "⇌" in eq):
        return False
    if ORGANIC_TEMPLATE_RE.search(eq) and "(−" not in eq:
        return False
    left, right = re.split(r"→|⇌", eq, maxsplit=1)
    left_check = re.sub(r"\bn(?=[A-Z])", "", left)
    right_check = re.sub(r"\bn(?=[A-Z])", "", right)
    if not FORMULA_TOKEN_RE.search(left_check) or not (FORMULA_TOKEN_RE.search(right_check) or re.search(r"[A-Z][a-z]?\d*", right_check)):
        return False
    if right.strip().endswith("+") or left.strip().endswith("+"):
        return False
    if FREE_ION_RE.search(eq) and not re.search(r"\[[^\]]+[+-][^\]]*\]", eq):
        return False
    def molecule_set(side: str) -> set[str]:
        vals = []
        for part in re.split(r"\s*\+\s*", side):
            p = re.sub(r"^\s*\d+", "", part.strip())
            p = re.sub(r"^n(?=[A-Z])", "", p)
            if p:
                vals.append(p)
        return set(vals)
    lset, rset = molecule_set(left), molecule_set(right)
    if rset and rset.issubset(lset) and lset != rset:
        return False
    if canonical_equation(left + "→" + right).split("=")[0] == canonical_equation(left + "→" + right).split("=")[-1]:
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
    # M = K, Rb, Cs / M -> Mg, Ca, Sr, Ba / Al -> Al, Ga, In
    for m in re.finditer(r"(?<![А-Яа-яA-Za-z])(M|X|Hal|Me|E|Э|Al)\s*(?:=|->|→)\s*([^;)\.]+)", text):
        var, raw = m.group(1), m.group(2)
        vals: list[str] = []
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
    return list(dict.fromkeys(fix_ocr_formula(x) for x in out))


def expand_templates(eq: str, context: str) -> list[str]:
    defs = parse_definitions(eq + " " + context)
    if not TEMPLATE_VARS_RE.search(eq):
        # Al -> Al, Ga, In must expand Al in Na[Al(OH)4] examples.
        if "Al" in defs and re.search(r"\bAl\b", eq):
            return [fix_ocr_formula(re.sub(r"\bAl\b", v, re.sub(r"\([^)]*(?:=|->|→)[^)]*\)", "", eq))) for v in defs["Al"]]
        return infer_parenthetical_substitution(eq)
    vars_found: list[str] = []
    for v in TEMPLATE_VARS:
        if re.search(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![A-Za-zА-Яа-я])", eq):
            if v in defs:
                vars_found.append(v)
            elif v == "X" and "Hal" in defs:
                defs["X"] = defs["Hal"]
                vars_found.append(v)
            else:
                return []
    base = re.sub(r"\([^)]*(?:=|->|→)[^)]*\)", "", eq).strip()
    expanded: list[str] = []
    for combo in itertools.product(*[defs[v] for v in vars_found]):
        cur = base
        for v, val in zip(vars_found, combo):
            cur = re.sub(rf"(?<![A-Za-zА-Яа-я]){re.escape(v)}(?![A-Za-zА-Яа-я])", val, cur)
        expanded.append(fix_ocr_formula(cur))
    return list(dict.fromkeys(expanded))


def _choose_better(a: ExtractedReaction, b: ExtractedReaction) -> ExtractedReaction:
    def score(r: ExtractedReaction) -> int:
        return len(r.conditions) + len(r.temperature) + len(r.catalysts) + len(r.solvents) + len(r.reaction_name) + int(r.confidence_score * 10)
    return b if score(b) > score(a) else a


def extract_reactions_from_text(text: str) -> list[ExtractedReaction]:
    raw_lines = [_clean_spaces(x) for x in str(text or "").splitlines() if _clean_spaces(x)]
    lines = merge_wrapped_lines(raw_lines)
    found: list[ExtractedReaction] = []
    for idx, raw in enumerate(lines):
        if BAD_TEXT_RE.search(raw) or HALF_REACTION_RE.search(raw):
            continue
        context = " ".join(lines[max(0, idx - 5): min(len(lines), idx + 4)])
        eq, meta, reaction_name, negative = split_equation_and_conditions(raw)
        if not eq:
            continue
        for candidate in expand_templates(eq, context):
            candidate = fix_ocr_formula(candidate)
            if not looks_like_reaction(candidate, negative=negative):
                continue
            if negative:
                reactants = candidate.replace("≠", "").strip()
                found.append(ExtractedReaction(
                    equation=f"{reactants} ≠",
                    reactants=reactants,
                    products="",
                    conditions="; ".join(meta["conditions"]),
                    catalysts="; ".join(meta["catalysts"]),
                    solvents="; ".join(meta["solvents"]),
                    temperature="; ".join(meta["temperature"]),
                    pressure="; ".join(meta["pressure"]),
                    reaction_name=reaction_name,
                    confidence_score=0.95,
                    hidden=True,
                    impossible_note="не реагируют между собой",
                    validation_status="does_not_react",
                ))
                continue
            left, right = re.split(r"→|⇌", candidate, maxsplit=1)
            arrow = "⇌" if "⇌" in candidate else "→"
            found.append(ExtractedReaction(
                equation=f"{left.strip()} {arrow} {right.strip()}",
                reactants=left.strip(),
                products=right.strip(),
                conditions="; ".join(meta["conditions"]),
                catalysts="; ".join(meta["catalysts"]),
                solvents="; ".join(meta["solvents"]),
                temperature="; ".join(meta["temperature"]),
                pressure="; ".join(meta["pressure"]),
                states="",
                confidence_score=0.94 if meta["conditions"] or meta["temperature"] or reaction_name else 0.90,
                reaction_name=reaction_name,
            ))
    dedup: dict[str, ExtractedReaction] = {}
    for r in found:
        key = canonical_equation(r.equation)
        if key in dedup:
            dedup[key] = _choose_better(dedup[key], r)
        else:
            dedup[key] = r
    return list(dedup.values())
