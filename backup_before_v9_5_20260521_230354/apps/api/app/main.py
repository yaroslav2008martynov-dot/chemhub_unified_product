from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db, init_db, SessionLocal
from app.extractor import canonical_equation, extract_reactions_from_text
from app.chemistry_tools import reaction_search_score, is_probably_impossible, upsert_best_reaction
from app.models import Advertisement, JobReaction, ParserFeedback, ProcessingJob, Reaction
from app.processor import UPLOAD_DIR, process_pdf_job
from app.seed import seed_reactions
from app.seo import extract_id_from_slug, reaction_slug, render_reaction_html, related_reactions, robots_txt, sitemap_xml
from app.schemas import (
    AdminLoginIn, AdminLoginOut, AdvertisementIn, AdvertisementOut, FeedbackIn,
    JobOut, JobReactionIn, JobReactionOut, ReactionIn, ReactionOut,
)

app = FastAPI(title="ChemHub Unified API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def require_admin(x_admin_token: Annotated[str | None, Header()] = None):
    if x_admin_token != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Admin access required")


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        seed_reactions(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sitemap.xml")
def root_sitemap(db: Session = Depends(get_db)):
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    return Response(content=sitemap_xml(reactions, settings.PUBLIC_BASE_URL), media_type="application/xml")


@app.get("/robots.txt")
def root_robots():
    return Response(content=robots_txt(), media_type="text/plain")


@app.get("/seo/sitemap.xml")
def seo_sitemap(db: Session = Depends(get_db)):
    return root_sitemap(db)


@app.get("/seo/robots.txt")
def seo_robots():
    return root_robots()


@app.get("/seo/reactions")
def seo_reaction_index(db: Session = Depends(get_db)):
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    return [{"id": r.id, "slug": reaction_slug(r), "url": f"/reaction/{reaction_slug(r)}", "title": r.reaction_name or r.equation} for r in reactions]


@app.get("/seo/reaction/{slug}/html", response_class=HTMLResponse)
def seo_reaction_page(slug: str, db: Session = Depends(get_db)):
    rid = extract_id_from_slug(slug)
    reaction = db.get(Reaction, rid) if rid else None
    if not reaction or reaction.hidden or not reaction.approved:
        raise HTTPException(status_code=404, detail="Reaction page not found")
    candidates = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.desc()).limit(500).all()
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
    db.add(job); db.commit(); db.refresh(job)
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
    data = payload.model_dump()
    data["canonical_equation"] = canonical_equation(data["equation"])
    for key, value in data.items():
        setattr(reaction, key, value)
    db.commit(); db.refresh(reaction)
    return reaction


@app.post("/agent/feedback")
def create_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    db.add(ParserFeedback(**payload.model_dump()))
    db.commit()
    return {"saved": True, "message": "Замечание сохранено."}


@app.post("/agent/publish")
def publish_reactions(reaction_ids: list[int], db: Session = Depends(get_db)):
    published = 0; updated = 0; kept = 0
    for reaction_id in reaction_ids:
        jr = db.get(JobReaction, reaction_id)
        if not jr or jr.published or not jr.selected:
            continue
        data = dict(
            reaction_name=jr.reaction_name, equation=jr.equation, canonical_equation=canonical_equation(jr.equation),
            reactants=jr.reactants, products=jr.products, conditions=jr.conditions, catalysts=jr.catalysts,
            solvents=jr.solvents, temperature=jr.temperature, pressure=jr.pressure, states=jr.states,
            source_pdf=jr.source_pdf, source_page=jr.source_page, confidence_score=jr.confidence_score,
            impossible_note=is_probably_impossible(jr.equation), reaction_kind="agent", approved=True,
            hidden=False, origin="agent",
        )
        _, status = upsert_best_reaction(db, Reaction, data)
        jr.published = True
        if status == "created": published += 1
        elif status == "updated_more_detailed": updated += 1
        else: kept += 1
    db.commit(); export_site_files(db)
    return {"created": published, "updated_more_detailed": updated, "kept_existing_more_detailed": kept}


@app.get("/reactions", response_model=list[ReactionOut])
def list_reactions(q: str = "", include_hidden: bool = False, db: Session = Depends(get_db)):
    query = db.query(Reaction)
    if not include_hidden:
        query = query.filter(Reaction.approved.is_(True), Reaction.hidden.is_(False))
    q_clean = q.strip()
    if q_clean:
        if "/reaction/" in q_clean or q_clean.startswith("reaction/"):
            slug = q_clean.split("/reaction/")[-1].replace("reaction/", "")
            rid = extract_id_from_slug(slug)
            if rid:
                return query.filter(Reaction.id == rid).all()
        all_rows = query.order_by(Reaction.id.desc()).limit(1000).all()
        scored = [(reaction_search_score(r, q_clean), r) for r in all_rows]
        scored = [(s, r) for s, r in scored if s > 0]
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored:
            return [r for _, r in scored[:100]]
        like = f"%{q_clean}%"
        query = query.filter(or_(Reaction.equation.ilike(like), Reaction.reactants.ilike(like), Reaction.products.ilike(like), Reaction.reaction_name.ilike(like), Reaction.conditions.ilike(like), Reaction.catalysts.ilike(like), Reaction.solvents.ilike(like), Reaction.temperature.ilike(like)))
    else:
        if not include_hidden:
            return []
    return query.order_by(Reaction.id.desc()).limit(500).all()


@app.get("/reactions/{reaction_id}", response_model=ReactionOut)
def get_reaction(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    return reaction


@app.get("/reactions/{reaction_id}/related", response_model=list[ReactionOut])
def get_related(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    candidates = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.desc()).limit(500).all()
    return related_reactions(reaction, candidates)


@app.get("/elements/{symbol}/reactions", response_model=list[ReactionOut])
def get_element_reactions(symbol: str, db: Session = Depends(get_db)):
    like = f"%{symbol}%"
    return db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False), Reaction.equation.ilike(like)).order_by(Reaction.id.desc()).limit(200).all()


@app.post("/validate/impossible")
def validate_impossible(equation: str):
    note = is_probably_impossible(equation)
    return {"possible": not bool(note), "note": note}


@app.post("/admin/reactions", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def create_reaction(payload: ReactionIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["canonical_equation"] = canonical_equation(data["equation"])
    data["impossible_note"] = is_probably_impossible(data["equation"])
    data["reaction_kind"] = "manual"
    data["origin"] = "manual"
    reaction, _ = upsert_best_reaction(db, Reaction, data)
    export_site_files(db)
    return reaction


@app.put("/admin/reactions/{reaction_id}", response_model=ReactionOut, dependencies=[Depends(require_admin)])
def update_reaction(reaction_id: int, payload: ReactionIn, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    data = payload.model_dump(); data["canonical_equation"] = canonical_equation(data["equation"])
    for key, value in data.items(): setattr(reaction, key, value)
    db.commit(); db.refresh(reaction); export_site_files(db)
    return reaction


@app.delete("/admin/reactions/{reaction_id}", dependencies=[Depends(require_admin)])
def delete_reaction(reaction_id: int, db: Session = Depends(get_db)):
    reaction = db.get(Reaction, reaction_id)
    if not reaction: raise HTTPException(status_code=404, detail="Reaction not found")
    db.delete(reaction); db.commit(); export_site_files(db)
    return {"deleted": True}


@app.get("/admin/review", response_model=list[JobReactionOut], dependencies=[Depends(require_admin)])
def review_queue(db: Session = Depends(get_db)):
    return db.query(JobReaction).filter((JobReaction.selected.is_(False)) | (JobReaction.review_reason != "")).order_by(JobReaction.id.desc()).limit(300).all()


@app.get("/ads", response_model=list[AdvertisementOut])
def list_ads(placement: str = "", db: Session = Depends(get_db)):
    query = db.query(Advertisement).filter(Advertisement.active.is_(True))
    if placement: query = query.filter(Advertisement.placement == placement)
    return query.order_by(Advertisement.id.desc()).all()


@app.post("/admin/export", dependencies=[Depends(require_admin)])
def admin_export(db: Session = Depends(get_db)):
    return export_site_files(db)


def export_site_files(db: Session):
    import json
    export_dir = Path("exports"); export_dir.mkdir(exist_ok=True)
    reactions = db.query(Reaction).filter(Reaction.approved.is_(True), Reaction.hidden.is_(False)).order_by(Reaction.id.asc()).all()
    data = [{
        "id": r.id, "slug": reaction_slug(r), "url": f"/reaction/{reaction_slug(r)}",
        "reaction_name": r.reaction_name, "equation": r.equation, "reactants": r.reactants,
        "products": r.products, "conditions": r.conditions, "catalysts": r.catalysts,
        "solvents": r.solvents, "temperature": r.temperature, "pressure": r.pressure,
        "states": r.states, "confidence_score": r.confidence_score,
    } for r in reactions]
    (export_dir / "site-reactions.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (export_dir / "site-reactions.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in data), encoding="utf-8")
    return {"exported": len(data)}
