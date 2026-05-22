def build_hybrid_page_text(page):
    """Return page text in a layout-friendly order.

    PyMuPDF often keeps arrow labels as nearby text lines. We preserve line
    order so the extractor can treat a short condition line immediately before
    an equation as text above the arrow.
    """
    try:
        blocks = page.get_text("blocks") or []
        blocks = sorted(blocks, key=lambda b: (round(b[1] / 4), b[0]))
        lines = []
        for b in blocks:
            txt = str(b[4] or "").strip()
            if txt:
                lines.extend(x.strip() for x in txt.splitlines() if x.strip())
        return "\n".join(lines)
    except Exception:
        return page.get_text("text") or ""