# app/db.py
from __future__ import annotations
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) else default

def build_database_url_from_parts() -> str:
    host = _env("DB_HOST", "")
    port = _env("DB_PORT", "5432")
    db   = _env("DB_NAME", "postgres")
    user = _env("DB_USER", "")
    pwd  = _env("DB_PASSWORD", "")

    # hostaddr força IPv4 se fornecido (o psycopg usa hostaddr no handshake)
    hostaddr = _env("DB_HOSTADDR", None)

    base = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"
    params = [
        "sslmode=require",
        "connect_timeout=10",
        "application_name=render",
    ]
    # Se hostaddr vier, passamos na querystring (psycopg3 respeita libpq params)
    if hostaddr:
        params.append(f"hostaddr={hostaddr}")

    return base + "?" + "&".join(params)

# 1) Respeita DATABASE_URL se existir. 2) Senão, monta das partes.
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL").strip()
    _printed_url = DATABASE_URL
    # ofusca senha ao imprimir
    if "://" in _printed_url and "@" in _printed_url:
        try:
            scheme, rest = _printed_url.split("://", 1)
            creds, tail = rest.split("@", 1)
            if ":" in creds:
                user, _pw = creds.split(":", 1)
                _printed_url = f"{scheme}://{user}:***@{tail}"
        except Exception:
            pass
    print(f"[DB] Using DATABASE_URL: {_printed_url}")
else:
    DATABASE_URL = build_database_url_from_parts()
    # imprime URL sem senha
    safe = DATABASE_URL
    try:
        scheme, rest = safe.split("://", 1)
        creds, tail = rest.split("@", 1)
        if ":" in creds:
            user, _pw = creds.split(":", 1)
            safe = f"{scheme}://{user}:***@{tail}"
    except Exception:
        pass
    print(f"[DB] Using DATABASE_URL: {safe}")

# Ajustes pró-pooler / pró-ambiente serverless
CONNECT_ARGS = {
    # Já exigimos ssl via querystring, mas manter aqui não atrapalha
    "sslmode": "require",
    # Em pgBouncer (especialmente Transaction), prepared statements podem causar reset.
    # Em psycopg3 dá para desabilitar server-side prepare definindo 'prepare_threshold' como 0:
    "prepare_threshold": 0,
    # Opcional: evita cair em réplica acidentalmente (em alguns setups)
    "target_session_attrs": "read-write",
    # Exemplo de timeout por sessão (30s)
    # "options": "-c statement_timeout=30000",
}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reabre conexões quebradas
    pool_recycle=300,     # recicla conexões periodicamente
    pool_size=5,
    max_overflow=10,
    connect_args=CONNECT_ARGS,
)

def init_db() -> None:
    from app.models import SQLModel  # evita import circular
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)
