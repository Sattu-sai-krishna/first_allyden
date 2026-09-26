import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


database_url = os.getenv("DATABASE_URL") or (
    f"sqlite:///{Path(__file__).resolve().with_name('attendance.db').as_posix()}"
)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine_options = {"pool_pre_ping": True}
if database_url.startswith("sqlite:"):
    engine_options["connect_args"] = {"check_same_thread": False}
elif database_url.startswith("postgresql+psycopg://"):
    engine_options["connect_args"] = {"prepare_threshold": None}

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
