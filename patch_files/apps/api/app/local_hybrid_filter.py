from __future__ import annotations

import re
from collections import defaultdict

ARROWS = {"→", "⇌", "->", "=>", "<->", "<=>"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _is_condition_like(text: str) -> bool:
    t = _clean(text)
    if not t or len(t) > 80:
        return False
    return bool(re.search(
        r"\d{1,4}\s*(?:-|–|—)?\s*\d{0,4}\s*(?:°\s*C|°C|o\s*C|K)"
        r"|(^|[\s,])(t|p|hv|hν|Δ|кат\.?|нагрев|электролиз|расплав|желатин|ацетон|SO2\s*ж|в\s+токе|CrO3|HNO3|F2|NaF|P4O10)([\s,()]|$)",
        t, re.I
    ))


def _words_to_lines(words):
    buckets = defaultdict(list)
    for w in words:
        # fitz word: x0,y0,x1,y1,text,block,line,word
        try:
            x0, y0, x1, y1, text = w[:5]
        except Exception:
            continue
        key = round(float(y0) / 4) * 4
        buckets[key].append((float(x0), float(y0), float(x1), float(y1), str(text)))
    lines = []
    for _, items in sorted(buckets.items()):
        items.sort(key=lambda x: x[0])
        text = _clean(" ".join(i[4] for i in items))
        if text:
            lines.append({
                "text": text,
                "x0": min(i[0] for i in items),
                "x1": max(i[2] for i in items),
                "y0": min(i[1] for i in items),
                "y1": max(i[3] for i in items),
                "items": items,
            })
    return lines


def _has_arrow(text: str) -> bool:
    return any(a in text for a in ARROWS) or "→" in text or "⇌" in text


def _arrow_x(line) -> float:
    items = line.get("items") or []
    for x0, _y0, x1, _y1, txt in items:
        if _has_arrow(txt):
            return (x0 + x1) / 2
    return (line["x0"] + line["x1"]) / 2


def _inject_visual_arrow_conditions(lines):
    """Add synthetic A -> condition -> B lines for conditions printed above arrow.

    PyMuPDF plain text often separates superscript/over-arrow conditions from the equation.
    This keeps the original text and adds an extra normalized line that extractor can parse.
    """
    out = [l["text"] for l in lines]
    for i, line in enumerate(lines):
        text = line["text"]
        if not _has_arrow(text):
            continue
        arrow = "⇌" if ("⇌" in text or "<->" in text or "<=>" in text) else "→"
        if arrow not in text:
            text2 = text.replace("->", "→").replace("=>", "→").replace("<->", "⇌").replace("<=>", "⇌")
        else:
            text2 = text
        if arrow not in text2:
            continue
        parts = text2.split(arrow, 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            continue
        ax = _arrow_x(line)
        candidates = []
        for prev in lines[max(0, i - 3):i]:
            ptxt = prev["text"]
            if _has_arrow(ptxt) or not _is_condition_like(ptxt):
                continue
            center = (prev["x0"] + prev["x1"]) / 2
            # Allow wider tolerance because conditions are often centered over a short arrow.
            if abs(center - ax) <= max(120, (line["x1"] - line["x0"]) * 0.35):
                candidates.append(ptxt)
        if candidates:
            cond = ", ".join(dict.fromkeys(candidates))
            out.append(f"{parts[0].strip()} {arrow} {cond} {arrow} {parts[1].strip()}")
    return out


def build_hybrid_page_text(page) -> str:
    try:
        plain = page.get_text("text") or ""
    except Exception:
        plain = ""
    try:
        words = page.get_text("words") or []
        lines = _words_to_lines(words)
        visual_lines = _inject_visual_arrow_conditions(lines)
        joined_visual = "\n".join(visual_lines)
        if joined_visual:
            return plain + "\n" + joined_visual
    except Exception:
        pass
    return plain
