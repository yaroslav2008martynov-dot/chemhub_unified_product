import threading
import time
from pathlib import Path
import fitz
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.extractor import extract_reactions_from_text, canonical_equation
from app.models import JobReaction, ProcessingJob

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def process_pdf_job(job_id: int, file_path: str, filename: str) -> None:
    threading.Thread(target=_process_pdf_job_sync, args=(job_id, file_path, filename), daemon=True).start()


def _page_text_blocks(page) -> str:
    # Layout-preserving extraction: sorted blocks reduce condition/reaction mixing.
    blocks = page.get_text("blocks") or []
    blocks = sorted(blocks, key=lambda b: (round(b[1] / 8), b[0]))
    lines = []
    for b in blocks:
        txt = (b[4] or "").strip()
        if not txt:
            continue
        # Keep lines that likely contain chemistry context or arrows.
        if any(ch in txt for ch in ["→", "⇌", "->", "=>", "=", "↑", "↓"]) or any(w in txt.lower() for w in ["электролиз", "метод", "синтез", "кат", "нагрев", "конц", "разб"]):
            lines.append(txt)
    return "\n".join(lines)


def _process_pdf_job_sync(job_id: int, file_path: str, filename: str) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        job.status = "processing"; job.message = "Открываю PDF"; db.commit()
        doc = fitz.open(file_path)
        job.total_pages = len(doc); db.commit()
        for page_index, page in enumerate(doc, start=1):
            text = _page_text_blocks(page)
            found = extract_reactions_from_text(text)
            for reaction in found:
                selected = reaction.confidence_score >= 0.75 and not reaction.review_reason
                db.add(JobReaction(
                    job_id=job_id, reaction_name=reaction.reaction_name,
                    equation=reaction.equation, canonical_equation=canonical_equation(reaction.equation),
                    reactants=reaction.reactants, products=reaction.products,
                    conditions=reaction.conditions, catalysts=reaction.catalysts,
                    solvents=reaction.solvents, temperature=reaction.temperature,
                    pressure=reaction.pressure, states=reaction.states,
                    source_pdf=filename, source_page=page_index,
                    confidence_score=reaction.confidence_score, selected=selected,
                    review_reason=reaction.review_reason,
                ))
            job.processed_pages = page_index
            job.progress_percent = int((page_index / max(len(doc), 1)) * 100)
            job.message = f"Обработана страница {page_index}/{len(doc)}"
            db.commit()
            time.sleep(0.03)
        job.status = "completed"; job.progress_percent = 100; job.message = "Обработка завершена"; db.commit()
    except Exception as exc:
        job = db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"; job.message = str(exc); db.commit()
    finally:
        db.close()
