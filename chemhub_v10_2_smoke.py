from app.extractor import extract_reactions_from_text, canonical_equation

cases = {
    "M hydrides": "2M + H2 -> 2MH (M = Li, Na, K)",
    "X chloride": "2K + Cl2 -> 2KX (X = Cl)",
    "Li oxidation": "H2 + 2Li0 -> 2Li + 1H-1",
    "Ca oxidation": "H2^0 + Ca^0 -> Ca+2H2-1",
    "conditions": "2Tl + S -> 300 В°C, РІ С‚РѕРєРµ H2 -> Tl2S",
    "pKa reject": "H3BO3 + H2O -> H + + [B(OH)4] - (pKa = 9,2)",
    "cathode reject": "РєР°С‚РѕРґ: Mg2+ + 2e- -> Mg",
}
for name, text in cases.items():
    rs = extract_reactions_from_text(text)
    print(name, "=>", [(r.equation, r.conditions, r.temperature, r.reaction_name) for r in rs])
