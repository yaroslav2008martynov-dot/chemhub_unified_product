import threading
import time
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import canonical_equation, extract_reactions_from_text
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
    eq = d.get("equation", "") or ""
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else ("≠" if "≠" in eq else ""))
    if arrow:
        left, right = eq.split(arrow, 1)
    else:
        left, right = "", ""
    r.equation = eq
    r.reactants = left.strip()
    r.products = right.strip()
    r.conditions = d.get("conditions", "") or ""
    r.catalysts = d.get("catalysts", "") or ""
    r.solvents = d.get("solvents", "") or ""
    r.temperature = d.get("temperature", "") or ""
    r.pressure = d.get("pressure", "") or ""
    r.states = d.get("states", "") or ""
    r.reaction_name = d.get("reaction_name", "") or ""
    r.review_reason = d.get("review_reason", "") or ""
    r.confidence_score = float(d.get("confidence_score", 0.9) or 0.9)
    return r


def _reaction_score(r) -> int:
    return sum(len(str(getattr(r, f, "") or "")) for f in ["conditions", "temperature", "catalysts", "solvents", "pressure", "reaction_name", "equation"])


def _dedup_existing_job_reactions(db: Session, job_id: int) -> set[str]:
    keys: dict[str, JobReaction] = {}
    for jr in db.query(JobReaction).filter(JobReaction.job_id == job_id).all():
        key = canonical_equation(jr.equation or "")
        if not key:
            continue
        old = keys.get(key)
        if old is None:
            keys[key] = jr
            continue
        old_score = sum(len(str(getattr(old, f, "") or "")) for f in ["conditions", "temperature", "catalysts", "solvents", "pressure", "reaction_name", "equation"])
        new_score = sum(len(str(getattr(jr, f, "") or "")) for f in ["conditions", "temperature", "catalysts", "solvents", "pressure", "reaction_name", "equation"])
        if new_score > old_score:
            old.selected = False
            keys[key] = jr
        else:
            jr.selected = False
    db.commit()
    return set(keys.keys())


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

        seen = _dedup_existing_job_reactions(db, job_id)
        use_vision = extract_page_reactions is not None

        for page_index, page in enumerate(doc, start=1):
            text = build_hybrid_page_text(page)
            found = []

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

            # Page-level dedup: keep only best version.
            page_best = {}
            for reaction in found:
                key = canonical_equation(getattr(reaction, "equation", ""))
                if not key:
                    continue
                if key not in page_best or _reaction_score(reaction) > _reaction_score(page_best[key]):
                    page_best[key] = reaction

            for key, reaction in page_best.items():
                if key in seen:
                    continue
                seen.add(key)
                db.add(JobReaction(
                    job_id=job_id,
                    reaction_name=getattr(reaction, "reaction_name", ""),
                    equation=reaction.equation,
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
                    review_reason=getattr(reaction, "review_reason", "") or "",
                ))

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
