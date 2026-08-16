"""Scrape HiBid.com open-auction lots for a search keyword.

HiBid actively blocks datacenter IPs (Cloudflare 403), so this is meant to run
from a residential connection (your own computer). The parser below is
deliberately class-name agnostic: instead of depending on HiBid's exact CSS
(which I couldn't observe from a blocked sandbox), it keys off the stable
`/lot/<id>` link structure and reads the money/bid text out of the surrounding
card. The first `python arb.py test-hibid "<keyword>"` run is the calibration
step -- if it finds 0 lots, run it with --dump and send me hibid_dump.html.
"""
import re
import time

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://hibid.com/lots"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MONEY_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")
BIDS_RE = re.compile(r"(\d+)\s+bids?", re.I)
LOT_HREF_RE = re.compile(r"/lot/(\d+)")


def _money(text):
    m = MONEY_RE.search(text or "")
    return float(m.group(1).replace(",", "")) if m else None


def _bid_count(text):
    m = BIDS_RE.search(text or "")
    return int(m.group(1)) if m else None


def _abs(href):
    return href if href.startswith("http") else "https://hibid.com" + href


def fetch(query, page=1, session=None, timeout=25):
    """Return the raw HTML of one HiBid search results page."""
    session = session or requests.Session()
    params = {"q": query, "status": "OPEN", "pageNumber": page}
    r = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def parse_lots(html):
    """Best-effort extraction of lots from a HiBid search results page.

    Finds every anchor linking to a /lot/<id> page, treats the nearest
    surrounding block that contains a '$' as the lot card, and pulls the
    title / current bid / bid count out of that block's text.
    """
    soup = BeautifulSoup(html, "html.parser")
    lots = {}
    for a in soup.find_all("a", href=LOT_HREF_RE):
        href = a.get("href", "")
        m = LOT_HREF_RE.search(href)
        if not m:
            continue
        lot_id = m.group(1)
        title = a.get_text(" ", strip=True)
        if not title:  # image-only anchor -- skip, the text anchor will win
            continue

        # Walk up to the card container that also holds the bid amount.
        block = a
        for _ in range(4):
            if block.parent is None:
                break
            block = block.parent
            if "$" in block.get_text():
                break
        block_text = block.get_text(" ", strip=True)

        entry = lots.get(lot_id)
        # Keep the longest title we've seen for this lot id (usually the name).
        if entry is None or len(title) > len(entry["title"]):
            lots[lot_id] = {
                "id": lot_id,
                "title": title,
                "url": _abs(href),
                "current_bid": _money(block_text),
                "bid_count": _bid_count(block_text),
            }
    return list(lots.values())


def search(query, pages=1, pause=1.5):
    """Search HiBid for `query`, returning a list of lot dicts."""
    session = requests.Session()
    out = []
    for p in range(1, pages + 1):
        lots = parse_lots(fetch(query, page=p, session=session))
        out.extend(lots)
        if not lots:  # no more results (or parser needs calibration)
            break
        if p < pages:
            time.sleep(pause)
    return out
