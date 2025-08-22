from __future__ import annotations
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
import json, pathlib
from urllib import robotparser
from sqlalchemy.orm import Session
from .models import Article
from .utils import canonical_url, domain_of, is_blocked
from .dedupe import DupeFilter
from .config import settings

ALLOWED_PATH = pathlib.Path('/app/allowed_domains.json')
BLOCKED_PATH = pathlib.Path('/app/blocked_domains.json')

def load_lists() -> tuple[list[str], list[str]]:
    allowed = json.loads(ALLOWED_PATH.read_text(encoding='utf-8'))
    blocked = json.loads(BLOCKED_PATH.read_text(encoding='utf-8'))
    return allowed, blocked

DUPE = DupeFilter()
HEADERS = {"User-Agent": settings.USER_AGENT}

def _robots_ok(url: str) -> bool:
    rp = robotparser.RobotFileParser()
    base = f"https://{domain_of(url)}"
    rp.set_url(urljoin(base, "/robots.txt"))
    try:
        rp.read()
        return rp.can_fetch(settings.USER_AGENT, url)
    except Exception:
        return True

def _parse_published(entry) -> datetime | None:
    for k in ("published_parsed", "updated_parsed"):
        val = entry.get(k)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for k in ("published", "updated"):
        if entry.get(k):
            try:
                return parsedate_to_datetime(entry[k])
            except Exception:
                continue
    return None

def _fetch_html(url: str):
    if not _robots_ok(url):
        return None, None
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return None, None
    html = r.text
    soup = BeautifulSoup(html, 'lxml')

    def first(*vals):
        for v in vals:
            if v and isinstance(v, str) and v.strip():
                return v.strip()
        return None

    title = first(
        soup.select_one('meta[property="og:title"]')['content'] if soup.select_one('meta[property="og:title"]') else None,
        soup.title.string if soup.title and soup.title.string else None
    )

    # forsøk å hente meningsfull tekst
    parts = []
    for sel in ['article', 'main', '.post', '.entry-content', '.article-content', '[role="main"]']:
        node = soup.select_one(sel)
        if node:
            txt = node.get_text(" ", strip=True)
            if txt and len(txt) > 200:
                parts.append(txt)
    if not parts:
        # fallback: alle <p>
        txt = " ".join(p.get_text(" ", strip=True) for p in soup.find_all('p'))
        parts.append(txt)

    # meta description kan være nyttig for summary
    meta_desc = soup.select_one('meta[name="description"]')
    og_desc = soup.select_one('meta[property="og:description"]')
    summary = first(
        (meta_desc['content'] if meta_desc and meta_desc.has_attr('content') else None),
        (og_desc['content'] if og_desc and og_desc.has_attr('content') else None),
        parts[0] if parts else None
    )

    return title, (summary or "")[:1000]

def _detect_language(title: str, summary: str) -> str:
    """Simple language detection based on common words and patterns"""
    text = f"{title} {summary}".lower()
    
    # Norwegian indicators
    no_words = ['og', 'det', 'er', 'til', 'på', 'av', 'med', 'for', 'som', 'ikke', 'har', 'var', 'vil', 'skal', 'kan', 'må', 'den', 'de', 'jeg', 'du', 'vi', 'han', 'hun', 'norsk', 'norge', 'oslo', 'regjeringen', 'stortinget', 'kroner', 'år', 'dag', 'måned']
    en_words = ['the', 'and', 'of', 'to', 'in', 'is', 'that', 'for', 'with', 'as', 'was', 'will', 'are', 'this', 'have', 'from', 'they', 'we', 'been', 'their', 'said', 'each', 'which', 'she', 'do', 'how', 'if', 'up', 'out', 'many', 'time', 'very', 'when', 'much', 'new', 'would', 'there', 'what', 'so', 'people', 'can', 'first', 'way', 'could', 'get', 'use', 'work', 'made', 'may', 'also', 'after', 'now', 'being']
    
    no_count = sum(1 for word in no_words if word in text)
    en_count = sum(1 for word in en_words if word in text)
    
    # Check for Chinese/Asian characters
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return 'zh'
    
    if no_count > en_count:
        return 'no'
    elif en_count > 0:
        return 'en'
    else:
        return 'unknown'

def _categorize_article(title: str, summary: str, domain: str) -> str:
    """Categorize articles based on content and source"""
    text = f"{title} {summary}".lower()
    
    # Health/Medical/Vaccine categories
    health_keywords = ['vaksine', 'vaccine', 'covid', 'mrna', 'pfizer', 'moderna', 'helse', 'health', 'medical', 'pandemic', 'virus', 'immunity', 'antibodies', 'side effects', 'bivirkninger']
    if any(keyword in text for keyword in health_keywords):
        return 'helse'
    
    # Politics
    politics_keywords = ['politik', 'politics', 'election', 'valg', 'parlament', 'government', 'regjeringen', 'stortinget', 'president', 'minister', 'trump', 'biden', 'putin', 'nato', 'eu']
    if any(keyword in text for keyword in politics_keywords):
        return 'politikk'
    
    # Economics/Finance
    economics_keywords = ['økonomi', 'economy', 'finance', 'bank', 'kroner', 'dollar', 'inflation', 'inflasjon', 'recession', 'marked', 'market', 'investering', 'investment']
    if any(keyword in text for keyword in economics_keywords):
        return 'økonomi'
    
    # War/Military
    war_keywords = ['krig', 'war', 'ukraine', 'ukraina', 'russia', 'russland', 'military', 'militær', 'weapon', 'våpen', 'conflict', 'konflikt', 'invasion', 'invasjon']
    if any(keyword in text for keyword in war_keywords):
        return 'krig'
    
    # Climate/Environment
    climate_keywords = ['klima', 'climate', 'environment', 'miljø', 'carbon', 'karbon', 'global warming', 'green', 'grønn', 'renewable', 'fornybar']
    if any(keyword in text for keyword in climate_keywords):
        return 'klima'
    
    # Technology
    tech_keywords = ['teknologi', 'technology', 'ai', 'artificial intelligence', 'robot', 'digital', 'internet', 'cyber', 'blockchain', 'bitcoin']
    if any(keyword in text for keyword in tech_keywords):
        return 'teknologi'
    
    # Culture/Society
    culture_keywords = ['kultur', 'culture', 'society', 'samfunn', 'religion', 'islam', 'kristendom', 'innvandring', 'immigration', 'feminism', 'woke']
    if any(keyword in text for keyword in culture_keywords):
        return 'kultur'
    
    # Media/Censorship
    media_keywords = ['media', 'medier', 'censorship', 'sensur', 'free speech', 'ytringsfrihet', 'journalism', 'journalistikk', 'fake news']
    if any(keyword in text for keyword in media_keywords):
        return 'medier'
    
    return 'generelt'

def fetch_and_store(db: Session) -> dict:
    allowed, blocked = load_lists()
    stats = {"seen":0, "saved":0, "skipped_blocked":0, "dupes":0}

    def handle_item(item, src_domain):
        nonlocal stats
        url = canonical_url(item.get('link') or item.get('id') or "")
        if not url:
            return
        dom = domain_of(url)
        if dom != src_domain and is_blocked(dom, blocked):
            stats["skipped_blocked"] += 1
            return
        if is_blocked(src_domain, blocked):
            stats["skipped_blocked"] += 1
            return
        title = (item.get('title') or '').strip()
        summary = (item.get('summary') or '').strip()
        published_at = _parse_published(item)
        author = (item.get('author') or None)
        language = item.get('language') or None
        
        # Detect language and filter out non-Norwegian/English content
        detected_lang = _detect_language(title, summary)
        if detected_lang not in ['no', 'en', 'nb', 'nn']:
            stats["skipped_blocked"] += 1
            return
        language = detected_lang
        
        # Categorize article
        theme = _categorize_article(title, summary, src_domain)

        if len(summary) < 40:
            t2, text = _fetch_html(url)
            if t2 and not title:
                title = t2
            if text and len(summary) < 40:
                summary = text[:1000]

        seen, sig = DUPE.seen(url, f"{title}\n{summary}")
        if seen:
            stats["dupes"] += 1
            return

        art = Article(
            url=url,
            url_canonical=url,
            source_domain=src_domain,
            source_name=src_domain,
            title=title or "(uten tittel)",
            summary=summary or None,
            author=author,
            published_at=published_at,
            language=language,
            theme=theme,
            raw=item,
            minhash_sig=sig,
        )
        db.add(art)
        stats["saved"] += 1

    for domain in allowed:
        try:
            # try common feed paths including rss.xml
            feed_urls = [f"https://{domain}/feed", f"https://{domain}/rss", f"https://{domain}/rss.xml", f"https://{domain}/atom.xml"]
            fetched = False
            for fu in feed_urls:
                try:
                    r = requests.get(fu, headers=HEADERS, timeout=12)
                except Exception:
                    continue
                if r.status_code == 304:
                    fetched = True
                    break
                if r.status_code == 200 and ("xml" in r.headers.get("content-type", "") or r.text.lstrip().startswith("<?xml")):
                    parsed = feedparser.parse(r.text)
                    for entry in parsed.entries:
                        handle_item(entry, domain)
                    fetched = True
                    break
            if not fetched:
                # Fallback: try homepage and scrape
                r = requests.get(f"https://{domain}", headers=HEADERS, timeout=12)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'lxml')
                    for a in soup.select('article a[href], h2 a[href], .post a[href]')[:30]:
                        href = a.get('href')
                        if not href:
                            continue
                        url = canonical_url(href if href.startswith('http') else urljoin(f"https://{domain}", href))
                        handle_item({"link": url, "title": a.get_text(strip=True)}, domain)
        except Exception:
            continue

    db.commit()
    return stats
