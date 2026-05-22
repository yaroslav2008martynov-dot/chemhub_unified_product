from app.extractor import extract_reactions_from_text

cases = {
    "alkali_hydrides": "2M + H2 -> 2MH M = Li, Na, K",
    "alkali_oxides": "M2O + H2O -> 2MOH M = Li, Na, K",
    "halide_product": "2K + Cl2 -> 2KX X = Cl",
    "inline_condition": "CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O",
    "condition_above": "300 В°C, РІ С‚РѕРєРµ H2\n2Tl + S -> Tl2S",
    "no_condition": "2Na + 2H2O -> 2NaOH + H2",
    "bad_pka": "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)",
}

for name, text in cases.items():
    rows = [(r.equation, r.conditions, r.temperature) for r in extract_reactions_from_text(text)]
    print(name, rows)
    if name == "alkali_hydrides":
        assert ("2Li + H2 в†’ 2LiH", "", "") in rows
        assert ("2Na + H2 в†’ 2NaH", "", "") in rows
        assert not any("M" in x[0] or "=" in x[0] for x in rows)
    if name == "alkali_oxides":
        assert ("Li2O + H2O в†’ 2LiOH", "", "") in rows
        assert not any("M" in x[0] or "=" in x[0] for x in rows)
    if name == "halide_product":
        assert rows == [("2K + Cl2 в†’ 2KCl", "", "")]
    if name == "inline_condition":
        assert rows == [("CH2(COOH)2 в†’ C3O2 + 2H2O", "140 В°C, P4O10", "")]
    if name == "condition_above":
        assert rows == [("2Tl + S в†’ Tl2S", "300 В°C, РІ С‚РѕРєРµ H2", "")]
    if name == "no_condition":
        assert rows == [("2Na + 2H2O в†’ 2NaOH + H2", "", "")]
    if name == "bad_pka":
        assert rows == []

print("CHEMHUB_V10_6_SMOKE_OK")
