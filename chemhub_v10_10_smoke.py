from app.extractor import extract_reactions_from_text, fix_ocr_formula
cases = [
    "2H20 + O2 -> 2H2+1O",
    "2H2^0 + O2 -> 2H2^+1O",
    "H20 + S -> H2+1S",
    "H20 + CuO -> Cu + H2O",
    "H20 + Ca -> Ca+2H2-1",
    "CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O",
    "2Tl + S -> 300 В°C, РІ С‚РѕРєРµ H2 -> Tl2S",
]
for c in cases:
    rs = extract_reactions_from_text(c)
    print("CASE:", c)
    print([(r.equation, r.conditions, r.temperature) for r in rs])
