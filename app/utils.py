import re, urllib.parse
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

CHANNEL_MAP = {
    "facebook.com": "Facebook", "fb.com": "Facebook",
    "x.com": "X (Twitter)", "twitter.com": "X (Twitter)",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube", "youtu.be": "YouTube",
    "tiktok.com": "TikTok", "linkedin.com": "LinkedIn",
    "medium.com": "Blog", "blogspot.com": "Blog",
    "wordpress.com": "Blog", "wordpress.org": "Blog",
}

_analyzer = SentimentIntensityAnalyzer()

def classify_channel(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    host = re.sub(r"^www\.", "", host)
    for k, v in CHANNEL_MAP.items():
        if k in host:
            return v
    return "Blog" if "blog" in host else "Site"

def simple_sentiment(text: str) -> str:
    scores = _analyzer.polarity_scores(text or "")
    c = scores["compound"]
    return "positivo" if c >= 0.15 else "negativo" if c <= -0.15 else "neutro"

import requests, json
from bs4 import BeautifulSoup
import dateparser

HEADERS_FETCH = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36"
}

def infer_published_at(url: str, timeout: int = 6):
    """
    Tenta inferir a data de publicação via:
    - meta property='article:published_time'
    - meta itemprop='datePublished'
    - JSON-LD schema.org (datePublished / dateModified)
    - <time datetime="...">
    Retorna datetime ou None.
    """
    try:
        r = requests.get(url, headers=HEADERS_FETCH, timeout=timeout)
    except Exception:
        return None

    if r.status_code >= 400 or not r.text:
        return None

    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    # 1) Meta tags comuns
    candidates = []
    for sel in [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"itemprop": "datePublished"}),
        ("meta", {"property": "og:updated_time"}),  # fallback
        ("meta", {"name": "DC.date"}),
        ("meta", {"name": "date"}),
    ]:
        tag = soup.find(*sel)
        if tag and tag.get("content"):
            candidates.append(tag.get("content"))

    # 2) JSON-LD schema.org
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        def extract_dates(obj):
            vals = []
            if isinstance(obj, dict):
                for k in ("datePublished", "dateCreated", "dateModified", "uploadDate"):
                    v = obj.get(k)
                    if isinstance(v, str): vals.append(v)
                for v in obj.values():
                    vals += extract_dates(v)
            elif isinstance(obj, list):
                for it in obj:
                    vals += extract_dates(it)
            return vals
        candidates += extract_dates(data)

    # 3) <time datetime="...">
    for t in soup.find_all("time"):
        dt = t.get("datetime")
        if dt: candidates.append(dt)

    # Parse com dateparser
    for raw in candidates:
        dt = dateparser.parse(raw)
        if dt:
            return dt

    return None
