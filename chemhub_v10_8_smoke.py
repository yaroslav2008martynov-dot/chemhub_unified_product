from app.extractor import extract_reactions_from_text
tests = [
    ("no_condition", "2Tl + S -> Tl2S"),
    ("arrow_condition", "CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O"),
    ("any_arrow_condition", "A + B -> SO2 Р¶, -80 В°C -> C + D"),
    ("concentration_inside", "3Cu + 8HNO3 СЂР°Р·Р±. -> 3Cu(NO3)2 + 2NO + 4H2O"),
    ("template_m", "M2O + H2O -> 2MOH M = Li, Na, K"),
    ("template_x", "2K + Cl2 -> 2KX X = Cl"),
    ("bad_meta", "SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0.6)"),
]
for name, text in tests:
    rows = extract_reactions_from_text(text)
    print(name, [(r.equation, r.conditions) for r in rows])
assert extract_reactions_from_text("2Tl + S -> Tl2S")[0].conditions == ""
assert extract_reactions_from_text("CH2(COOH)2 -> 140 В°C, P4O10 -> C3O2 + 2H2O")[0].conditions == "140 В°C, P4O10"
assert "СЂР°Р·Р±." in extract_reactions_from_text("3Cu + 8HNO3 СЂР°Р·Р±. -> 3Cu(NO3)2 + 2NO + 4H2O")[0].equation
assert extract_reactions_from_text("3Cu + 8HNO3 СЂР°Р·Р±. -> 3Cu(NO3)2 + 2NO + 4H2O")[0].conditions == ""
assert not extract_reactions_from_text("SnCl4 + 2HCl -> H2SnCl6 (pKa1=-0.6)")
