from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ARROW_RE = re.compile(r"(->|=>|<->|<=>|→|⇌|⟶|↔|=)")
FORMULA_RE = re.compile(r"(?:\d*\s*)?(?:\[[^\]]+\]|[A-ZА-Я][a-zа-я]?)(?:[A-Za-zА-Яа-я0-9()\[\].·+\-↑↓]*)")
TEMPLATE_CONTEXT_RE = re.compile(
    r"\b(M|X|Hal|Me|E|Э)\s*(?:=|→|->|-)|щелоч|щзм|щм|галоген|халькоген|пниктоген|group\s*(?:13|14|15|16|17)|(?:13|14|15|16|17)\s*группа",
    re.I,
)
BAD_PROSE_RE = re.compile(r"\b(рис\.|таблица|пример|задача|вопрос|ответ|упражнение|страница)\b", re.I)
IONIC_OR_ELECTRODE_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|баланс|pka|pkb|пка|пкб|пр\s*=)\b|[ē]", re.I)
BAD_METADATA_RE = re.compile(r"\b(pka|pkb|пка|пкб|пр\s*=|ПР\s*=|lg\s*\(|lg\s*[A-Za-zА-Яа-я]?\s*=|кч\s*=)\b", re.I)


@dataclass
class LayoutLine:
    text: str
    page_no: int
    x0: float
    y0: float
    x1: float
    y1: float


def _clean(s: str) -> str:
    if not s:
        return ""
    repl = {
        "": "⚡",
        "⎯": " ",
        "─": " ",
        "—": "-",
        "–": "-",
        "оС": "°C",
        "o C": "°C",
        "oC": "°C",
        "Сo": "°C",
        "Со": "°C",
        "⟶": "→",
        "=>": "→",
        "->": "→",
        "<=>": "⇌",
        "<->": "⇌",
        "↔": "⇌",
        "тЖТ": "→",
        "тЖУ": "↓",
        "тЖС": "↑",
        "тЙа": "≠",
        "┬╖": "·",
        "╨║╨╛╨╜╤Ж.": "конц.",
        "╨║o╨╜╤Ж.": "конц.",
        "pa╨╖╨▒.": "разб.",
        "╤А╨░╨╖╨▒.": "разб.",
        "╨╢.": "ж.",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _looks_like_condition_line(text: str) -> bool:
    t = _clean(text)
    if not t or ARROW_RE.search(t) or BAD_METADATA_RE.search(t):
        return False
    if len(t) > 90:
        return False
    # Any visually isolated text above the arrow is a condition, not only a fixed whitelist.
    # Still require at least one condition-like clue so random prose is not attached.
    if re.search(r"\b(t|p|hv|hν|Δ|кат\.?|нагрев|электролиз|расплав|ток|ж\.|газ|свет|давл|охлажд|кип|спирт|эфир)\b", t, re.I):
        return True
    if re.search(r"\d{1,4}\s*(?:-\s*\d{1,4}\s*)?(?:°\s*C|°C|K)\b", t, re.I):
        return True
    if re.search(r"\b(P4O10|SO2|CrO3|HNO3|F2|NaF|Pt|Pd|Ni|Fe|MnO2|V2O5|AlCl3|FeCl3|CCl4|H2)\b", t):
        return True
    # Short formula-only labels over arrows, such as "SO2 ж" or "P4O10".
    formulas = FORMULA_RE.findall(t)
    return 1 <= len(formulas) <= 3 and len(t) <= 40


def _line_score(text: str) -> int:
    t = _clean(text)
    if not t:
        return -20
    score = 0
    if ARROW_RE.search(t):
        score += 8
    formulas = FORMULA_RE.findall(t)
    if len(formulas) >= 2:
        score += 5
    elif len(formulas) == 1:
        score += 1
    if _looks_like_condition_line(t):
        score += 2
    if TEMPLATE_CONTEXT_RE.search(t):
        score += 3
    if BAD_PROSE_RE.search(t):
        score -= 6
    if IONIC_OR_ELECTRODE_RE.search(t) and not ("[" in t and "]" in t and ARROW_RE.search(t)):
        score -= 8
    if len(t) > 180:
        score -= 3
    return score


def extract_layout_lines(page: Any) -> list[LayoutLine]:
    out: list[LayoutLine] = []
    try:
        d = page.get_text("dict")
        page_no = int(getattr(page, "number", 0)) + 1
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = _clean("".join(s.get("text", "") for s in spans))
                if not text:
                    continue
                bbox = line.get("bbox") or block.get("bbox") or (0, 0, 0, 0)
                out.append(LayoutLine(text, page_no, *bbox))
    except Exception:
        try:
            raw = page.get_text("text") or ""
        except Exception:
            raw = ""
        page_no = int(getattr(page, "number", 0)) + 1
        for i, line in enumerate(raw.splitlines()):
            text = _clean(line)
            if text:
                out.append(LayoutLine(text, page_no, 0, i * 10, 100, i * 10 + 8))
    out.sort(key=lambda l: (round(l.y0, 1), l.x0))
    return out


def _inject_condition_into_reaction(reaction: str, condition: str) -> str:
    reaction = _clean(reaction)
    condition = _clean(condition)
    if not condition or BAD_METADATA_RE.search(condition):
        return reaction
    m = ARROW_RE.search(reaction)
    if not m:
        return reaction
    left = reaction[:m.start()].strip()
    right = reaction[m.end():].strip()
    arrow = "⇌" if m.group(1) in {"⇌", "<->", "<=>", "↔"} else "→"
    return f"{left} {arrow} {condition} {arrow} {right}"


def build_hybrid_page_text(page: Any) -> str:
    """Return reaction-like lines and attach only visually over-arrow condition text.

    If a short condition line is visually placed above/near an equation arrow,
    this returns a synthetic line: A → condition → B. The extractor then stores
    condition separately and keeps A → B as the equation. Conditions are not copied
    to unrelated reactions.
    """
    lines = extract_layout_lines(page)
    if not lines:
        return ""

    result: list[str] = []
    used_condition_indexes: set[int] = set()

    for i, ln in enumerate(lines):
        if _line_score(ln.text) < 6 or not ARROW_RE.search(ln.text):
            continue

        best_cond: tuple[float, int, str] | None = None
        arrow_center_x = (ln.x0 + ln.x1) / 2

        # Search only close lines above this equation. This prevents bleed to other reactions.
        for j in range(max(0, i - 4), i):
            cand = lines[j]
            if j in used_condition_indexes or not _looks_like_condition_line(cand.text):
                continue
            vertical_gap = ln.y0 - cand.y1
            if vertical_gap < -2 or vertical_gap > 55:
                continue
            cand_center_x = (cand.x0 + cand.x1) / 2
            # Conditions over arrows are usually near the horizontal center or inside equation width.
            x_ok = (ln.x0 - 30 <= cand_center_x <= ln.x1 + 30) or abs(cand_center_x - arrow_center_x) < 180
            if not x_ok:
                continue
            score = vertical_gap + abs(cand_center_x - arrow_center_x) * 0.15
            if best_cond is None or score < best_cond[0]:
                best_cond = (score, j, cand.text)

        if best_cond:
            used_condition_indexes.add(best_cond[1])
            result.append(_inject_condition_into_reaction(ln.text, best_cond[2]))
        else:
            result.append(_clean(ln.text))

        # Keep a following template definition line, but not arbitrary conditions.
        if i + 1 < len(lines) and TEMPLATE_CONTEXT_RE.search(lines[i + 1].text):
            result.append(_clean(lines[i + 1].text))

    # Add standalone template-definition lines if no reaction was selected nearby.
    for i, ln in enumerate(lines):
        if TEMPLATE_CONTEXT_RE.search(ln.text) and _clean(ln.text) not in result:
            result.append(_clean(ln.text))

    return "\n".join(result).strip()
