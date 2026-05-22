from __future__ import annotations

import threading
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import ExtractedReaction, canonical_equation, extract_reactions_from_text
from app.models import JobReaction, ProcessingJob

try:
    from app.local_hybrid_filter import build_hybrid_page_text
except Exception:
    build_hybrid_page_text = None

try:
    from app.vision_extractor import extract_page_reactions
except Exception:
    extract_page_reactions = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def process_pdf_job(job_id: int, file_path: str, filename: str) -> None:
    threading.Thread(target=_process_pdf_job_sync, args=(job_id, file_path, filename), daemon=True).start()


def _dict_to_reaction_obj(d: dict) -> ExtractedReaction:
    eq = str(d.get("equation", "") or "")
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else "->")
    if arrow in eq:
        left, right = eq.split(arrow, 1)
    else:
        left, right = "", ""
    return ExtractedReaction(
        equation=eq,
        reactants=str(d.get("reactants") or left).strip(),
        products=str(d.get("products") or right).strip(),
        conditions=str(d.get("conditions", "") or ""),
        catalysts=str(d.get("catalysts", "") or ""),
        solvents=str(d.get("solvents", "") or ""),
        temperature=str(d.get("temperature", "") or ""),
        pressure=str(d.get("pressure", "") or ""),
        states=str(d.get("states", "") or ""),
        confidence_score=float(d.get("confidence_score", 0.9) or 0.9),
        reaction_name=str(d.get("reaction_name", "") or ""),
    )


def _score(r: ExtractedReaction) -> int:
    return len(r.equation or "") + 8 * bool(r.temperature) + 8 * bool(r.conditions) + 8 * bool(r.catalysts) + 8 * bool(r.solvents) + 12 * bool(r.reaction_name)


def _upsert_job_reaction(db: Session, job_id: int, reaction: ExtractedReaction, filename: str, page_index: int) -> None:
    key = canonical_equation(reaction.equation)
    existing = None
    try:
        existing = db.query(JobReaction).filter(JobReaction.job_id == job_id, JobReaction.canonical_equation == key).first()
    except Exception:
        existing = None
    payload = dict(
        job_id=job_id,
        reaction_name=getattr(reaction, "reaction_name", "") or "",
        equation=reaction.equation,
        canonical_equation=key,
        reactants=reaction.reactants,
        products=reaction.products,
        conditions=reaction.conditions,
        catalysts=reaction.catalysts,
        solvents=reaction.solvents,
        temperature=reaction.temperature,
        pressure=reaction.pressure,
        states=reaction.states,
        source_pdf=filename,
        source_page=page_index,
        confidence_score=reaction.confidence_score,
        selected=True,
    )
    if getattr(reaction, "validation_status", "") == "does_not_react":
        payload["review_reason"] = "does_not_react"
        payload["selected"] = False
    if existing:
        current_obj = ExtractedReaction(
            equation=existing.equation,
            reactants=existing.reactants,
            products=existing.products,
            conditions=existing.conditions,
            catalysts=existing.catalysts,
            solvents=existing.solvents,
            temperature=existing.temperature,
            pressure=existing.pressure,
            states=existing.states,
            confidence_score=existing.confidence_score,
            reaction_name=existing.reaction_name,
        )
        if _score(reaction) > _score(current_obj):
            for k, v in payload.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
        return
    db.add(JobReaction(**{k: v for k, v in payload.items() if k in JobReaction.__table__.columns.keys()}))


def _page_text(page) -> str:
    if build_hybrid_page_text is not None:
        try:
            return build_hybrid_page_text(page)
        except Exception:
            pass
    return page.get_text("text") or ""


def _process_pdf_job_sync(job_id: int, file_path: str, filename: str) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        job.status = "processing"
        job.message = "Opening PDF"
        db.commit()
        doc = fitz.open(file_path)
        job.total_pages = len(doc)
        db.commit()
        use_vision = extract_page_reactions is not None
        for page_index, page in enumerate(doc, start=1):
            text = _page_text(page)
            found: list[ExtractedReaction] = []
            if use_vision:
                try:
                    job.message = f"Vision extraction page {page_index}/{len(doc)}"
                    db.commit()
                    vision_items = extract_page_reactions(file_path, page_index - 1, context=text)
                    found = [_dict_to_reaction_obj(x) for x in vision_items]
                    print(f"CHEMHUB_VISION_USED page={page_index} reactions={len(found)}", flush=True)
                except Exception as exc:
                    print(f"CHEMHUB_VISION_FAILED page={page_index}: {exc}", flush=True)
                    found = []
            if not found:
                found = extract_reactions_from_text(text)
                print(f"CHEMHUB_TEXT_FALLBACK page={page_index} reactions={len(found)}", flush=True)
            for reaction in found:
                _upsert_job_reaction(db, job_id, reaction, filename, page_index)
            job.processed_pages = page_index
            job.progress_percent = int((page_index / max(len(doc), 1)) * 100)
            job.message = f"Обработана страница {page_index}/{len(doc)}"
            db.commit()
        job.status = "completed"
        job.progress_percent = 100
        job.message = "Processing completed"
        db.commit()
    except Exception as exc:
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.message = str(exc)
            db.commit()
    finally:
        db.close()
