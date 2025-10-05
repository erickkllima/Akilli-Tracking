import re
import time
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# -------------------------------
# Configurações básicas do crawler
# -------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}
GOOGLE_URL = "https://www.google.com/search"
analyzer = SentimentIntensityAnalyzer()

# Mapeamento simples de domínio -> canal
CHANNEL_MAP = {
    "facebook.com": "Facebook",
    "fb.com": "Facebook",
    "x.com": "X (Twitter)",
    "twitter.com": "X (Twitter)",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "tiktok.com": "TikTok",
    "linkedin.com": "LinkedIn",
    "medium.com": "Blog",
    "blogspot.com": "Blog",
    "wordpress.com": "Blog",
    "wordpress.org": "Blog",
}

def classify_channel(url: str) -> str:
    try:
        host = re.sub(r"^www\.", "", urllib.parse.urlparse(url).netloc.lower())
    except Exception:
        return "Site"
    for key, val in CHANNEL_MAP.items():
        if key in host:
            return val
    # fallback simples
    if "blog" in host:
        return "Blog"
    return "Site"

def simple_sentiment(text: str) -> str:
    """
    Usa VADER (otimizado para redes sociais).
    Retorna: 'positivo', 'negativo' ou 'neutro'
    """
    if not text:
        return "neutro"
    scores = analyzer.polarity_scores(text)
    comp = scores["compound"]
    if comp >= 0.15:
        return "positivo"
    elif comp <= -0.15:
        return "negativo"
    return "neutro"

def google_search(query: str, num_results: int = 20, pause_s: float = 1.5):
    """
    Faz scraping leve da SERP do Google (não confiável a longo prazo).
    Para produção, recomendo usar a Google Custom Search JSON API ou SerpAPI.
    """
    collected = []
    per_page = 10
    pages = (num_results + per_page - 1) // per_page

    for page in range(pages):
        start = page * per_page
        params = {
            "q": query,
            "num": str(per_page),
            "start": str(start),
            "hl": "pt-BR",
            "gl": "br",
            "pws": "0",  # personalização off
        }
        resp = requests.get(GOOGLE_URL, headers=HEADERS, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"[WARN] HTTP {resp.status_code} na página {page+1}.")
            print("HTTP Status:", resp.status_code)
            print("HTML recebido (primeiros 500 caracteres):", resp.text[:500])
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        # Seletor comum de resultados orgânicos (pode mudar)
        for item in soup.select("div.tF2Cxc"):
            a = item.select_one("a")
            h3 = item.select_one("h3")
            snippet_el = item.select_one(".VwiC3b, .IsZvec")
            if not a or not h3:
                continue

            url = a.get("href")
            title = h3.get_text(strip=True)
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

            channel = classify_channel(url)
            sentiment = simple_sentiment(f"{title}. {snippet}")

            collected.append({
                "titulo": title,
                "url": url,
                "trecho": snippet,
                "canal": channel,
                "sentimento": sentiment,
                "tags": [],  # usuário poderá adicionar depois
            })

        # Respeito mínimo entre requisições
        time.sleep(2)

    return collected

def main():
    print("=== MVP Monitor de Menções via Google ===")
    termo = input("Digite o termo de busca (ex.: Akilli Brasil): ").strip()
    if not termo:
        print("Termo vazio. Encerrando.")
        return

    try:
        qtd = int(input("Quantos resultados buscar (ex.: 20): ").strip() or "20")
    except ValueError:
        qtd = 20

    print(f"\n[BUSCANDO] \"{termo}\" | resultados: {qtd}\n")
    resultados = google_search(termo, num_results=qtd)

    if not resultados:
        print("Nenhum resultado coletado.")
        return

    # Imprime um resumo legível
    for i, r in enumerate(resultados, 1):
        print(f"{i:02d}. [{r['canal']}] {r['titulo']}")
        print(f"    URL: {r['url']}")
        print(f"    Sentimento: {r['sentimento']}")
        if r["trecho"]:
            print(f"    Trecho: {r['trecho'][:240]}{'...' if len(r['trecho'])>240 else ''}")
        print()

    # Também salva em JSON para etapas seguintes
    out = {
        "termo": termo,
        "total": len(resultados),
        "itens": resultados
    }
    with open("resultados_google.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print('>> Arquivo salvo: "resultados_google.json"')

if __name__ == "__main__":
    main()
