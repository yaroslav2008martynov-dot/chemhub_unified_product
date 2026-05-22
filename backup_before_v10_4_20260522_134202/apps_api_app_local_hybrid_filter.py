def build_hybrid_page_text(page):
    """Safe local fallback: extract text from a PyMuPDF page.

    Kept as a tiny module so older processor imports remain compatible.
    """
    try:
        return page.get_text("text") or ""
    except Exception:
        return ""
