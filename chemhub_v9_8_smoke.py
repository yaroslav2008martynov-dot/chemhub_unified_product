import sys
sys.path.insert(0, "/app")
from app.extractor import extract_reactions_from_text, canonical_equation
cases = {
 "hydride_ca": ("H2^0 + Ca^0 -> Ca+2H2-1", "CaH2"),
 "hydride_li": ("H2 + 2Li0 -> 2Li + 1H-1", "2LiH"),
 "haber": ("3H2^0 + N2 -> t, p, РєР°С‚. (Fe) -> 2NH3+1 (РЎРёРЅС‚РµР· Р°РјРјРёР°РєР° (РїСЂРѕС†РµСЃСЃ Р“Р°Р±РµСЂР°-Р‘РѕС€Р°))", "2NH3"),
 "pka_reject": ("H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)", ""),
 "complex_charge": ("S8 + 3AsF5 -> SO2 Р¶ -> [S8^2+][AsF6-]2 + AsF3", "[S8^2+]"),
 "template_al": ("Na[Al(OH)4] + CO2 -> Al(OH)3в†“ + NaHCO3 (Al -> Al, Ga, In)", "Na[Ga(OH)4]"),
}
for name, (text, expected) in cases.items():
    rs = extract_reactions_from_text(text)
    joined = " | ".join([r.equation + " " + r.conditions + " " + r.temperature + " " + r.reaction_name for r in rs])
    if expected and expected not in joined:
        raise SystemExit(f"SMOKE FAIL {name}: {joined}")
    if not expected and rs:
        raise SystemExit(f"SMOKE FAIL {name}: should reject, got {joined}")
print("CHEMHUB_V9_8_SMOKE_OK", canonical_equation("A + B -> C + D"), canonical_equation("D + C -> B + A"))
