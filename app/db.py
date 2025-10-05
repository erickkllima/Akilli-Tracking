# app/db.py
import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

if DATABASE_URL:
    # Normaliza para o driver moderno "psycopg" (evita cair em psycopg2)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # fallback local (SQLite)
    engine = create_engine("sqlite:///./monitorx.db", connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
