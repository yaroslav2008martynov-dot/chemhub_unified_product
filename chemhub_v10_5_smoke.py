from app.extractor import extract_reactions_from_text

cases = [
    ("2M + H2 -> 2MH (M = Li, Na, K)", ["2Li + H2 → 2LiH", "2Na + H2 → 2NaH", "2K + H2 → 2KH"]),
    ("M2O + H2O -> 2MOH (M = Li, Na, K)", ["Li2O + H2O → 2LiOH", "Na2O + H2O → 2NaOH", "K2O + H2O → 2KOH"]),
    ("2M + 2H2O -> 2MOH + H2 (M = Li, Na, K)", ["2Li + 2H2O → 2LiOH + H2", "2Na + 2H2O → 2NaOH + H2", "2K + 2H2O → 2KOH + H2"]),
    ("2K + Cl2 -> 2KX (X = Cl)", ["2K + Cl2 → 2KCl"]),
    ("140 °C, P4O10\nCH2(COOH)2 -> C3O2 + 2H2O", ["CH2(COOH)2 → C3O2 + 2H2O"]),
    ("2Tl + S -> 300 °C, в токе H2 -> Tl2S", ["2Tl + S → Tl2S"]),
    ("H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)", []),
    ("катод: Mg2+ + 2e- -> Mg", []),
]
for text, expected in cases:
    rows = extract_reactions_from_text(text)
    eqs = [r.equation for r in rows]
    print("CASE:", text)
    print("RESULT:", [(r.equation, r.conditions, r.temperature) for r in rows])
    if expected:
        for eq in expected:
            assert eq in eqs, f"Expected {eq}, got {eqs}"
    else:
        assert not rows, f"Expected reject, got {eqs}"
print("CHEMHUB_V10_5_SMOKE_OK")
