from app.extractor import extract_reactions_from_text
cases = [
    ("2M + H2 -> 2MH M = Li, Na, K", ["2Li + H2 в†’ 2LiH", "2Na + H2 в†’ 2NaH", "2K + H2 в†’ 2KH"]),
    ("M2O + H2O -> 2MOH M = Li, Na, K", ["Li2O + H2O в†’ 2LiOH", "Na2O + H2O в†’ 2NaOH", "K2O + H2O в†’ 2KOH"]),
    ("CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O", ["CH2(COOH)2 в†’ C3O2 + 2H2O"]),
]
for text, expected in cases:
    rows = extract_reactions_from_text(text)
    equations = [r.equation for r in rows]
    print(text, "=>", [(r.equation, r.conditions, r.temperature) for r in rows])
    for e in expected:
        assert e in equations, (text, e, equations)
    assert not any(" = " in e for e in equations), equations
    assert not any("M" in e or "X" in e or "Hal" in e for e in equations), equations
rows = extract_reactions_from_text("CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O")
assert rows and ("P4O10" in rows[0].conditions or "P4O10" in rows[0].catalysts), [(r.conditions, r.catalysts) for r in rows]
print("SMOKE_OK")
