
from app.extractor import extract_reactions_from_text, canonical_equation

def get(text):
    return [(r.equation, r.conditions, r.temperature, r.catalysts, r.reaction_name) for r in extract_reactions_from_text(text)]

tests = {
    "calcium_hydride": ("H2^0 + Ca^0 -> Ca+2H2-1", "H2 + Ca → CaH2"),
    "lithium_hydride": ("H2 + 2Li0 -> 2Li + 1H-1", "H2 + 2Li → 2LiH"),
    "haber": ("3H2^0 + N2 -> t,p,кат.(Fe) -> 2NH3+1", "3H2 + N2 → 2NH3"),
    "reject_pka": ("H3BO3 + H2O -> H + + [B(OH)4] - (pKa = 9,2)", None),
    "reject_cathode": ("катод: Mg2 + + 2ē -> Cl02)", None),
    "keep_complex_charge": ("S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3", "[S8^2+][AsF6-]2"),
    "template_expand": ("Na[Al(OH)4] + CO2 -> Al(OH)3↓ + NaHCO3 (Al -> Al, Ga, In)", "Na[Ga(OH)4]"),
    "negative_reaction": ("Bi + 4HNO3 конц. ≠", "≠"),
    "line_continuation": ("BeO + H2SO4 -> BeSO4 +\n+ H2O", "BeSO4 + H2O"),
    "no_lost_plus": ("4CuSO4+H3PO2+H2O -> 4CuH+H3PO4+H2SO4", "4CuSO4 + H3PO2 + H2O"),
    "drop_class_comment": ("K + O2 -> KO2 (надпероксид)", "K + O2 → KO2"),
    "polymer": ("nC2F4 -> t -> (-C2F4-)n (тефлон)", "(-C2F4-)n"),
    "reject_broken_copy": ("2H2O + O2 -> 2H2O", None),
}

for name, (text, expected) in tests.items():
    result = get(text)
    print(name, result)
    if expected is None:
        assert not result, f"{name}: expected no reactions, got {result}"
    else:
        flat = " | ".join(" ".join(map(str, item)) for item in result)
        assert expected in flat, f"{name}: expected {expected!r} in {flat!r}"

assert canonical_equation("A + B -> C + D") == canonical_equation("D + C -> B + A")
print("CHEMHUB_V9_9_SMOKE_OK")
