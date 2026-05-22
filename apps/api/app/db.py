from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _ensure_column(table: str, column: str, ddl: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table):
        return
    existing = {c['name'] for c in inspector.get_columns(table)}
    if column not in existing:
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))

def _safe_sql(sql: str) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
    except Exception:
        pass

def init_db():
    import app.models  # noqa
    Base.metadata.create_all(bind=engine)
    for table in ['reactions', 'job_reactions']:
        _ensure_column(table, 'canonical_equation', "TEXT DEFAULT ''")
        _ensure_column(table, 'internet_status', "VARCHAR(100) DEFAULT 'not_checked'")
        _ensure_column(table, 'internet_note', "TEXT DEFAULT ''")
    _ensure_column('job_reactions', 'review_reason', "TEXT DEFAULT ''")
    _ensure_column('reactions', 'reaction_kind', "VARCHAR(100) DEFAULT ''")
    _ensure_column('reactions', 'impossible_note', "TEXT DEFAULT ''")
    _ensure_column('reactions', 'hidden', "BOOLEAN DEFAULT FALSE")
    _ensure_column('reactions', 'approved', "BOOLEAN DEFAULT TRUE")
    _ensure_column('reactions', 'origin', "VARCHAR(100) DEFAULT 'ai'")
    _ensure_column('reactions', 'updated_at', "TIMESTAMP DEFAULT NOW()")
    _safe_sql("ALTER TABLE reactions ALTER COLUMN created_at SET DEFAULT NOW()")
    _safe_sql("ALTER TABLE reactions ALTER COLUMN updated_at SET DEFAULT NOW()")
    _safe_sql("ALTER TABLE processing_jobs ALTER COLUMN created_at SET DEFAULT NOW()")
    _safe_sql("ALTER TABLE reactions ALTER COLUMN validation_status SET DEFAULT 'not_checked'")
    _safe_sql("UPDATE reactions SET canonical_equation = '' WHERE canonical_equation IS NULL")
    _safe_sql("UPDATE job_reactions SET canonical_equation = '' WHERE canonical_equation IS NULL")
