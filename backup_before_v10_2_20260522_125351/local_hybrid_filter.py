# ChemHub v10.0.1 compatibility module
# Restores the local hybrid filter API expected by processor.py.
# It is intentionally conservative: it never removes chemistry text by itself.
# The chemistry-aware extractor/validator remains responsible for filtering.

from __future__ import annotations

import re
from typing import Any

REACTION_HINT_RE = re.compile(
    r"(→|⇌|<->|<=>|->|=>|=|≠|электролиз|кат\.|катализ|t\s*(?:,|$)|°\s*C|o\s*C|\bK\b|H2|O2|Cl2|Na|K|Li|Ca|Mg|Al|Fe|Cu|HNO3|H2SO4)",
    re.IGNORECASE,
)

def _page_text(page: Any) -> str:
    try:
        return page.get_text("text") or ""
    except Exception:
        return ""

def _merge_broken_lines(text: str) -> str:
    """Merge common textbook line breaks, especially product continuations after '+'."""
    raw_lines = [re.sub(r"\s+", " ", x).strip() for x in str(text or "").splitlines()]
    lines = [x for x in raw_lines if x]
    out: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        # Merge: "BeSO4 +" + "+ H2O" or "MgCl2 +" + "+ H2O"
        while i + 1 < len(lines) and (cur.rstrip().endswith("+") or lines[i + 1].lstrip().startswith("+")):
            nxt = lines[i + 1].lstrip()
            if nxt.startswith("+"):
                nxt = nxt[1:].lstrip()
            cur = cur.rstrip("+ ").rstrip() + " + " + nxt
            i += 1
        out.append(cur)
        i += 1
    return "\n".join(out)

def build_hybrid_page_text(*args: Any, **kwargs: Any) -> str:
    """Return page text for extractor.

    Compatible call styles:
    - build_hybrid_page_text(page)
    - build_hybrid_page_text(page, text)
    - build_hybrid_page_text(text)
    - build_hybrid_page_text(page=..., text=...)

    This module must never crash API startup. If anything is unclear,
    it returns the safest available plain text.
    """
    page = kwargs.get("page")
    text = kwargs.get("text") or kwargs.get("fallback_text") or ""

    if args:
        first = args[0]
        if hasattr(first, "get_text"):
            page = first
            if len(args) > 1 and isinstance(args[1], str):
                text = args[1]
        elif isinstance(first, str):
            text = first

    if not text and page is not None:
        text = _page_text(page)

    text = _merge_broken_lines(text)

    # Do not aggressively drop lines here. Earlier versions lost conditions and plus signs.
    # Keep all lines with reaction hints, but if filtering would produce nothing, return original.
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    filtered = [x for x in lines if REACTION_HINT_RE.search(x)]
    if filtered:
        return "\n".join(filtered)
    return text
