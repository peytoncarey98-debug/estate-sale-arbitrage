"""Scrape HiBid.com open-auction lots for a search keyword.

HiBid sits behind Cloudflare bot protection that fingerprints the HTTP client,
so requests go through net.session() (browser impersonation). The lot cards are
Angular components; rather than depend on their exact CSS class names, this
parser keys off the stable `/lot/<id>` link and reads the price/bid/time text
out of the surrounding card. HiBid shows prices as "High Bid: 6.00 USD".
"""
import re
import time

from bs4 import BeautifulSoup

import net

SEARCH_URL = "https://hibid.com/lots"

# Prefer the labelled current/high bid; fall back to a bare "N.NN USD" or "$N".
HIGH_BID_RE = re.compile(
    r"(?:High Bid|Current Bid|Winning Bid|Starting Bid|Opening Bid|Minimum Bid)"
    r"\D{0,3}([\d,]+(?:\.\d{2})?)",
    re.I,
)
USD_RE = re.compile(r"([\d,]+\.\d{2})\s*USD")
DOLLAR_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")
BIDS_RE = re.compile(r"(\d+)\s+bids?", re.I)
TIME_RE = re.compile(r"(\d+d(?:\s*\d+h)?(?:\s*\d+m)?|\d+h(?:\s*\d+m)?|\d+m)")
LOT_HREF_RE = re.compile(r"/lot/(\d+)")
_LOTNUM_RE = re.compile(r"lot\s*#?\s*\d+\s*\|?", re.I)


def _bid(text):
    for rx in (HIGH_BID_RE, USD_RE, DOLLAR_RE):
        m = rx.search(text or "")
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _bid_count(text):
    m = BIDS_RE.search(text or "")
    return int(m.group(1)) if m else None


def _time_left(text):
    """Return (display_string, minutes) for the lot's remaining time."""
    m = TIME_RE.search(text or "")
    if not m:
        return None, None
    s = m.group(0)
    d = int(re.search(r"(\d+)d", s).group(1)) if "d" in s else 0
    h = int(re.search(r"(\d+)h", s).group(1)) if "h" in s else 0
    mi = int(re.search(r"(\d+)m", s).group(1)) if "m" in s else 0
    return re.sub(r"\s+", " ", s), d * 1440 + h * 60 + mi


def _abs(href):
    return href if href.startswith("http") else "https://hibid.com" + href


def clean_title(title):
    """Turn a lot title into a clean eBay search query (drop lot #, model #s)."""
    t = _LOTNUM_RE.sub(" ", title)
    t = re.sub(r"\b[A-Za-z]?\d{2,}-\d+\b", " ", t)  # model numbers like 72-6
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(t.split()[:8])


def fetch(query, page=1, session=None, timeout=30):
    """Return the raw HTML of one HiBid search results page."""
    session = session or net.session()
    params = {"q": query, "status": "OPEN", "pageNumber": page}
    r = session.get(SEARCH_URL, params=params, timeout=timeout)
    r.raise_for_status()
    return r.text


def parse_lots(html):
    """Extract lots from a HiBid search results page."""
    soup = BeautifulSoup(html, "html.parser")
    lots = {}
    for a in soup.find_all("a", href=LOT_HREF_RE):
        href = a.get("href", "")
        m = LOT_HREF_RE.search(href)
        if not m:
            continue
        lot_id = m.group(1)
        title = a.get_text(" ", strip=True)
        if not title:  # image-only anchor; the text anchor for this lot wins
            continue

        # Climb to the first ancestor holding the bid text -- that's the card.
        block = a
        for _ in range(8):
            if block.parent is None:
                break
            block = block.parent
            if "USD" in block.get_text() or "$" in block.get_text():
                break
        block_text = block.get_text(" ", strip=True)
        tl, mins = _time_left(block_text)

        entry = lots.get(lot_id)
        if entry is None or len(title) > len(entry["title"]):
            lots[lot_id] = {
                "id": lot_id,
                "title": title,
                "url": _abs(href),
                "current_bid": _bid(block_text),
                "bid_count": _bid_count(block_text),
                "time_left": tl,
                "end_minutes": mins,
            }
    return list(lots.values())


def search(query, pages=1, pause=1.5):
    """Search HiBid for `query`, returning a list of lot dicts."""
    s = net.session()
    out = []
    for p in range(1, pages + 1):
        lots = parse_lots(fetch(query, page=p, session=s))
        out.extend(lots)
        if not lots:
            break
        if p < pages:
            time.sleep(pause)
    return out
