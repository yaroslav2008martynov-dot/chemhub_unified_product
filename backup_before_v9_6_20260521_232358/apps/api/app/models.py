from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Reaction(Base):
    __tablename__ = "reactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reaction_name: Mapped[str] = mapped_column(String(255), default="")
    equation: Mapped[str] = mapped_column(Text)
    canonical_equation: Mapped[str] = mapped_column(Text, default="", index=True)
    reactants: Mapped[str] = mapped_column(Text, default="")
    products: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    catalysts: Mapped[str] = mapped_column(Text, default="")
    solvents: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[str] = mapped_column(String(100), default="")
    pressure: Mapped[str] = mapped_column(String(100), default="")
    states: Mapped[str] = mapped_column(Text, default="")
    reaction_kind: Mapped[str] = mapped_column(String(100), default="")
    impossible_note: Mapped[str] = mapped_column(Text, default="")
    source_pdf: Mapped[str] = mapped_column(String(500), default="")
    source_page: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[str] = mapped_column(String(100), default="needs_review")
    internet_status: Mapped[str] = mapped_column(String(100), default="not_checked")
    internet_note: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    origin: Mapped[str] = mapped_column(String(100), default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(100), default="queued")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reactions: Mapped[list["JobReaction"]] = relationship(back_populates="job", cascade="all, delete-orphan")

class JobReaction(Base):
    __tablename__ = "job_reactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("processing_jobs.id"))
    reaction_name: Mapped[str] = mapped_column(String(255), default="")
    equation: Mapped[str] = mapped_column(Text)
    canonical_equation: Mapped[str] = mapped_column(Text, default="", index=True)
    reactants: Mapped[str] = mapped_column(Text, default="")
    products: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[str] = mapped_column(Text, default="")
    catalysts: Mapped[str] = mapped_column(Text, default="")
    solvents: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[str] = mapped_column(String(100), default="")
    pressure: Mapped[str] = mapped_column(String(100), default="")
    states: Mapped[str] = mapped_column(Text, default="")
    source_pdf: Mapped[str] = mapped_column(String(500), default="")
    source_page: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    internet_status: Mapped[str] = mapped_column(String(100), default="not_checked")
    internet_note: Mapped[str] = mapped_column(Text, default="")
    review_reason: Mapped[str] = mapped_column(Text, default="")
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped[ProcessingJob] = relationship(back_populates="reactions")

class ParserFeedback(Base):
    __tablename__ = "parser_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reaction_id: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str] = mapped_column(String(100), default="general")
    comment: Mapped[str] = mapped_column(Text, default="")
    before_text: Mapped[str] = mapped_column(Text, default="")
    after_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Advertisement(Base):
    __tablename__ = "advertisements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    placement: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    html: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
