# app/db.py
from __future__ import annotations
import os
import socket
from typing import Optional
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v.strip() if isinstance(v, str) else default

def _resolve_ipv4(host: str) -> Optional[str]:
    """
    Resolve o IPv4 (A record) do host. Se não conseguir, retorna None.
    Isso evita depender do ambiente do Render/Windows devolver AAAA (IPv6).
    """
    try:
        # AF_INET => só IPv4; getaddrinfo retorna [(family, socktype, proto, canonname, sockaddr), ...]
        infos = socket.getaddrinfo(host, None, family=socket.AF_INET)
        for family, _, _, _, sockaddr in infos:
            if family == socket.AF_INET and sockaddr and len(sockaddr) >= 1:
                return sockaddr[0]  # IP v4
    except Exception:
        pass
    return None

def build_database_url_from_parts() -> str:
    host = _env("DB_HOST", "")
    port = _env("DB_PORT", "5432")
    db   = _env("DB_NAME", "postgres")
    user = _env("DB_USER", "")
    pwd  = _env("DB_PASSWORD", "")

    # Se o usuário não definiu DB_HOSTADDR, tentamos resolver IPv4 automaticamente
    hostaddr = _env("DB_HOSTADDR", None)
    if not hostaddr and host:
        hostaddr = _resolve_ipv4(host)

    base = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"
    params = [
        "sslmode=require",
        "connect_timeout=10",
        "application_name=render",
        "target_session_attrs=read-write",
    ]
    if hostaddr:
        params.append(f"hostaddr={hostaddr}")  # psycopg3 aceita libpq params na querystring

    return base + "?" + "&".join(params)

# 1) Usa DATABASE_URL se existir; 2) senão, monta das partes
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL").strip()
    _printed_url = DATABASE_URL
    # ofusca a senha ao logar
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

CONNECT_ARGS = {
    "sslmode": "require",
    "prepare_threshold": 0,  # amigável a poolers; inofensivo na conexão direta
    "target_session_attrs": "read-write",
    # "options": "-c statement_timeout=30000",  # opcional
}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    connect_args=CONNECT_ARGS,
)

def init_db() -> None:
    from app.models import SQLModel  # evita import circular
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)
