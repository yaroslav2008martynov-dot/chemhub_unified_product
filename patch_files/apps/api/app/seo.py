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
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:90] or "reaction"

def reaction_slug(reaction: Reaction) -> str:
    base = reaction.reaction_name or reaction.equation or f"reaction-{reaction.id}"
    return f"{reaction.id}-{normalize_formula_for_slug(base)}"

def extract_id_from_slug(slug: str) -> int | None:
    m = re.match(r"^(\d+)-", slug or "")
    return int(m.group(1)) if m else None

def pretty_formula(text: str) -> str:
    s = html.escape(text or "")
    s = s.replace("-&gt;", "→").replace("=&gt;", "→").replace("&lt;-&gt;", "⇌")
    s = re.sub(r"\^([0-9]*[+\-])", r"<sup class='chem-sup'>\1</sup>", s)
    s = re.sub(r"(?<=[A-Za-zА-Яа-я\]\)])(\d+)", r"<sub class='chem-sub'>\1</sub>", s)
    s = s.replace("→", "<span class='chem-arrow'>→</span>").replace("⇌", "<span class='chem-arrow'>⇌</span>")
    return s

def conditions_text(reaction: Reaction) -> str:
    items = []
    for val in [reaction.temperature, reaction.pressure, reaction.catalysts, reaction.solvents, reaction.conditions, reaction.states]:
        if val and str(val).strip() and str(val).strip() not in items:
            items.append(str(val).strip())
    return "; ".join(items)

def reaction_title(reaction: Reaction) -> str:
    name = (reaction.reaction_name or "").strip()
    return f"{name}: уравнение и условия реакции" if name else f"Химическая реакция {reaction.equation[:80]}"

def reaction_description(reaction: Reaction) -> str:
    parts = []
    if reaction.reactants: parts.append(f"реагенты: {reaction.reactants}")
    if reaction.products: parts.append(f"продукты: {reaction.products}")
    cond = conditions_text(reaction)
    if cond: parts.append(f"условия: {cond}")
    if reaction.impossible_note: parts.append(reaction.impossible_note)
    return ("ChemHub: " + "; ".join(parts or [reaction.equation or "химическая реакция"]))[:300]

def related_reactions(current: Reaction, candidates: Iterable[Reaction], limit: int = 6) -> list[Reaction]:
    tokens = set(re.findall(r"[A-ZА-Я][a-zа-я]?\d*", " ".join([current.reactants or "", current.products or "", current.equation or ""])))
    scored = []
    for r in candidates:
        if r.id == current.id: continue
        blob = " ".join([r.reactants or "", r.products or "", r.equation or ""])
        score = sum(1 for t in tokens if t in blob)
        if score > 0: scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]

def json_ld(reaction: Reaction, slug: str) -> str:
    data = {"@context":"https://schema.org","@type":"ScholarlyArticle","headline":reaction_title(reaction),"description":reaction_description(reaction),"url":f"{BASE_URL}/reaction/{slug}","keywords":", ".join(filter(None,[reaction.equation,reaction.reactants,reaction.products,reaction.reaction_name,conditions_text(reaction)])),"isAccessibleForFree":True,"publisher":{"@type":"Organization","name":"ChemHub"}}
    return json.dumps(data, ensure_ascii=False)

def render_reaction_html(reaction: Reaction, related: list[Reaction]) -> str:
    slug = reaction_slug(reaction)
    title = reaction_title(reaction)
    cond = conditions_text(reaction)
    related_links = "".join(f"<li><a href='/reaction/{reaction_slug(r)}'>{html.escape(r.reaction_name or r.equation[:90])}</a></li>" for r in related) or "<li>Похожие реакции пока не найдены.</li>"
    if reaction.impossible_note or reaction.reaction_kind == "does_not_react":
        main = f"<div class='negative-reaction'><strong>{html.escape(reaction.reactants)}</strong> — {html.escape(reaction.impossible_note or 'не реагируют между собой')}.</div>"
    else:
        main = f"<div class='seo-conditions'>{html.escape(cond)}</div><div class='seo-equation'>{pretty_formula(reaction.equation)}</div>"
    return f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>{html.escape(title)}</title><meta name='description' content='{html.escape(reaction_description(reaction))}'><link rel='canonical' href='{BASE_URL}/reaction/{slug}'><script type='application/ld+json'>{json_ld(reaction, slug)}</script><style>body{{font-family:Arial,sans-serif;max-width:920px;margin:0 auto;padding:24px;line-height:1.5}}.seo-equation{{font-size:32px;text-align:center;margin:24px 0}}.seo-conditions{{text-align:center;font-size:16px;color:#42526e;min-height:22px}}.chem-sub{{font-size:.65em;vertical-align:sub;color:#2563eb}}.chem-sup{{font-size:.65em;vertical-align:super;color:#dc2626}}.chem-arrow{{display:inline-block;margin:0 .5em}}.ad{{border:1px dashed #bbb;padding:16px;text-align:center;color:#777;margin:24px 0}}</style></head><body><h1>{html.escape(title)}</h1><div class='ad'>Место для рекламы</div>{main}{f'<p><strong>{html.escape(reaction.reaction_name)}</strong></p>' if reaction.reaction_name else ''}<h2>Похожие реакции</h2><ul>{related_links}</ul><div class='ad'>Место для рекламы</div></body></html>"""

def sitemap_xml(reactions: Iterable[Reaction]) -> str:
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/reaction/{reaction_slug(r)}" for r in reactions]
    body = "\n".join(f"<url><loc>{html.escape(url)}</loc><changefreq>weekly</changefreq><priority>{'1.0' if url == BASE_URL + '/' else '0.8'}</priority></url>" for url in urls)
    return f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{body}</urlset>"

def robots_txt() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"
