from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from app.utils import infer_published_at  # <--- importar
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlmodel import select
from pydantic import BaseModel
from app.db import init_db, get_session
from app.models import Mention
from app.services.google_cse import cse_search
from sqlmodel import select, func
from pydantic import BaseModel
from sqlalchemy import func as sa_func  # já temos func, mas renomeio p/ evitar confusão
from datetime import datetime
from typing import Dict

class BulkDelete(BaseModel):
    ids: List[int]

class TagUpdate(BaseModel):
    add: Optional[List[str]] = None
    remove: Optional[List[str]] = None

app = FastAPI(title="MonitorX - MVP", version="0.1")

# CORS liberado no MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", include_in_schema=False)
def root():
    # redireciona para a UI de testes
    return RedirectResponse(url="/docs")


@app.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok", "service": "MonitorX API"}


@app.post("/search")
def search_and_save(
    term: str,
    qty: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    enrich_dates: bool = False,   # quando True, tenta descobrir published_at de cada URL
):
    # Limite efetivo no backend (se nada vier, usa 50)
    qty_eff = 50 if not qty else max(1, min(int(qty), 100))
    print(f"[SEARCH] term='{term}', qty={qty} (efetivo={qty_eff}), date_from={date_from}, date_to={date_to}, enrich_dates={enrich_dates}")

    # 1) Buscar na CSE
    try:
        items = cse_search(
            term,
            total=qty_eff,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2) Dedup por (termo, url)
    unique = {}
    for it in items:
        key = (term, it.get("url", ""))
        if key not in unique:
            unique[key] = it
    items = list(unique.values())

    # 3) Persistência
    saved = 0
    with get_session() as s:
        for it in items:
            pub_dt = None
            if enrich_dates:
                # tenta inferir data de publicação da própria página (rápido, timeout curto)
                pub_dt = infer_published_at(it.get("url", ""))  # requer utils.infer_published_at

            m = Mention(
                termo=term,
                titulo=it.get("titulo", ""),
                url=it.get("url", ""),
                trecho=it.get("trecho", ""),
                canal=it.get("canal", "Site"),
                sentimento=it.get("sentimento", "neutro"),
                tags_csv="",
                published_at=pub_dt,
            )
            s.add(m)
            saved += 1
        s.commit()

    print(f"[SEARCH] Salvos {saved} (deduplicados) para '{term}'.")
    return {"termo": term, "total": saved}

@app.get("/mentions")
def list_mentions(
    q: Optional[str] = None,
    canal: Optional[str] = None,
    sentimento: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    page: Optional[int] = None,
    date_field: str = "mined",              # 'mined' | 'published'
    date_from: Optional[str] = None,        # 'YYYY-MM-DD'
    date_to: Optional[str] = None,
):
    limit = max(1, min(int(limit), 100))
    if page is not None and page >= 1:
        offset = (int(page) - 1) * limit

    with get_session() as s:
        base = select(Mention)
        if q:
            like = f"%{q}%"
            base = base.where((Mention.titulo.like(like)) | (Mention.trecho.like(like)))
        if canal:
            base = base.where(Mention.canal == canal)
        if sentimento:
            base = base.where(Mention.sentimento == sentimento)
        if tag:
            like = f"%{tag}%"
            base = base.where(Mention.tags_csv.like(like))

        # Filtro por data, escolhendo campo
        field = Mention.created_at if date_field == "mined" else Mention.published_at
        if date_from:
            base = base.where(field >= datetime.fromisoformat(date_from + "T00:00:00"))
        if date_to:
            base = base.where(field <= datetime.fromisoformat(date_to + "T23:59:59"))

        # total
        total = s.exec(select(func.count()).select_from(base.subquery())).one()

        # paginação
        stmt = base.order_by(Mention.id.desc()).offset(offset).limit(limit)
        rows = s.exec(stmt).all()

        def to_dict(m: Mention):
            return {
                "id": m.id,
                "termo": m.termo,
                "titulo": m.titulo,
                "url": m.url,
                "trecho": m.trecho,
                "canal": m.canal,
                "sentimento": m.sentimento,
                "tags": m.tags,
                "created_at": m.created_at.isoformat() + "Z",
                "published_at": m.published_at.isoformat() + "Z" if m.published_at else None,
            }

        page_num = (offset // limit) + 1
        page_count = (total + limit - 1) // limit if total else 1

        return {
            "items": [to_dict(m) for m in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "page": page_num,
            "page_count": page_count,
            "has_prev": page_num > 1,
            "has_next": page_num < page_count,
        }

@app.patch("/mentions/{mention_id}/tags")
def update_tags(mention_id: int, payload: TagUpdate):
    with get_session() as s:
        m = s.get(Mention, mention_id)
        if not m:
            raise HTTPException(status_code=404, detail="Mention not found")

        current = set(m.tags)

        if payload.add:
            current |= set([t.strip() for t in payload.add if t and t.strip()])

        if payload.remove:
            current -= set([t.strip() for t in payload.remove if t and t.strip()])

        m.set_tags(list(current))
        s.add(m)
        s.commit()
        s.refresh(m)

        return {"id": m.id, "tags": m.tags}
    
from fastapi import status

@app.delete("/mentions/{mention_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mention(mention_id: int):
    with get_session() as s:
        m = s.get(Mention, mention_id)
        if not m:
            raise HTTPException(status_code=404, detail="Mention not found")
        s.delete(m)
        s.commit()
    # 204 No Content, não precisa retornar body
    return

@app.post("/mentions/bulk_delete")
def bulk_delete_mentions(payload: BulkDelete):
    ids = [i for i in (payload.ids or []) if isinstance(i, int)]
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")

    with get_session() as s:
        count = 0
        for mid in ids:
            m = s.get(Mention, mid)
            if m:
                s.delete(m)
                count += 1
        s.commit()
    return {"deleted": count}

@app.get("/analytics")
def analytics(
    q: Optional[str] = None,
    canal: Optional[str] = None,
    sentimento: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[str] = None,   # 'YYYY-MM-DD'
    date_to: Optional[str] = None,     # 'YYYY-MM-DD'
    date_field: str = "mined",         # 'mined' | 'published'
):
    """
    Retorna agregados:
      - total
      - by_sentiment: [{sentimento, count}]
      - by_channel:   [{canal, count}]
      - timeseries_daily: [{date, count}]
      - top_tags:     [{tag, count}]
    Todos os filtros são opcionais e aplicados a todas as agregações.
    """

    # Escolhe o campo de data para filtros e timeseries
    field = Mention.created_at if date_field == "mined" else Mention.published_at

    with get_session() as s:
        # -------- base filtrada --------
        base = select(Mention)

        if q:
            like = f"%{q}%"
            base = base.where((Mention.titulo.like(like)) | (Mention.trecho.like(like)))

        if canal:
            base = base.where(Mention.canal == canal)

        if sentimento:
            base = base.where(Mention.sentimento == sentimento)

        if tag:
            like = f"%{tag}%"
            base = base.where(Mention.tags_csv.like(like))

        if date_from:
            base = base.where(field >= datetime.fromisoformat(date_from + "T00:00:00"))

        if date_to:
            base = base.where(field <= datetime.fromisoformat(date_to + "T23:59:59"))

        # -------- total --------
        total = s.exec(
            select(sa_func.count()).select_from(base.subquery())
        ).one()

        # -------- por sentimento --------
        _by_senti_rows = s.exec(
            select(Mention.sentimento, sa_func.count())
            .select_from(base.subquery())
            .group_by(Mention.sentimento)
        ).all()
        by_sentiment = [{"sentimento": k or "desconhecido", "count": v} for k, v in _by_senti_rows]

        # -------- por canal --------
        _by_channel_rows = s.exec(
            select(Mention.canal, sa_func.count())
            .select_from(base.subquery())
            .group_by(Mention.canal)
        ).all()
        by_channel = [{"canal": k or "desconhecido", "count": v} for k, v in _by_channel_rows]

        # -------- série temporal diária (pelo campo escolhido) --------
        _times = s.exec(
            select(sa_func.date(field), sa_func.count())
            .select_from(base.subquery())
            .group_by(sa_func.date(field))
            .order_by(sa_func.date(field))
        ).all()
        timeseries_daily = [{"date": d, "count": c} for d, c in _times]

        # -------- top tags (contado em Python a partir do CSV) --------
        rows = s.exec(base).all()
        tag_counts: Dict[str, int] = {}
        for m in rows:
            for t in m.tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

        top_tags = sorted(
            [{"tag": k, "count": v} for k, v in tag_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:20]

        # -------- retorno --------
        return {
            "total": total,
            "by_sentiment": by_sentiment,
            "by_channel": by_channel,
            "timeseries_daily": timeseries_daily,
            "top_tags": top_tags,
        }

@app.post("/mentions/enrich_dates")
def enrich_dates_endpoint(limit: int = 50, only_missing: bool = True):
    """
    Enriquecimento em lote: tenta preencher published_at em até `limit` menções.
    Por padrão, processa apenas as que ainda não têm published_at.
    """
    with get_session() as s:
        stmt = select(Mention).order_by(Mention.id.desc())
        if only_missing:
            stmt = stmt.where(Mention.published_at.is_(None))

        rows = s.exec(stmt.limit(max(1, min(limit, 500)))).all()
        if not rows:
            return {"processed": 0, "updated": 0}

        updated = 0
        for m in rows:
            dt = infer_published_at(m.url)
            if dt:
                m.published_at = dt
                s.add(m)
                updated += 1
        s.commit()

    return {"processed": len(rows), "updated": updated}