from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ARROW_RE = re.compile(r"(->|=>|<->|<=>|→|⇌|⟶|↔|=)")
FORMULA_RE = re.compile(r"(?:\d*\s*)?(?:\[[^\]]+\]|[A-ZА-Я][a-zа-я]?)(?:[A-Za-zА-Яа-я0-9()\[\].·+\-↑↓]*)")
CONDITION_RE = re.compile(
    r"(^|[\s,])(t|p|hv|hν|Δ)([\s,]|$)|\d{1,4}\s*(?:-\s*\d{1,4}\s*)?(?:°\s*C|°C|o\s*C)|\d{2,5}\s*K|кат\.?|нагрев|электролиз|расплав|в токе|желатин|ацетон|SO2\s*ж|CrO3|HNO3|P4O10|F2|NaF|Pt|Pd|Ni|Fe|MnO2|V2O5",
    re.I,
)
TEMPLATE_CONTEXT_RE = re.compile(r"\b(M|X|Hal|Me|E|Э)\s*(?:=|→|->|-)|щелоч|щзм|щм|галоген|халькоген|пниктоген|group\s*(?:13|14|15|16|17)|(?:13|14|15|16|17)\s*группа", re.I)
BAD_PROSE_RE = re.compile(r"\b(рис\.|таблица|пример|задача|вопрос|ответ|упражнение|страница)\b", re.I)
IONIC_OR_ELECTRODE_RE = re.compile(r"\b(катод|анод|электрон|полуреакц|баланс|pka|pkb|пка|пкб|пр\s*=)\b|[ē]", re.I)

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
        "": "⚡", "⎯": " ", "─": " ", "—": "-", "–": "-",
        "оС": "°C", "o C": "°C", "oC": "°C", "Сo": "°C", "Со": "°C",
        "⟶": "→", "=>": "→", "->": "→", "<=>": "⇌", "<->": "⇌", "↔": "⇌",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    return s

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
    if CONDITION_RE.search(t):
        score += 3
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

def build_hybrid_page_text(page: Any) -> str:
    """Return reaction-like lines with only their visually adjacent condition lines.

    Important: condition lines are included only when close to a reaction arrow line.
    This prevents a condition from one reaction being attached to unrelated reactions.
    """
    lines = extract_layout_lines(page)
    if not lines:
        return ""
    selected: set[int] = set()

    for i, ln in enumerate(lines):
        score = _line_score(ln.text)
        if score >= 6:
            selected.add(i)

            # Add visually adjacent condition lines directly above/below this reaction.
            for j in (i - 2, i - 1, i + 1):
                if 0 <= j < len(lines):
                    near = lines[j]
                    vertical_gap = min(abs(near.y1 - ln.y0), abs(near.y0 - ln.y1), abs(near.y0 - ln.y0))
                    same_block_x = not (near.x1 < ln.x0 - 40 or near.x0 > ln.x1 + 40)
                    if vertical_gap < 45 and same_block_x and CONDITION_RE.search(near.text):
                        selected.add(j)

            # Add same-line or immediately following split products only when they look like formulas,
            # not arbitrary condition lines.
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                vertical_gap = abs(nxt.y0 - ln.y0)
                if vertical_gap < 25 and FORMULA_RE.search(nxt.text) and not BAD_PROSE_RE.search(nxt.text):
                    selected.add(i + 1)

        elif score >= 3 and TEMPLATE_CONTEXT_RE.search(ln.text):
            selected.add(i)

    result: list[str] = []
    last_y: float | None = None
    for idx in sorted(selected):
        ln = lines[idx]
        if last_y is not None and abs(ln.y0 - last_y) > 80:
            result.append("")
        result.append(ln.text)
        last_y = ln.y0
    return "\n".join(result).strip()
