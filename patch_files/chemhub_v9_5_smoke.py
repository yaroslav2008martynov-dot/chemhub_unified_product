import sys
from app.extractor import extract_reactions_from_text, canonical_equation

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

cases = {
    'h2_oxidation': 'H20 + S -> H2+1S',
    'plus_keep': '4CuSO4+H3PO2+H2O -> 4CuH+H3PO4+H2SO4',
    'ionic_reject': 'H3BO3 + H2O -> H+ + [B(OH)4]- (pKa = 9,2)',
    'wrap': 'MgO + 2HCl -> MgCl2 +\n+ H2O',
    'condition': '2Tl + S -> 300 C, в токе H2 -> Tl2S',
    'complex_charge': 'S8 + 3AsF5 -> SO2 ж -> [S8^2+][AsF6-]2 + AsF3',
}
rs = extract_reactions_from_text(cases['h2_oxidation'])
assert_true(rs and rs[0].equation == 'H2 + S → H2S', 'H2 oxidation cleanup failed')
rs = extract_reactions_from_text(cases['plus_keep'])
assert_true(rs and '+' in rs[0].equation, 'plus signs lost')
assert_true(not extract_reactions_from_text(cases['ionic_reject']), 'ionic/pKa equation was not rejected')
rs = extract_reactions_from_text(cases['wrap'])
assert_true(rs and rs[0].equation == 'MgO + 2HCl → MgCl2 + H2O', 'line wrap merge failed')
rs = extract_reactions_from_text(cases['condition'])
assert_true(rs and rs[0].temperature == '300 °C' and 'в токе H2' in rs[0].conditions, 'conditions extraction failed')
rs = extract_reactions_from_text(cases['complex_charge'])
assert_true(rs and '[S8^2+]' in rs[0].equation, 'complex charge was lost')
assert_true(canonical_equation('A + B -> C + D') == canonical_equation('D + C -> B + A'), 'canonical duplicate matching failed')
print('CHEMHUB_V9_5_SMOKE_OK')

if '--cleanup' in sys.argv:
    from app.db import SessionLocal
    from app.models import Reaction
    db = SessionLocal()
    try:
        reactions = db.query(Reaction).all()
        for r in reactions:
            r.canonical_equation = canonical_equation(r.equation or '')
        db.commit()
        groups = {}
        for r in db.query(Reaction).all():
            groups.setdefault(r.canonical_equation or f'id:{r.id}', []).append(r)
        def score(r):
            return len(r.equation or '') + 8*bool(r.temperature) + 8*bool(r.conditions) + 8*bool(r.catalysts) + 8*bool(r.solvents) + 12*bool(r.reaction_name)
        hidden = 0
        for items in groups.values():
            if len(items) > 1:
                best = max(items, key=score)
                for r in items:
                    if r.id != best.id:
                        r.hidden = True
                        r.approved = False
                        hidden += 1
        db.commit()
        print(f'CHEMHUB_V9_5_DUPLICATES_HIDDEN={hidden}')
    finally:
        db.close()
