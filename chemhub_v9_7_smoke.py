from app.extractor import extract_reactions_from_text, canonical_equation
cases = [
    ("ca_hydride", "H2^0 + Ca^0 -> Ca+2H2-1", "Ca + H2 -> CaH2"),
    ("li_hydride", "H2 + 2Li0 -> 2Li + 1H-1", "2Li + H2 -> 2LiH"),
    ("template", "Na[Al(OH)4] + CO2 -> Al(OH)3 + NaHCO3 (Al = Al, Ga, In)", "Na[Ga(OH)4]"),
    ("reject_pka", "H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)", ""),
    ("reject_electrode", "РєР°С‚РѕРґ: Mg2+ + 2e- -> Mg", ""),
    ("negative", "Bi + 4HNO3 РєРѕРЅС†. !=", ""),
    ("haber", "3H2^0 + N2 -> t,p,РєР°С‚.(Fe) -> 2NH3+1 (РЎРёРЅС‚РµР· Р°РјРјРёР°РєР° РїСЂРѕС†РµСЃСЃ Р“Р°Р±РµСЂР°-Р‘РѕС€Р°)", "3H2 + N2"),
    ("cluster", "S8 + 3AsF5 -> SO2 Р¶ -> [S8^2+][AsF6-]2 + AsF3", "[S8^2+]"),
    ("wrap", "BeO + H2SO4 -> BeSO4 +\n+ H2O", "BeSO4 + H2O"),
]
for name, text, expected in cases:
    rs = extract_reactions_from_text(text.replace('!=','в‰ '))
    joined = ' | '.join([r.equation + ' ' + r.conditions + ' ' + r.reaction_name for r in rs])
    print(name, joined)
    if expected and expected not in joined:
        raise SystemExit(f"FAILED {name}: expected {expected}, got {joined}")
    if not expected and joined:
        raise SystemExit(f"FAILED {name}: expected reject, got {joined}")
print("canonical", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
print("SMOKE_OK")
