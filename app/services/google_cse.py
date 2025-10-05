# app/services/google_cse.py
import os, time, json, requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from app.utils import classify_channel, simple_sentiment

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID  = os.getenv("GOOGLE_CSE_ID")

def _yyyymmdd(date_str: str) -> str:
    # Espera 'YYYY-MM-DD' e retorna 'YYYYMMDD'
    return date_str.replace("-", "")

def cse_search(
    query: str,
    total: int = 20,
    date_from: Optional[str] = None,  # 'YYYY-MM-DD'
    date_to: Optional[str] = None,    # 'YYYY-MM-DD'
) -> List[Dict]:
    if not API_KEY or not CSE_ID:
        raise RuntimeError("Configure GOOGLE_API_KEY e GOOGLE_CSE_ID no .env")

    results = []
    start_index = 1  # 1-based

    # 'sort' da CSE suporta 'date:r:YYYYMMDD:YYYYMMDD'
    sort_val = None
    if date_from and date_to:
        sort_val = f"date:r:{_yyyymmdd(date_from)}:{_yyyymmdd(date_to)}"
    elif date_from and not date_to:
        sort_val = f"date:r:{_yyyymmdd(date_from)}:{_yyyymmdd(date_from)}"
    elif date_to and not date_from:
        sort_val = f"date:r:{_yyyymmdd(date_to)}:{_yyyymmdd(date_to)}"

    # Capamos 'total' pra evitar loops sem fim (pode ajustar)
    total = max(1, min(int(total), 100)) if total else 50  # se None/0, puxa até 50

    while len(results) < total:
        num = min(10, total - len(results))
        params = {
            "key": API_KEY,
            "cx": CSE_ID,
            "q": query,
            "num": num,
            "start": start_index,
            "hl": "pt-BR",
            "gl": "br",
            "safe": "off",
            "fields": "items(title,link,snippet),queries(nextPage(startIndex))",
        }
        if sort_val:
            params["sort"] = sort_val

        r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=30)
        if r.status_code != 200:
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text[:500]}
            raise RuntimeError(f"Custom Search API {r.status_code}: {json.dumps(data)[:500]}")

        data = r.json()
        items = data.get("items", [])
        if not items:
            break

        for it in items:
            link = it.get("link", "")
            title = it.get("title", "")
            snippet = it.get("snippet", "")
            canal = classify_channel(link)
            senti = simple_sentiment(f"{title}. {snippet}")
            results.append({
                "titulo": title, "url": link, "trecho": snippet,
                "canal": canal, "sentimento": senti, "tags": []
            })

        next_page = data.get("queries", {}).get("nextPage", [])
        if next_page:
            start_index = next_page[0].get("startIndex", 0)
            time.sleep(0.8)
        else:
            break

    return results[:total]
