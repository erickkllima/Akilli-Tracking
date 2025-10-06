# app/db.py (versão “minimalista” para não montar por partes)
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

DATABASE_URL = os.environ["DATABASE_URL"]  # falha cedo se estiver ausente
print(f"[DB] Using DATABASE_URL (sanitized): {DATABASE_URL.split('@')[0]}@***")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
