from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, init_db
from app.extractor import canonical_equation, fix_ocr_formula
from app.models import Advertisement, JobReaction, ParserFeedback, ProcessingJob, Reaction
from app.processor import UPLOAD_DIR, process_pdf_job
from app.seo import extract_id_from_slug, reaction_slug, render_reaction_html, related_reactions, robots_txt, sitemap_xml
from app.schemas import (
    AdminLoginIn, AdminLoginOut, AdvertisementIn, AdvertisementOut, FeedbackIn, JobOut,
    JobReactionIn, JobReactionOut, ReactionIn, ReactionOut,
)

app = FastAPI(title="ChemHub Unified API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def require_admin(x_admin_token: Annotated[str | None, Header()] = None):
    if x_admin_token != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Admin access required")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/seo/sitemap.xml")
def seo_sitemap(db: Session = Depends(get_db)):
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    return Response(content=sitemap_xml(reactions), media_type="application/xml")


@app.get("/seo/robots.txt")
def seo_robots():
    return Response(content=robots_txt(), media_type="text/plain")


@app.get("/seo/reactions")
def seo_reaction_index(db: Session = Depends(get_db)):
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    return [{"id": r.id, "slug": reaction_slug(r), "title": r.reaction_name or r.equation} for r in reactions]


@app.get("/seo/reaction/{slug}/html", response_class=HTMLResponse)
def seo_reaction_page(slug: str, db: Session = Depends(get_db)):
    reaction_id = extract_id_from_slug(slug)
    reaction = db.get(Reaction, reaction_id) if reaction_id else None
    if not reaction or reaction.hidden or not reaction.approved:
        raise HTTPException(status_code=404, detail="Reaction page not found")
    candidates = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.desc()).limit(300).all()
    return HTMLResponse(content=render_reaction_html(reaction, related_reactions(reaction, candidates)))


@app.post("/admin/login", response_model=AdminLoginOut)
def admin_login(payload: AdminLoginIn):
    if payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    return AdminLoginOut(ok=True, token=settings.ADMIN_PASSWORD)


@app.post("/agent/upload", response_model=JobOut)
def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    data = file.file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is too large")
    safe_name = Path(file.filename).name
    job = ProcessingJob(filename=safe_name, status="queued", message="Файл принят в обработку")
    db.add(job)
    db.commit()
    db.refresh(job)
    target_path = UPLOAD_DIR / f"job-{job.id}-{safe_name}"
    target_path.write_bytes(data)
    process_pdf_job(job.id, str(target_path), safe_name)
    return job


@app.get("/agent/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/agent/jobs/{job_id}/reactions", response_model=list[JobReactionOut])
def get_job_reactions(job_id: int, db: Session = Depends(get_db)):
    return db.query(JobReaction).filter(JobReaction.job_id == job_id).order_by(JobReaction.id.asc()).all()


@app.put("/agent/job-reactions/{reaction_id}", response_model=JobReactionOut)
def update_job_reaction(reaction_id: int, payload: JobReactionIn, db: Session = Depends(get_db)):
    reaction = db.get(JobReaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    for key, value in payload.model_dump().items():
        setattr(reaction, key, value)
    reaction.canonical_equation = canonical_equation(reaction.equation)
    db.commit()
    db.refresh(reaction)
    return reaction


def _internet_check(equation: str) -> tuple[str, str]:
    cleaned = equation.replace("→", " ").replace("⇌", " ").replace("+", " ")
    query = f'"{cleaned}" chemical reaction'
    try:
        res = requests.get("https://duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": "ChemHubBot/0.1"}, timeout=8)
        if res.status_code != 200:
            return "internet_check_failed", f"Не удалось проверить интернет-источники: HTTP {res.status_code}"
        body = res.text.lower()
        tokens = [t.lower() for t in equation.replace("→", " ").replace("⇌", " ").replace("+", " ").split() if len(t) >= 2]
        hits = sum(1 for t in tokens[:8] if t in body)
        if hits >= max(2, min(4, len(tokens))):
            return "possible_online_analog", "Есть возможный аналог в интернете. Проверь источник вручную."
        return "no_online_evidence", "Нет сведений в интернете по автоматической проверке. Нужна ручная проверка."
    except Exception as exc:
        return "internet_check_failed", f"Проверка не выполнена: {exc}"


@app.post("/agent/job-reactions/{reaction_id}/internet-check", response_model=JobReactionOut)
def check_job_reaction_internet(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(JobReaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    status, note = _internet_check(reaction.equation)
    reaction.internet_status = status
    reaction.internet_note = note
    db.commit()
    db.refresh(reaction)
    return reaction


@app.post("/agent/feedback")
def create_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    fb = ParserFeedback(**payload.model_dump())
    db.add(fb)
    db.commit()
    return {"saved": True, "message": "Замечание сохранено. Оно будет использоваться как правило для ручной донастройки парсера."}


def _info_score(obj) -> int:
    return sum(len(str(getattr(obj, f, "") or "")) for f in [
        "reaction_name", "conditions", "catalysts", "solvents", "temperature", "pressure", "states", "equation"
    ])


def _copy_job_to_reaction(jr: JobReaction, existing: Reaction | None = None) -> Reaction:
    hidden = jr.internet_status == "does_not_react" or jr.review_reason == "does_not_react" or "≠" in (jr.equation or "")
    reaction = existing or Reaction()
    reaction.reaction_name = jr.reaction_name or reaction.reaction_name or ""
    reaction.equation = jr.equation
    reaction.canonical_equation = jr.canonical_equation or canonical_equation(jr.equation)
    reaction.reactants = jr.reactants
    reaction.products = jr.products
    reaction.conditions = jr.conditions
    reaction.catalysts = jr.catalysts
    reaction.solvents = jr.solvents
    reaction.temperature = jr.temperature
    reaction.pressure = jr.pressure
    reaction.states = jr.states
    reaction.source_pdf = jr.source_pdf
    reaction.source_page = jr.source_page
    reaction.confidence_score = jr.confidence_score
    reaction.internet_status = jr.internet_status
    reaction.internet_note = jr.internet_note
    reaction.validation_status = "does_not_react" if hidden else "approved_from_agent"
    reaction.reaction_kind = "does_not_react" if hidden else (reaction.reaction_kind or "")
    reaction.impossible_note = jr.internet_note or ("не реагируют между собой" if hidden else "")
    reaction.approved = True
    reaction.hidden = hidden
    reaction.origin = "agent"
    return reaction


@app.post("/agent/publish")
def publish_reactions(reaction_ids: list[int], db: Session = Depends(get_db)):
    published = 0
    for reaction_id in reaction_ids:
        jr = db.get(JobReaction, reaction_id)
        if not jr or jr.published:
            continue
        jr.canonical_equation = jr.canonical_equation or canonical_equation(jr.equation)
        existing = db.query(Reaction).filter(Reaction.canonical_equation == jr.canonical_equation).order_by(Reaction.id.asc()).first()
        if existing:
            candidate_score = _info_score(jr)
            existing_score = _info_score(existing)
            if candidate_score > existing_score:
                _copy_job_to_reaction(jr, existing)
        else:
            db.add(_copy_job_to_reaction(jr))
        jr.published = True
        published += 1
    db.commit()
    _cleanup_duplicates(db)
    export_site_files(db)
    return {"published": published}


def _loose_query(q: str) -> str:
    q = (q or "").lower()
    q = q.replace("0", "o").replace("а", "a").replace("о", "o").replace("н", "h").replace("с", "c")
    q = re.sub(r"[^a-zа-яё0-9]+", "", q)
    return q


def _reaction_blob(r: Reaction) -> str:
    return " ".join([r.equation or "", r.reactants or "", r.products or "", r.reaction_name or "", r.conditions or "", r.catalysts or "", r.solvents or "", r.temperature or "", r.pressure or "", r.impossible_note or ""])


@app.get("/reactions", response_model=list[ReactionOut])
def list_reactions(q: str = "", include_hidden: bool = False, db: Session = Depends(get_db)):
    q_clean = q.strip()
    query = db.query(Reaction)
    if not include_hidden:
        query = query.filter(Reaction.approved.is_(True), Reaction.hidden.is_(False))
    if q_clean:
        if "/reaction/" in q_clean or q_clean.startswith("reaction/"):
            slug = q_clean.split("/reaction/")[-1].replace("reaction/", "")
            rid = extract_id_from_slug(slug)
            if rid:
                query = query.filter(Reaction.id == rid)
        else:
            like = f"%{q_clean}%"
            query = query.filter(or_(
                Reaction.equation.ilike(like), Reaction.reactants.ilike(like), Reaction.products.ilike(like),
                Reaction.reaction_name.ilike(like), Reaction.conditions.ilike(like), Reaction.catalysts.ilike(like),
                Reaction.solvents.ilike(like), Reaction.temperature.ilike(like), Reaction.pressure.ilike(like),
                Reaction.states.ilike(like), Reaction.impossible_note.ilike(like),
            ))
    else:
        if not include_hidden:
            return []
    results = query.order_by(Reaction.id.desc()).limit(500).all()

    # Fuzzy fallback for typo queries like na0h+hl.
    if q_clean and not results:
        q_loose = _loose_query(fix_ocr_formula(q_clean))
        pool = db.query(Reaction).filter(Reaction.approved.is_(True)).order_by(Reaction.id.desc()).limit(1500).all()
        results = [r for r in pool if q_loose and q_loose in _loose_query(_reaction_blob(r))][:50]
        # Include negative hidden reactions only when user explicitly searches their reactants.
        if not results:
            results = [r for r in pool if r.hidden and any(tok.lower() in _reaction_blob(r).lower() for tok in q_clean.split())][:20]
    return results[:500]


@app.get("/reactions/{reaction_id}", response_model=ReactionOut)
def get_reaction(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return reaction


@app.post("/admin/reactions", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def create_reaction(payload: ReactionIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["canonical_equation"] = canonical_equation(data.get("equation", ""))
    reaction = Reaction(**data, origin="manual")
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    _cleanup_duplicates(db)
    export_site_files(db)
    return reaction


@app.put("/admin/reactions/{reaction_id}", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def update_reaction(reaction_id: int, payload: ReactionIn, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    for key, value in payload.model_dump().items():
        setattr(reaction, key, value)
    reaction.canonical_equation = canonical_equation(reaction.equation)
    db.commit()
    db.refresh(reaction)
    _cleanup_duplicates(db)
    export_site_files(db)
    return reaction


@app.delete("/admin/reactions/{reaction_id}", dependencies=[Depends(require_admin)])
def delete_reaction(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    db.delete(reaction)
    db.commit()
    export_site_files(db)
    return {"deleted": True}


@app.get("/ads", response_model=list[AdvertisementOut])
def list_ads(placement: str = "", db: Session = Depends(get_db)):
    query = db.query(Advertisement).filter(Advertisement.active.is_(True))
    if placement:
        query = query.filter(Advertisement.placement == placement)
    return query.order_by(Advertisement.id.desc()).all()


@app.get("/admin/ads", response_model=list[AdvertisementOut], dependencies=[Depends(require_admin)])
def admin_list_ads(db: Session = Depends(get_db)):
    return db.query(Advertisement).order_by(Advertisement.id.desc()).all()


@app.post("/admin/ads", response_model=AdvertisementOut, dependencies=[Depends(require_admin)])
def create_ad(payload: AdvertisementIn, db: Session = Depends(get_db)):
    ad = Advertisement(**payload.model_dump())
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@app.put("/admin/ads/{ad_id}", response_model=AdvertisementOut, dependencies=[Depends(require_admin)])
def update_ad(ad_id: int, payload: AdvertisementIn, db: Session = Depends(get_db)):
    ad = db.get(Advertisement, ad_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    for key, value in payload.model_dump().items():
        setattr(ad, key, value)
    db.commit()
    db.refresh(ad)
    return ad


@app.post("/admin/export", dependencies=[Depends(require_admin)])
def admin_export(db: Session = Depends(get_db)):
    return export_site_files(db)


def _cleanup_duplicates(db: Session) -> None:
    rows = db.query(Reaction).order_by(Reaction.id.asc()).all()
    best: dict[str, Reaction] = {}
    for r in rows:
        r.canonical_equation = r.canonical_equation or canonical_equation(r.equation)
        key = r.canonical_equation
        if not key:
            continue
        if key not in best:
            best[key] = r
            continue
        keep = best[key]
        if _info_score(r) > _info_score(keep):
            keep.hidden = True
            best[key] = r
        else:
            r.hidden = True
    db.commit()


def export_site_files(db: Session):
    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    data = [{
        "id": r.id,
        "slug": reaction_slug(r),
        "url": f"/reaction/{reaction_slug(r)}",
        "reaction_name": r.reaction_name,
        "equation": r.equation,
        "reactants": r.reactants,
        "products": r.products,
        "conditions": r.conditions,
        "catalysts": r.catalysts,
        "solvents": r.solvents,
        "temperature": r.temperature,
        "pressure": r.pressure,
        "states": r.states,
        "confidence_score": r.confidence_score,
    } for r in reactions]
    (export_dir / "site-reactions.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (export_dir / "site-reactions.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in data), encoding="utf-8")
    return {"exported": len(data)}
