import os
import time
import json
import re
import urllib.parse
import requests
from dotenv import load_dotenv
load_dotenv()
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID  = os.getenv("GOOGLE_CSE_ID")
HEADERS = {"Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8"}
analyzer = SentimentIntensityAnalyzer()

CHANNEL_MAP = {
    "facebook.com": "Facebook", "fb.com": "Facebook",
    "x.com": "X (Twitter)", "twitter.com": "X (Twitter)",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "tiktok.com": "TikTok", "linkedin.com": "LinkedIn",
    "medium.com": "Blog", "blogspot.com": "Blog",
    "wordpress.com": "Blog", "wordpress.org": "Blog",
}

def classify_channel(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    host = re.sub(r"^www\.", "", host)
    for k, v in CHANNEL_MAP.items():
        if k in host:
            return v
    return "Blog" if "blog" in host else "Site"

def simple_sentiment(text: str) -> str:
    scores = analyzer.polarity_scores(text or "")
    c = scores["compound"]
    return "positivo" if c >= 0.15 else "negativo" if c <= -0.15 else "neutro"

def cse_search(query: str, total: int = 20):
    if not API_KEY or not CSE_ID:
        raise RuntimeError("Defina GOOGLE_API_KEY e GOOGLE_CSE_ID no ambiente.")

    results = []
    start_index = 1  # CSE usa 1-based
    while len(results) < total:
        num = min(10, total - len(results))
        params = {
            "key": API_KEY,
            "cx": CSE_ID,
            "q": query,
            "num": num,
            "start": start_index,           # <-- IMPORTANTE
            "hl": "pt-BR",
            "gl": "br",
            "safe": "off",
            # Dica: reduzir campos economiza cota e acelera
            "fields": "items(title,link,snippet),queries(nextPage(startIndex))"
        }
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params, headers=HEADERS, timeout=30
        )
        if r.status_code != 200:
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text[:500]}
            print(f"[WARN] HTTP {r.status_code}: {json.dumps(data, ensure_ascii=False)[:800]}")
            if r.status_code in (401, 403):
                print("Dica: verifique se a Custom Search API está habilitada, billing e restrições da chave.")
            break

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

        # próxima página (se houver)
        next_page = data.get("queries", {}).get("nextPage", [])
        if next_page:
            start_index = next_page[0].get("startIndex", 0)
            time.sleep(0.8)  # backoff curto e educado
        else:
            break

    return results[:total]

def main():
    termo = input("Termo de busca: ").strip()
    qtd = int(input("Qtd resultados (ex.: 20): ").strip() or "20")
    print(f"[BUSCANDO] \"{termo}\" | {qtd}")
    itens = cse_search(termo, total=qtd)
    if not itens:
        print("Nenhum resultado.")
        return
    out = {"termo": termo, "total": len(itens), "itens": itens}
    with open("resultados_google.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for i, r in enumerate(itens, 1):
        print(f"{i:02d}. [{r['canal']}] {r['titulo']}  | {r['sentimento']}\n    {r['url']}")
    print('>> Salvo em resultados_google.json')

if __name__ == "__main__":
    main()
