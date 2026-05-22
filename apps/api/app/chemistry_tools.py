import re
from app.extractor import canonical_equation

COMMON_IMPOSSIBLE = [
    ("NaCl + Cu", "NaCl и Cu обычно не реагируют в водном растворе без специальных условий."),
    ("Cu + HCl", "Медь не вытесняет водород из HCl при обычных условиях."),
    ("Ag + HCl", "Серебро не вытесняет водород из HCl при обычных условиях."),
]

def detail_score(obj) -> int:
    fields = ["conditions", "catalysts", "solvents", "temperature", "pressure", "states", "reaction_name"]
    score = len(getattr(obj, "equation", "") or "")
    for f in fields:
        v = getattr(obj, f, "") or ""
        score += len(v) * 3
    return score


def semantic_tokens(text: str) -> set[str]:
    text = text or ""
    formulas = re.findall(r"[A-Z][a-z]?[A-Za-z0-9()\[\]·]*", text)
    words = re.findall(r"[А-Яа-яA-Za-z]{3,}", text.lower())
    aliases = {
        "электролиз": ["electrolysis", "электролиз", "ток"],
        "осадок": ["precipitate", "осадок", "выпадает"],
        "газ": ["gas", "газ", "выделяется"],
        "кислота": ["кислота", "acid"],
        "щелочь": ["щелочь", "alkali", "основание"],
        "окислитель": ["окислитель", "oxidizer"],
        "температура": ["нагрев", "temperature", "t"],
    }
    out = set(x.lower() for x in formulas + words)
    for key, vals in aliases.items():
        if any(v in text.lower() for v in vals):
            out.add(key)
    return out


def reaction_search_score(reaction, query: str) -> int:
    q = semantic_tokens(query)
    if not q:
        return 0
    hay = " ".join([
        reaction.equation or "", reaction.reactants or "", reaction.products or "",
        reaction.conditions or "", reaction.catalysts or "", reaction.solvents or "",
        reaction.temperature or "", reaction.pressure or "", reaction.reaction_name or "",
        reaction.reaction_kind or "",
    ])
    h = semantic_tokens(hay)
    score = len(q & h) * 10
    if query.lower() in hay.lower():
        score += 50
    return score


def is_probably_impossible(equation: str) -> str:
    normalized = canonical_equation(equation).replace("→", "+")
    for pattern, note in COMMON_IMPOSSIBLE:
        parts = [p.strip().lower() for p in pattern.split("+")]
        if all(p in normalized for p in parts):
            return note
    return ""


def upsert_best_reaction(db, ReactionModel, data: dict):
    canonical = data.get("canonical_equation") or canonical_equation(data.get("equation", ""))
    existing = db.query(ReactionModel).filter(ReactionModel.canonical_equation == canonical).first()
    if not existing:
        obj = ReactionModel(**data)
        db.add(obj); db.commit(); db.refresh(obj)
        return obj, "created"
    class Temp: pass
    temp = Temp()
    for k, v in data.items(): setattr(temp, k, v)
    if detail_score(temp) > detail_score(existing):
        for k, v in data.items():
            if k not in {"id", "created_at"}:
                setattr(existing, k, v)
        db.commit(); db.refresh(existing)
        return existing, "updated_more_detailed"
    return existing, "kept_existing_more_detailed"
