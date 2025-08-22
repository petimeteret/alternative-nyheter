\
import re
from urllib.parse import urlparse
from url_normalize import url_normalize

MAINSTREAM_PATTERNS = [
    r"(?:vg|nrk|dagbladet|aftenposten|tv2)\.no",
    r"(?:bbc|cnn|reuters|apnews|nytimes|guardian)\.com",
]

def canonical_url(url: str) -> str:
    return url_normalize(url, default_scheme="https")

def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower()

def is_blocked(domain: str, blocked_list: list[str]) -> bool:
    dom = domain.lower()
    if dom in blocked_list:
        return True
    for pat in MAINSTREAM_PATTERNS:
        if re.search(pat, dom):
            return True
    return False
