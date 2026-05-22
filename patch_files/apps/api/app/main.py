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
    AdminLoginIn,
    AdminLoginOut,
    AdvertisementIn,
    AdvertisementOut,
    FeedbackIn,
    JobOut,
    JobReactionIn,
    JobReactionOut,
    ReactionIn,
    ReactionOut,
)

app = FastAPI(title="ChemHub Unified API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"saved": True, "message": "Замечание сохранено."}


def _info_score(obj) -> int:
    return sum(len(str(getattr(obj, f, "") or "")) for f in ["conditions", "catalysts", "solvents", "temperature", "pressure", "states", "reaction_name"])


def _copy_reaction_fields(dst: Reaction, src: JobReaction):
    for f in ["reaction_name", "equation", "reactants", "products", "conditions", "catalysts", "solvents", "temperature", "pressure", "states", "source_pdf", "source_page", "confidence_score", "internet_status", "internet_note"]:
        if hasattr(dst, f) and hasattr(src, f):
            setattr(dst, f, getattr(src, f) or getattr(dst, f, ""))
    if hasattr(dst, "canonical_equation"):
        setattr(dst, "canonical_equation", canonical_equation(src.equation))


@app.post("/agent/publish")
def publish_reactions(reaction_ids: list[int], db: Session = Depends(get_db)):
    published = 0
    for reaction_id in reaction_ids:
        jr = db.get(JobReaction, reaction_id)
        if not jr or jr.published:
            continue
        key = canonical_equation(jr.equation)
        existing = None
        if hasattr(Reaction, "canonical_equation"):
            existing = db.query(Reaction).filter(getattr(Reaction, "canonical_equation") == key).first()
        if existing is None:
            existing = next((r for r in db.query(Reaction).order_by(Reaction.id.desc()).limit(500).all() if canonical_equation(r.equation) == key), None)
        is_negative = "≠" in (jr.equation or "")
        if existing:
            if _info_score(jr) > _info_score(existing):
                _copy_reaction_fields(existing, jr)
            existing.hidden = bool(is_negative or getattr(existing, "hidden", False))
            if is_negative and hasattr(existing, "impossible_note"):
                existing.impossible_note = "не реагируют между собой"
            if hasattr(existing, "validation_status") and is_negative:
                existing.validation_status = "does_not_react"
        else:
            data = dict(
                reaction_name=jr.reaction_name,
                equation=jr.equation,
                reactants=jr.reactants,
                products=jr.products,
                conditions=jr.conditions,
                catalysts=jr.catalysts,
                solvents=jr.solvents,
                temperature=jr.temperature,
                pressure=jr.pressure,
                states=jr.states,
                source_pdf=jr.source_pdf,
                source_page=jr.source_page,
                confidence_score=jr.confidence_score,
                internet_status=jr.internet_status,
                internet_note=jr.internet_note,
                validation_status="does_not_react" if is_negative else "approved_from_agent",
                approved=True,
                hidden=bool(is_negative),
                origin="agent",
            )
            reaction = Reaction(**data)
            if hasattr(reaction, "canonical_equation"):
                reaction.canonical_equation = key
            if is_negative and hasattr(reaction, "impossible_note"):
                reaction.impossible_note = "не реагируют между собой"
            db.add(reaction)
        jr.published = True
        published += 1
    db.commit()
    export_site_files(db)
    return {"published": published}


def _query_variants(q: str) -> list[str]:
    q = (q or "").strip()
    variants = {q, q.upper(), q.lower()}
    fixed = q.replace("0", "O").replace("l", "Cl").replace("L", "Cl")
    variants.add(fixed)
    try:
        variants.add(fix_ocr_formula(fixed))
    except Exception:
        pass
    compact = re.sub(r"\s+", "", fixed)
    variants.add(compact)
    return [v for v in variants if v]


@app.get("/reactions", response_model=list[ReactionOut])
def list_reactions(q: str = "", include_hidden: bool = False, db: Session = Depends(get_db)):
    query = db.query(Reaction)
    q_clean = q.strip()
    if q_clean:
        if "/reaction/" in q_clean or q_clean.startswith("reaction/"):
            slug = q_clean.split("/reaction/")[-1].replace("reaction/", "")
            rid = extract_id_from_slug(slug)
            if rid:
                query = query.filter(Reaction.id == rid)
            else:
                query = query.filter(Reaction.equation.ilike(f"%{q_clean}%"))
        else:
            clauses = []
            for variant in _query_variants(q_clean):
                like = f"%{variant}%"
                clauses.extend([
                    Reaction.equation.ilike(like), Reaction.reactants.ilike(like), Reaction.products.ilike(like),
                    Reaction.reaction_name.ilike(like), Reaction.conditions.ilike(like), Reaction.catalysts.ilike(like),
                    Reaction.solvents.ilike(like), Reaction.temperature.ilike(like), Reaction.pressure.ilike(like), Reaction.states.ilike(like),
                ])
            query = query.filter(or_(*clauses))
        # Hidden negative reactions can be returned only on explicit search.
        if not include_hidden:
            query = query.filter(Reaction.approved.is_(True))
    else:
        if not include_hidden:
            return []
    if not q_clean and not include_hidden:
        query = query.filter(Reaction.hidden.is_(False), Reaction.approved.is_(True))
    elif not include_hidden:
        query = query.filter(Reaction.approved.is_(True))
    return query.order_by(Reaction.hidden.asc(), Reaction.id.desc()).limit(500).all()


@app.get("/reactions/{reaction_id}", response_model=ReactionOut)
def get_reaction(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return reaction


@app.post("/admin/reactions", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def create_reaction(payload: ReactionIn, db: Session = Depends(get_db)):
    reaction = Reaction(**payload.model_dump(), origin="manual")
    if hasattr(reaction, "canonical_equation"):
        reaction.canonical_equation = canonical_equation(reaction.equation)
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    export_site_files(db)
    return reaction


@app.put("/admin/reactions/{reaction_id}", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def update_reaction(reaction_id: int, payload: ReactionIn, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    for key, value in payload.model_dump().items():
        setattr(reaction, key, value)
    if hasattr(reaction, "canonical_equation"):
        reaction.canonical_equation = canonical_equation(reaction.equation)
    db.commit()
    db.refresh(reaction)
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


def export_site_files(db: Session):
    import json
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
