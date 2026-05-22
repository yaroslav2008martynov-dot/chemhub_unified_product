from __future__ import annotations

import threading
import time
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import canonical_equation, extract_reactions_from_text, fix_ocr_formula
from app.local_hybrid_filter import build_hybrid_page_text
from app.models import JobReaction, ProcessingJob

try:
    from app.vision_extractor import extract_page_reactions
except Exception:
    extract_page_reactions = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def process_pdf_job(job_id: int, file_path: str, filename: str) -> None:
    threading.Thread(target=_process_pdf_job_sync, args=(job_id, file_path, filename), daemon=True).start()


def _dict_to_reaction_obj(d: dict):
    class R:
        pass
    r = R()
    eq = fix_ocr_formula(d.get("equation", "") or "")
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else ("≠" if "≠" in eq else ""))
    if arrow and arrow in eq:
        left, right = eq.split(arrow, 1)
    else:
        left, right = "", ""
    r.reaction_name = d.get("reaction_name", "") or ""
    r.equation = eq
    r.reactants = left.strip()
    r.products = right.strip()
    r.conditions = d.get("conditions", "") or ""
    r.catalysts = d.get("catalysts", "") or ""
    r.solvents = d.get("solvents", "") or ""
    r.temperature = d.get("temperature", "") or ""
    r.pressure = d.get("pressure", "") or ""
    r.states = d.get("states", "") or ""
    r.confidence_score = float(d.get("confidence_score", 0.9) or 0.9)
    return r


def _reaction_quality(r) -> int:
    return sum(len(str(getattr(r, f, "") or "")) for f in [
        "equation", "conditions", "catalysts", "solvents", "temperature", "pressure", "states", "reaction_name"
    ])


def _existing_job_reactions(db: Session, job_id: int) -> dict[str, JobReaction]:
    out: dict[str, JobReaction] = {}
    for jr in db.query(JobReaction).filter(JobReaction.job_id == job_id).all():
        try:
            out[canonical_equation(jr.equation)] = jr
        except Exception:
            out[jr.equation] = jr
    return out


def _upsert_job_reaction(db: Session, job_id: int, reaction, filename: str, page_index: int) -> None:
    reaction.equation = fix_ocr_formula(reaction.equation)
    key = canonical_equation(reaction.equation)
    existing = _existing_job_reactions(db, job_id).get(key)
    if existing:
        if _reaction_quality(reaction) > _reaction_quality(existing):
            existing.reaction_name = getattr(reaction, "reaction_name", "") or existing.reaction_name
            existing.equation = reaction.equation
            existing.canonical_equation = key
            existing.reactants = reaction.reactants
            existing.products = reaction.products
            existing.conditions = reaction.conditions
            existing.catalysts = reaction.catalysts
            existing.solvents = reaction.solvents
            existing.temperature = reaction.temperature
            existing.pressure = reaction.pressure
            existing.states = reaction.states
            existing.source_pdf = filename
            existing.source_page = page_index
            existing.confidence_score = reaction.confidence_score
        return
    db.add(JobReaction(
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
    ))


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
            text = build_hybrid_page_text(page)
            found = []

            # Text extractor is always run because it preserves exact visual arrow labels from the page layout.
            text_found = extract_reactions_from_text(text)
            found.extend(text_found)

            if use_vision:
                try:
                    job.message = f"Vision extraction page {page_index}/{len(doc)}"
                    db.commit()
                    vision_items = extract_page_reactions(file_path, page_index - 1, context=text)
                    vision_found = [_dict_to_reaction_obj(x) for x in vision_items]
                    # Re-run extractor on vision equations to remove oxidation-state OCR artifacts.
                    normalized_vision = []
                    for vr in vision_found:
                        for rr in extract_reactions_from_text("\n".join([vr.conditions, vr.equation]).strip() or vr.equation):
                            rr.reaction_name = rr.reaction_name or vr.reaction_name
                            normalized_vision.append(rr)
                    found.extend(normalized_vision)
                    print(f"CHEMHUB_VISION_USED page={page_index} reactions={len(vision_found)}", flush=True)
                except Exception as exc:
                    print(f"CHEMHUB_VISION_FAILED page={page_index}: {exc}", flush=True)

            print(f"CHEMHUB_PAGE page={page_index} text_reactions={len(text_found)} total_candidates={len(found)}", flush=True)
            for reaction in found:
                _upsert_job_reaction(db, job_id, reaction, filename, page_index)

            job.processed_pages = page_index
            job.progress_percent = int((page_index / max(len(doc), 1)) * 100)
            job.message = f"Processed page {page_index}/{len(doc)}"
            db.commit()
            time.sleep(0.01)

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
