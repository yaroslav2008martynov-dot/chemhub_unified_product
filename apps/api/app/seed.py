from app.extractor import canonical_equation
from app.chemistry_tools import upsert_best_reaction, is_probably_impossible
from app.models import Reaction

SEED_REACTIONS = [
    dict(reaction_name="Получение водорода активным металлом", equation="2K + 2H2O → 2KOH + H2↑", reactants="2K + 2H2O", products="2KOH + H2↑"),
    dict(reaction_name="Электролиз воды", equation="2H2O → 2H2↑ + O2↑", reactants="2H2O", products="2H2↑ + O2↑", conditions="электролиз"),
    dict(reaction_name="Электролиз раствора NaCl", equation="2NaCl + 2H2O → H2↑ + Cl2↑ + 2NaOH", reactants="2NaCl + 2H2O", products="H2↑ + Cl2↑ + 2NaOH", conditions="электролиз"),
    dict(reaction_name="Конверсия метана; синтез-газ", equation="CH4 + H2O ⇌ CO + 3H2", reactants="CH4 + H2O", products="CO + 3H2", catalysts="Ni", temperature="1250 K"),
    dict(reaction_name="Синтез аммиака (процесс Габера-Боша)", equation="3H2 + N2 ⇌ 2NH3", reactants="3H2 + N2", products="2NH3", catalysts="Fe", conditions="нагревание", pressure="p"),
    dict(reaction_name="Железопаровой способ", equation="Fe + H2O → FeO + H2", reactants="Fe + H2O", products="FeO + H2", temperature="t > 570 °C"),
    dict(reaction_name="Железопаровой способ", equation="3Fe + 4H2O → Fe3O4 + 4H2", reactants="3Fe + 4H2O", products="Fe3O4 + 4H2", temperature="t < 570 °C"),
    dict(reaction_name="Алюминотермия", equation="8Al + 3Fe3O4 → 4Al2O3 + 9Fe", reactants="8Al + 3Fe3O4", products="4Al2O3 + 9Fe"),
    dict(reaction_name="Получение алюминия", equation="AlCl3 + 3K → Al + 3KCl", reactants="AlCl3 + 3K", products="Al + 3KCl", conditions="нагревание"),
    dict(reaction_name="Качественная реакция на хлорид-ион", equation="AgNO3 + NaCl → AgCl↓ + NaNO3", reactants="AgNO3 + NaCl", products="AgCl↓ + NaNO3"),
    dict(reaction_name="Получение гидроксида алюминия", equation="Na[Al(OH)4] + CO2 → Al(OH)3↓ + NaHCO3", reactants="Na[Al(OH)4] + CO2", products="Al(OH)3↓ + NaHCO3"),
    dict(reaction_name="Горение магния", equation="2Mg + O2 → 2MgO", reactants="2Mg + O2", products="2MgO"),
    dict(reaction_name="Получение хлора из оксида марганца(IV)", equation="MnO2 + 4HCl → MnCl2 + Cl2↑ + 2H2O", reactants="MnO2 + 4HCl", products="MnCl2 + Cl2↑ + 2H2O", conditions="нагревание"),
    dict(reaction_name="Разложение пероксида водорода", equation="2H2O2 → 2H2O + O2↑", reactants="2H2O2", products="2H2O + O2↑", catalysts="MnO2"),
]

def seed_reactions(db):
    if db.query(Reaction).count() > 0:
        return
    for item in SEED_REACTIONS:
        item = dict(item)
        item.setdefault("conditions", ""); item.setdefault("catalysts", ""); item.setdefault("solvents", "")
        item.setdefault("temperature", ""); item.setdefault("pressure", ""); item.setdefault("states", "")
        item["canonical_equation"] = canonical_equation(item["equation"])
        item["impossible_note"] = is_probably_impossible(item["equation"])
        item["reaction_kind"] = "seed"
        item["approved"] = True; item["hidden"] = False; item["origin"] = "seed"
        upsert_best_reaction(db, Reaction, item)
