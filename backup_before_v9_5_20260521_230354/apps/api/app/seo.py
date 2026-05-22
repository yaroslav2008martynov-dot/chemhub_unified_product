import html
import re
from urllib.parse import quote


def slugify(text: str) -> str:
    text = (text or "reaction").lower().replace("→", "-").replace("⇌", "-").replace("+", "-")
    text = re.sub(r"[^a-zа-я0-9]+", "-", text, flags=re.I).strip("-")
    return quote(text[:90] or "reaction")


def reaction_slug(r) -> str:
    return f"{r.id}-{slugify(r.reaction_name or r.equation)}"


def extract_id_from_slug(slug: str) -> int | None:
    m = re.match(r"(\d+)", slug or "")
    return int(m.group(1)) if m else None


def _render_equation(r) -> str:
    eq = html.escape(r.equation or "")
    conditions = ", ".join(x for x in [r.temperature, r.pressure, r.catalysts, r.solvents, r.conditions] if x)
    if "⇌" in eq:
        left, right = eq.split("⇌", 1); arrow = "⇌"
    elif "→" in eq:
        left, right = eq.split("→", 1); arrow = "→"
    else:
        return f"<div class='equation'>{eq}</div>"
    return f"""
    <div class='equation-wrap'>
      <span>{left.strip()}</span>
      <span class='arrow-box'><span class='arrow-cond'>{html.escape(conditions)}</span><span class='arrow'>{arrow}</span></span>
      <span>{right.strip()}</span>
    </div>"""


def related_reactions(reaction, candidates, limit=6):
    tokens = set(re.findall(r"[A-Z][a-z]?", reaction.equation or ""))
    scored = []
    for c in candidates:
        if c.id == reaction.id:
            continue
        ct = set(re.findall(r"[A-Z][a-z]?", c.equation or ""))
        score = len(tokens & ct)
        if reaction.catalysts and reaction.catalysts == c.catalysts:
            score += 1
        if reaction.conditions and reaction.conditions == c.conditions:
            score += 1
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def render_reaction_html(r, related):
    title = html.escape(r.reaction_name or r.equation)
    desc = html.escape(f"Уравнение реакции: {r.equation}. Условия: {', '.join(x for x in [r.temperature,r.catalysts,r.conditions] if x) or 'не указаны'}.")
    related_html = "".join(f"<li><a href='/reaction/{reaction_slug(x)}'>{html.escape(x.reaction_name or x.equation)}</a></li>" for x in related)
    schema = html.escape('{"@context":"https://schema.org","@type":"LearningResource","name":"' + (r.reaction_name or r.equation).replace('"','') + '"}')
    return f"""<!doctype html><html lang='ru'><head><meta charset='utf-8'/><title>{title} — ChemHub</title>
<meta name='description' content='{desc}'/><link rel='canonical' href='/reaction/{reaction_slug(r)}'/>
<meta property='og:title' content='{title}'/><meta property='og:description' content='{desc}'/>
<script type='application/ld+json'>{schema}</script>
<style>body{{font-family:Inter,Arial,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;color:#0f172a}}.card{{border:1px solid #e5e7eb;border-radius:24px;padding:28px;box-shadow:0 8px 24px #0001}}.equation-wrap{{display:flex;align-items:center;justify-content:center;gap:18px;font-size:30px;font-weight:750;flex-wrap:wrap}}.arrow-box{{display:inline-flex;flex-direction:column;align-items:center;min-width:110px}}.arrow-cond{{font-size:14px;min-height:20px;color:#2563eb}}.arrow{{font-size:40px;color:#0f172a}}a{{color:#2563eb}}</style>
</head><body><a href='/'>← ChemHub</a><h1>{title}</h1><div class='card'>{_render_equation(r)}</div>
<h2>Условия</h2><p>{html.escape(', '.join(x for x in [r.temperature, r.pressure, r.catalysts, r.solvents, r.conditions] if x) or 'Не указаны')}</p>
{('<h2>Название реакции</h2><p>'+html.escape(r.reaction_name)+'</p>') if r.reaction_name else ''}
<h2>Похожие реакции</h2><ul>{related_html}</ul></body></html>"""


def sitemap_xml(reactions, base_url="http://localhost:3000"):
    rows = ["<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"]
    rows.append(f"<url><loc>{base_url}/</loc></url>")
    rows.append(f"<url><loc>{base_url}/elements</loc></url>")
    for r in reactions:
        rows.append(f"<url><loc>{base_url}/reaction/{reaction_slug(r)}</loc></url>")
    rows.append("</urlset>")
    return "\n".join(rows)


def robots_txt():
    return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
