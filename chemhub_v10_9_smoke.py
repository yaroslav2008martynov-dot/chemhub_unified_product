from app.extractor import extract_reactions_from_text

tests = [
    ("oxidation", "H2^0 + S -> H2+1S", [("H2 + S в†’ H2S", "", "")]),
    ("visual_condition_separate", "300В° C, РІ С‚РѕРєРµ H2\n2Tl + S -> Tl2S", [("2Tl + S в†’ Tl2S", "300 В°C, РІ С‚РѕРєРµ H2", "300 В°C")]),
    ("visual_condition_inline", "2Tl + S -> 300В° C, РІ С‚РѕРєРµ H2 -> Tl2S", [("2Tl + S в†’ Tl2S", "300 В°C, РІ С‚РѕРєРµ H2", "300 В°C")]),
    ("no_condition", "2Tl + S -> Tl2S", [("2Tl + S в†’ Tl2S", "", "")]),
    ("concentration_inside", "HNO3 РєРѕРЅС†. + Cu -> Cu(NO3)2 + NO2", [("HNO3 РєРѕРЅС†. + Cu в†’ Cu(NO3)2 + NO2", "", "")]),
    ("p4o10_condition", "CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O", [("CH2(COOH)2 в†’ C3O2 + 2H2O", "140 В°C, P4O10", "140 В°C")]),
    ("template_x", "2K + Cl2 -> 2KX X = Cl", [("2K + Cl2 в†’ 2KCl", "", "")]),
    ("template_m", "M2O + H2O -> 2MOH M = Li, Na, K", [("Li2O + H2O в†’ 2LiOH", "", ""), ("Na2O + H2O в†’ 2NaOH", "", ""), ("K2O + H2O в†’ 2KOH", "", "")]),
    ("bad_constant", "SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0,6)", [("SnCl4 + 2HCl в†’ H2SnCl6", "", "")]),
    ("lg_noise", "(lg(B)=11,2)", []),
]

ok = True
for name, text, expected in tests:
    got = [(r.equation, r.conditions, r.temperature) for r in extract_reactions_from_text(text)]
    print(name, "=>", got)
    if got != expected:
        print("EXPECTED:", expected)
        ok = False
if not ok:
    raise SystemExit(1)
print("SMOKE_OK")
