# app/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from urllib.parse import quote_plus

def _from_env_trim(key: str) -> str | None:
    v = os.getenv(key)
    if v is None: 
        return None
    v = v.strip()
    return v or None

def build_database_url() -> str:
    # Se o usuário deixou DATABASE_URL pronto e válido, use.
    raw = _from_env_trim("DATABASE_URL")
    if raw and raw.startswith(("postgresql://", "postgresql+psycopg://")):
        return raw

    host = _from_env_trim("DB_HOST") or ""
    # se colaram a connection string inteira por engano no DB_HOST, limpe
    if host.startswith("postgresql://"):
        host = host.split("@", 1)[-1]
        if "/" in host:
            host = host.split("/", 1)[0]
        if ":" in host:
            host = host.split(":", 1)[0]

    port = _from_env_trim("DB_PORT") or "6543"  # pooler
    name = _from_env_trim("DB_NAME") or "postgres"
    user = _from_env_trim("DB_USER") or ""
    pwd  = _from_env_trim("DB_PASSWORD") or ""
    hostaddr = _from_env_trim("DB_HOSTADDR")  # opcional, força IPv4

    # senha url-encoded
    pwd_q = quote_plus(pwd)

    params = [
        "sslmode=require",
        "connect_timeout=10",
        "application_name=render",
    ]
    if hostaddr:
        params.append(f"hostaddr={hostaddr}")

    query = "&".join(params)
    url = f"postgresql+psycopg://{user}:{pwd_q}@{host}:{port}/{name}?{query}"
    print(f"[DB] Using DATABASE_URL: postgresql+psycopg://{user}:***@{host}:{port}/{name}?{query}")
    return url

DATABASE_URL = build_database_url()

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
