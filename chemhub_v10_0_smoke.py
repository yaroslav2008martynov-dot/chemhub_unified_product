from app.extractor import extract_reactions_from_text, canonical_equation

cases = [
    ("hydride", "2M + H2 -> 2MH (M = Li, Na, K)"),
    ("ca_hydride", "H2^0 + Ca^0 -> Ca+2H2-1"),
    ("conditions1", "2Re2O7 -> t -> 2ReO2 + 3H2O"),
    ("conditions2", "CH2(COOH)2 -> 140 o C, P4O10 -> C3O2 + 2H2O"),
    ("conditions3", "2Tl + S -> 300 o C, в токе H2 -> Tl2S"),
    ("template_al_ga", "2M + 6H2O -> 2M(OH)3 + 3H2 (M = Al, Ga)"),
    ("bad_ion", "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)"),
]
for name, text in cases:
    rs = extract_reactions_from_text(text)
    print(name, [(r.equation, r.temperature, r.conditions, r.catalysts) for r in rs])
print("canonical", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
