"""Database session & declarative base (SQLite for MVP, Postgres-ready)."""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Create tables and apply lightweight migrations for new columns."""
    import app.models.lead  # noqa: F401
    import app.models.sequence  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.workflow  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Add columns introduced after the initial schema (SQLite ALTER)."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        if "sequences" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("sequences")]
            if "ab_enabled" not in cols:
                conn.execute(text("ALTER TABLE sequences ADD COLUMN ab_enabled INTEGER DEFAULT 0"))
            if "variants" not in cols:
                conn.execute(text("ALTER TABLE sequences ADD COLUMN variants JSON"))
        if "sequence_enrollments" in inspector.get_table_names():
            ecols = [c["name"] for c in inspector.get_columns("sequence_enrollments")]
            if "variant" not in ecols:
                conn.execute(
                    text("ALTER TABLE sequence_enrollments ADD COLUMN variant VARCHAR(10) DEFAULT 'A'")
                )


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
