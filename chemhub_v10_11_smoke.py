from app.extractor import extract_reactions_from_text
cases = [
    ("2H20 + O2 -> 2H2O", "2H2 + O2 в†’ 2H2O"),
    ("2H2^0 + O2^0 -> 2H2O", "2H2 + O2 в†’ 2H2O"),
    ("2H2O + O2 -> 2H2O", "2H2 + O2 в†’ 2H2O"),
    ("H2O + S -> H2S", "H2 + S в†’ H2S"),
    ("H2O + CuO -> Cu + H2O", "H2 + CuO в†’ Cu + H2O"),
    ("H2O + Ca -> CaH2", "H2 + Ca в†’ CaH2"),
    ("2K + Cl2 -> 2KX X = Cl", "2K + Cl2 в†’ 2KCl"),
]
for text, expected in cases:
    got = [r.equation for r in extract_reactions_from_text(text)]
    print(text, "=>", got)
    assert expected in got, (text, expected, got)
r = extract_reactions_from_text("300 В°C, РІ С‚РѕРєРµ H2\n2Tl + S -> Tl2S")[0]
print("condition test =>", r.equation, r.conditions)
assert r.equation == "2Tl + S в†’ Tl2S"
assert r.conditions == "300 В°C, РІ С‚РѕРєРµ H2"
r = extract_reactions_from_text("HNO3 РєРѕРЅС†. + Cu -> Cu(NO3)2 + NO2")[0]
assert r.conditions == "" and "РєРѕРЅС†." in r.equation
r = extract_reactions_from_text("SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0,6)")[0]
assert "pKa" not in r.equation and r.conditions == ""
print("CHEMHUB_V10_11_SMOKE_OK")
