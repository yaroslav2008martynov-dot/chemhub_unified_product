from __future__ import annotations

import html
import json
import re
from typing import Iterable
from app.models import Reaction

BASE_URL = "http://localhost:3000"
TRANSLIT = {"а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"c","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"}
SUBS = str.maketrans({"₀":"0","₁":"1","₂":"2","₃":"3","₄":"4","₅":"5","₆":"6","₇":"7","₈":"8","₉":"9","⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9","⁺":"+","⁻":"-","−":"-","–":"-","—":"-","→":"-","⇌":"-"})

def normalize_formula_for_slug(value: str) -> str:
    value = (value or "").translate(SUBS).lower()
    value = "".join(TRANSLIT.get(ch, ch) for ch in value)
    value = value.replace("⇌", "-").replace("→", "-").replace("=", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")[:90] or "reaction"

def reaction_slug(reaction: Reaction) -> str:
    base = reaction.reaction_name or reaction.equation or f"reaction-{reaction.id}"
    return f"{reaction.id}-{normalize_formula_for_slug(base)}"

def extract_id_from_slug(slug: str) -> int | None:
    m = re.match(r"^(\d+)-", slug or "")
    return int(m.group(1)) if m else None

def pretty_formula(text: str) -> str:
    s = html.escape(text or "")
    s = s.replace("->", "→").replace("=>", "→").replace("<->", "⇌")
    s = re.sub(r"\^([0-9]*[+\-])", r"<sup class='charge'>\1</sup>", s)
    s = re.sub(r"(?<=[A-Za-zА-Яа-я\]\)])(\d+)", r"<sub class='idx'>\1</sub>", s)
    s = s.replace("↑", "<span class='gas'>↑</span>").replace("↓", "<span class='ppt'>↓</span>")
    return s

def conditions_text(reaction: Reaction) -> str:
    items = []
    for v in [reaction.temperature, reaction.pressure, reaction.catalysts, reaction.solvents, reaction.conditions, reaction.states]:
        if v and str(v).strip() and str(v).strip() not in items:
            items.append(str(v).strip())
    return ", ".join(items)

def reaction_title(reaction: Reaction) -> str:
    name = (reaction.reaction_name or "").strip()
    if name:
        return f"{name}: уравнение и условия реакции"
    return f"Химическая реакция {reaction.equation[:90]}"

def reaction_description(reaction: Reaction) -> str:
    parts = [reaction.equation or ""]
    cond = conditions_text(reaction)
    if cond:
        parts.append(f"условия: {cond}")
    if reaction.reaction_name:
        parts.append(reaction.reaction_name)
    return ("ChemHub — справочник химических реакций: " + "; ".join(parts))[:300]

def related_reactions(current: Reaction, candidates: Iterable[Reaction], limit: int = 6) -> list[Reaction]:
    tokens = set(re.findall(r"[A-ZА-Я][a-zа-я]?\d*", " ".join([current.reactants or "", current.products or "", current.equation or ""])))
    scored = []
    for r in candidates:
        if r.id == current.id:
            continue
        blob = " ".join([r.reactants or "", r.products or "", r.equation or ""])
        score = sum(1 for t in tokens if t in blob)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]

def json_ld(reaction: Reaction, slug: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": reaction_title(reaction),
        "description": reaction_description(reaction),
        "url": f"{BASE_URL}/reaction/{slug}",
        "about": [reaction.reactants, reaction.products, reaction.reaction_name],
        "keywords": ", ".join(filter(None, [reaction.equation, reaction.reactants, reaction.products, reaction.reaction_name, conditions_text(reaction)])),
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "ChemHub"},
    }
    return json.dumps(data, ensure_ascii=False)

def render_reaction_html(reaction: Reaction, related: list[Reaction]) -> str:
    slug = reaction_slug(reaction)
    title = reaction_title(reaction)
    desc = reaction_description(reaction)
    cond = conditions_text(reaction)
    related_links = "".join(f"<li><a href='/reaction/{reaction_slug(r)}'>{html.escape(r.reaction_name or r.equation[:90])}</a></li>" for r in related) or "<li>Похожие реакции пока не найдены.</li>"
    name_block = f"<p class='reaction-name'>Название реакции: {html.escape(reaction.reaction_name)}</p>" if reaction.reaction_name else ""
    no_reaction = "<p class='no-reaction'>Эти вещества не реагируют между собой.</p>" if reaction.validation_status == "does_not_react" or "≠" in (reaction.equation or "") else ""
    return f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'/><title>{html.escape(title)}</title><meta name='description' content='{html.escape(desc)}'/><link rel='canonical' href='{BASE_URL}/reaction/{slug}'/><script type='application/ld+json'>{json_ld(reaction, slug)}</script><style>body{{font-family:Arial,sans-serif;max-width:920px;margin:auto;padding:24px;background:#f6f8fc;color:#172033}}.card{{background:white;border-radius:22px;padding:24px;box-shadow:0 10px 28px #0001}}.eq{{font-size:30px;text-align:center;margin:26px 0}}.cond{{font-size:16px;color:#455;text-align:center;margin-bottom:-12px}}sub.idx{{color:#0f766e;font-weight:700}}sup.charge{{color:#b45309;font-weight:700}}.reaction-name{{font-size:14px;color:#475569;text-align:center}}.ad{{border:1px dashed #cbd5e1;border-radius:16px;padding:16px;text-align:center;color:#64748b;margin:20px 0}}a{{color:#1565c0}}</style></head><body><div class='card'><h1>{html.escape(title)}</h1><div class='ad'>Место для рекламы</div>{f"<div class='cond'>{html.escape(cond)}</div>" if cond else ""}<div class='eq'>{pretty_formula(reaction.equation)}</div>{name_block}{no_reaction}<h2>Реагенты</h2><p>{pretty_formula(reaction.reactants or '—')}</p><h2>Продукты</h2><p>{pretty_formula(reaction.products or '—')}</p><h2>Условия</h2><p>{html.escape(cond or 'Специальные условия не указаны.')}</p><h2>Похожие реакции</h2><ul>{related_links}</ul><div class='ad'>Место для рекламы</div><p>Создатель проекта: Telegram @brovler228. По рекламе и исправлениям: @brovler228</p></div></body></html>"""

def sitemap_xml(reactions: Iterable[Reaction]) -> str:
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/reaction/{reaction_slug(r)}" for r in reactions]
    body = "\n".join(f"<url><loc>{html.escape(url)}</loc><changefreq>weekly</changefreq><priority>{'1.0' if url == BASE_URL + '/' else '0.8'}</priority></url>" for url in urls)
    return f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{body}</urlset>"

def robots_txt() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"
