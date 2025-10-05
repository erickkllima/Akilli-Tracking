# app/db.py
import os
from urllib.parse import quote_plus
from sqlmodel import SQLModel, create_engine, Session

def _normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

def _build_url_from_parts() -> str | None:
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd  = os.getenv("DB_PASSWORD")
    hostaddr = os.getenv("DB_HOSTADDR")  # IPv4 opcional (força IPv4)

    if all([host, port, name, user, pwd]):
        user_q = quote_plus(user)
        pwd_q  = quote_plus(pwd)
        qparams = ["sslmode=require", "connect_timeout=10", "application_name=render"]
        if hostaddr:
            qparams.append(f"hostaddr={hostaddr}")
        query = "&".join(qparams)
        return f"postgresql+psycopg://{user_q}:{pwd_q}@{host}:{port}/{name}?{query}"
    return None

# 1) Tenta partes (mais seguro)
DATABASE_URL = _build_url_from_parts()

# 2) Se não houver, usa DATABASE_URL bruta e normaliza prefixo
if not DATABASE_URL:
    raw = os.getenv("DATABASE_URL", "")
    if raw:
        DATABASE_URL = _normalize_url(raw)

if DATABASE_URL:
    # log enxuto (sem senha)
    try:
        safe_url = DATABASE_URL
        if "://" in safe_url and "@" in safe_url:
            # mascara credenciais
            scheme, rest = safe_url.split("://", 1)
            user_pass, host_part = rest.split("@", 1)
            if ":" in user_pass:
                user = user_pass.split(":")[0]
            else:
                user = user_pass
            safe_url = f"{scheme}://{user}:***@{host_part}"
        print(f"[DB] Using DATABASE_URL: {safe_url}")
    except Exception:
        pass

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    print("[DB] No DATABASE_URL found; using SQLite local.")
    engine = create_engine("sqlite:///./monitorx.db", connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
