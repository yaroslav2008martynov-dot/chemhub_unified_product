from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Reaction(Base):
    __tablename__ = "reactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reaction_name: Mapped[str] = mapped_column(String(255), default="")
    equation: Mapped[str] = mapped_column(Text, index=True)
    canonical_equation: Mapped[str] = mapped_column(Text, index=True, default="")
    reactants: Mapped[str] = mapped_column(Text, default="")
    products: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    catalysts: Mapped[str] = mapped_column(Text, default="")
    solvents: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[str] = mapped_column(String(255), default="")
    pressure: Mapped[str] = mapped_column(String(255), default="")
    states: Mapped[str] = mapped_column(String(255), default="")
    reaction_kind: Mapped[str] = mapped_column(String(255), default="")
    impossible_note: Mapped[str] = mapped_column(Text, default="")
    source_pdf: Mapped[str] = mapped_column(String(255), default="")
    source_page: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.9)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String(50), default="manual")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="queued")
    message: Mapped[str] = mapped_column(Text, default="")
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class JobReaction(Base):
    __tablename__ = "job_reactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("processing_jobs.id"), index=True)
    reaction_name: Mapped[str] = mapped_column(String(255), default="")
    equation: Mapped[str] = mapped_column(Text)
    canonical_equation: Mapped[str] = mapped_column(Text, default="")
    reactants: Mapped[str] = mapped_column(Text, default="")
    products: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    catalysts: Mapped[str] = mapped_column(Text, default="")
    solvents: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[str] = mapped_column(String(255), default="")
    pressure: Mapped[str] = mapped_column(String(255), default="")
    states: Mapped[str] = mapped_column(String(255), default="")
    source_pdf: Mapped[str] = mapped_column(String(255), default="")
    source_page: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.9)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[str] = mapped_column(Text, default="")
    internet_status: Mapped[str] = mapped_column(String(80), default="")
    internet_note: Mapped[str] = mapped_column(Text, default="")

class ParserFeedback(Base):
    __tablename__ = "parser_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_text: Mapped[str] = mapped_column(Text, default="")
    wrong_result: Mapped[str] = mapped_column(Text, default="")
    correct_result: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")

class Advertisement(Base):
    __tablename__ = "advertisements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    placement: Mapped[str] = mapped_column(String(80), default="main")
    title: Mapped[str] = mapped_column(String(255), default="")
    html: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
