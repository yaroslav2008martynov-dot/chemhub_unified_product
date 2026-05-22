import threading
from pathlib import Path
from typing import Any

import fitz
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.extractor import extract_reactions_from_text
from app.models import JobReaction, ProcessingJob

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _val(obj: Any, name: str, default: str = "") -> str:
    value = getattr(obj, name, default)
    if value is None:
        return default
    return str(value)


def _score(obj: Any, default: float = 0.9) -> float:
    try:
        return float(getattr(obj, "confidence_score", default) or default)
    except Exception:
        return default


def process_pdf_job(job_id: int, file_path: str, filename: str) -> None:
    threading.Thread(
        target=_process_pdf_job_sync,
        args=(job_id, file_path, filename),
        daemon=True,
    ).start()


def _process_pdf_job_sync(job_id: int, file_path: str, filename: str) -> None:
    db: Session = SessionLocal()
    seen_equations: set[str] = set()
    saved_total = 0
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return

        job.status = "processing"
        job.message = "Открываю PDF"
        job.processed_pages = 0
        job.progress_percent = 0
        db.commit()

        doc = fitz.open(file_path)
        total_pages = len(doc)
        job.total_pages = total_pages
        job.message = f"PDF открыт: {total_pages} страниц"
        db.commit()

        for page_index, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text") or ""
                found = extract_reactions_from_text(text)
            except Exception as page_exc:
                job.processed_pages = page_index
                job.progress_percent = int((page_index / max(total_pages, 1)) * 100)
                job.message = f"Страница {page_index}/{total_pages} пропущена: {page_exc}"
                db.commit()
                continue

            page_saved = 0
            for reaction in found:
                equation = _val(reaction, "equation").strip()
                if not equation:
                    continue
                key = equation.lower().replace(" ", "")
                if key in seen_equations:
                    continue
                seen_equations.add(key)

                db.add(
                    JobReaction(
                        job_id=job_id,
                        equation=equation,
                        reactants=_val(reaction, "reactants"),
                        products=_val(reaction, "products"),
                        conditions=_val(reaction, "conditions"),
                        catalysts=_val(reaction, "catalysts"),
                        solvents=_val(reaction, "solvents"),
                        temperature=_val(reaction, "temperature"),
                        pressure=_val(reaction, "pressure"),
                        states=_val(reaction, "states"),
                        source_pdf=filename,
                        source_page=page_index,
                        confidence_score=_score(reaction),
                        selected=True,
                    )
                )
                page_saved += 1
                saved_total += 1

            job.processed_pages = page_index
            job.progress_percent = int((page_index / max(total_pages, 1)) * 100)
            job.message = (
                f"Обработана страница {page_index}/{total_pages}. "
                f"Найдено на странице: {page_saved}. Всего: {saved_total}."
            )
            db.commit()

        job.status = "completed"
        job.progress_percent = 100
        job.message = f"Обработка завершена. Найдено реакций: {saved_total}."
        db.commit()
    except Exception as exc:
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.message = str(exc)
            db.commit()
    finally:
        db.close()
