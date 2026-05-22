import threading
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import extract_reactions_from_text
from app.models import JobReaction, ProcessingJob

try:
    from app.local_hybrid_filter import build_hybrid_page_text
except Exception:  # pragma: no cover
    build_hybrid_page_text = None

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def process_pdf_job(job_id: int, file_path: str, filename: str) -> None:
    threading.Thread(target=_process_pdf_job_sync, args=(job_id, file_path, filename), daemon=True).start()


def _safe_jobreaction_kwargs(**kwargs):
    """Only pass columns that exist in the currently installed model.
    This keeps the patch backward compatible with older DB/model variants.
    """
    columns = set(JobReaction.__table__.columns.keys())
    return {k: v for k, v in kwargs.items() if k in columns}


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

        seen_equations: set[str] = set()
        for page_index, page in enumerate(doc, start=1):
            try:
                text = _page_text(page)
                found = extract_reactions_from_text(text)
                added = 0
                for reaction in found:
                    eq = (reaction.equation or "").strip()
                    if not eq or eq in seen_equations:
                        continue
                    seen_equations.add(eq)
                    db.add(JobReaction(**_safe_jobreaction_kwargs(
                        job_id=job_id,
                        reaction_name=getattr(reaction, "reaction_name", ""),
                        equation=eq,
                        canonical_equation=getattr(reaction, "canonical_equation", ""),
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
                        published=False,
                        review_reason="",
                    )))
                    added += 1
                job.processed_pages = page_index
                job.progress_percent = int((page_index / max(len(doc), 1)) * 100)
                job.message = f"Обработана страница {page_index}/{len(doc)} · найдено реакций: {len(seen_equations)}"
                db.commit()
            except Exception as page_exc:
                job.processed_pages = page_index
                job.progress_percent = int((page_index / max(len(doc), 1)) * 100)
                job.message = f"Ошибка на странице {page_index}: {page_exc}"
                db.commit()

        job.status = "completed"
        job.progress_percent = 100
        job.message = f"Processing completed · найдено реакций: {len(seen_equations)}"
        db.commit()
    except Exception as exc:
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.message = str(exc)
            db.commit()
    finally:
        db.close()
