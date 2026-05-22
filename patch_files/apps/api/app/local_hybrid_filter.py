from __future__ import annotations

import re


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def build_hybrid_page_text(page) -> str:
    """Build page text while preserving visual line order.

    PyMuPDF's plain get_text() can separate the label printed above an arrow from the
    reaction. This helper keeps close visual lines around reactions, so extractor can
    attach only the immediately adjacent condition line to the correct equation.
    """
    lines: list[tuple[float, float, str]] = []
    try:
        data = page.get_text("dict")
        for block in data.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = _clean("".join(span.get("text", "") for span in spans))
                if not text:
                    continue
                bbox = line.get("bbox") or [0, 0, 0, 0]
                lines.append((float(bbox[1]), float(bbox[0]), text))
    except Exception:
        pass

    if not lines:
        try:
            return page.get_text("text") or ""
        except Exception:
            return ""

    lines.sort(key=lambda x: (round(x[0] / 3) * 3, x[1]))
    out: list[str] = []
    for _, _, text in lines:
        if text and text not in out[-3:]:
            out.append(text)
    return "\n".join(out)
