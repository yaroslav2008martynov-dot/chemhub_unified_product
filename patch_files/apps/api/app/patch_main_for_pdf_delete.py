from pathlib import Path

p = Path("apps/api/app/main.py")
text = p.read_text(encoding="utf-8")

if "from pydantic import BaseModel" not in text:
    text = text.replace("from typing import Annotated\n", "from typing import Annotated\nfrom pydantic import BaseModel\n", 1)

if "class DeleteBySourcePdfIn" not in text:
    marker = 'app = FastAPI(title="ChemHub Unified API")'
    block = '''class DeleteBySourcePdfIn(BaseModel):
    source_pdf: str


'''
    if marker not in text:
        raise SystemExit("main.py marker not found: FastAPI title")
    text = text.replace(marker, block + marker, 1)

if '@app.get("/admin/source-pdfs"' not in text:
    marker = '\n\n@app.get("/ads", response_model=list[AdvertisementOut])'
    block = '''

@app.get("/admin/source-pdfs", dependencies=[Depends(require_admin)])
def admin_source_pdfs(db: Session = Depends(get_db)):
    rows = db.query(Reaction.source_pdf).filter(Reaction.source_pdf.isnot(None), Reaction.source_pdf != "").all()
    counts: dict[str, int] = {}
    for (name,) in rows:
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    return [{"source_pdf": name, "count": count} for name, count in sorted(counts.items(), key=lambda x: x[0].lower())]


@app.delete("/admin/reactions/by-source-pdf", dependencies=[Depends(require_admin)])
def delete_reactions_by_source_pdf(payload: DeleteBySourcePdfIn, db: Session = Depends(get_db)):
    source_pdf = (payload.source_pdf or "").strip()
    if not source_pdf:
        raise HTTPException(status_code=400, detail="source_pdf is required")
    rows = db.query(Reaction).filter(Reaction.source_pdf == source_pdf).all()
    deleted = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    export_site_files(db)
    return {"deleted": deleted, "source_pdf": source_pdf}
'''
    if marker not in text:
        raise SystemExit("main.py marker not found: /ads endpoint")
    text = text.replace(marker, block + marker, 1)

p.write_text(text, encoding="utf-8")
