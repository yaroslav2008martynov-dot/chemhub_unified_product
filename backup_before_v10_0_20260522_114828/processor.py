
import threading
import time
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import canonical_equation, extract_reactions_from_text
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


def _dict_to_reaction_obj(d: dict):
    class R:
        pass

    r = R()
    eq = d.get("equation", "") or ""
    arrow = "⇌" if "⇌" in eq else ("→" if "→" in eq else "->")
    if arrow in eq:
        left, right = eq.split(arrow, 1)
    else:
        left, right = "", ""
    r.equation = eq
    r.reactants = left.strip()
    r.products = right.strip()
    r.conditions = d.get("conditions", "") or d.get("arrow_conditions", "")
    r.catalysts = d.get("catalysts", "")
    r.solvents = d.get("solvents", "")
    r.temperature = d.get("temperature", "")
    r.pressure = d.get("pressure", "")
    r.states = d.get("states", "")
    r.reaction_name = d.get("reaction_name", "") or d.get("name", "")
    r.confidence_score = float(d.get("confidence_score", 0.9) or 0.9)
    return r


def _page_text(page) -> str:
    if build_hybrid_page_text:
        try:
            return build_hybrid_page_text(page)
        except Exception:
            pass
    return page.get_text("text") or ""


def _has_column_safe(model_cls, attr: str) -> bool:
    return hasattr(model_cls, attr)


def _make_job_reaction(job_id: int, reaction, filename: str, page_index: int) -> JobReaction:
    payload = dict(
        job_id=job_id,
        reaction_name=getattr(reaction, "reaction_name", "") or "",
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
    )
    # Some user databases/models have these newer columns, some do not.
    if _has_column_safe(JobReaction, "canonical_equation"):
        payload["canonical_equation"] = canonical_equation(reaction.equation)
    if _has_column_safe(JobReaction, "review_reason"):
        payload["review_reason"] = ""
    return JobReaction(**payload)


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

        seen: set[str] = set()

        for page_index, page in enumerate(doc, start=1):
            text = _page_text(page)
            found = []

            if extract_page_reactions is not None:
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
                key = canonical_equation(reaction.equation)
                if not key or key in seen:
                    continue
                seen.add(key)
                db.add(_make_job_reaction(job_id, reaction, filename, page_index))

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
        print(f"CHEMHUB_PROCESSING_FAILED job={job_id}: {exc}", flush=True)
    finally:
        db.close()
