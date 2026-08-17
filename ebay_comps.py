"""Look up recent eBay SOLD prices ("comps") for a search term.

eBay's genuine sold-price data isn't in their free official API (it's behind the
access-gated Marketplace Insights API), so this reads the public "Sold listings"
search page via net.session() (browser impersonation + cookie warm-up).

eBay challenges suspicious traffic with a "Security Measure" captcha page --
common from datacenter IPs, uncommon from a residential connection. When that
happens we raise BlockedError so the caller can degrade gracefully instead of
parsing a captcha page as if it were results.
"""
import re
import statistics
import urllib.parse

from bs4 import BeautifulSoup

import net

SEARCH_URL = "https://www.ebay.com/sch/i.html"
MONEY_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")


class BlockedError(Exception):
    """eBay served a captcha / security-verification page instead of results."""


# eBay rotates several interstitial/challenge pages; any of these means "blocked".
BLOCK_MARKERS = (
    "security measure",
    "please verify yourself",
    "pardon our interruption",
    "are you a human",
    "px-captcha",
    "checking your browser",
)


def sold_url(query):
    """Human URL for eBay sold/completed listings -- handy for manual checks."""
    q = urllib.parse.urlencode({"_nkw": query, "LH_Sold": 1, "LH_Complete": 1, "_sop": 13})
    return f"{SEARCH_URL}?{q}"


def _first_price(text):
    m = MONEY_RE.search(text or "")
    return float(m.group(1).replace(",", "")) if m else None


def raw(query, session=None, timeout=30):
    """Return the raw HTML of an eBay sold search (no block check -- for dumps)."""
    session = session or net.session(warmup="https://www.ebay.com/")
    params = {"_nkw": query, "LH_Sold": 1, "LH_Complete": 1, "_sop": 13, "_ipg": 60}
    r = session.get(SEARCH_URL, params=params, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_sold(query, session=None, timeout=30):
    """Return sold-search HTML, raising BlockedError on a captcha page."""
    html = raw(query, session=session, timeout=timeout)
    low = html.lower()
    if any(marker in low for marker in BLOCK_MARKERS):
        raise BlockedError("eBay returned a security/verification page")
    return html


def parse_sold(html, min_price=5.0, max_comps=20):
    """Return a list of sold prices from an eBay sold-search page.

    eBay has several markup generations in the wild, so we try the classic
    s-item cards first, then newer card containers, then a last-ditch scan.
    """
    soup = BeautifulSoup(html, "html.parser")

    items = soup.select("li.s-item")
    if len(items) < 2:  # newer layouts
        items = soup.select("li.brwrvr__item-card, div.s-card, div.su-card-container")

    prices = []
    for item in items:
        text = item.get_text(" ", strip=True)
        if text.lower().startswith("shop on ebay"):
            continue  # eBay's placeholder first cell
        price_el = item.select_one(".s-item__price, .su-styled-text.positive, .s-card__price")
        price = _first_price(price_el.get_text()) if price_el else _first_price(text)
        if price is None or price < min_price:
            continue
        prices.append(price)
        if len(prices) >= max_comps:
            break
    return prices


def comps(query, min_price=5.0, max_comps=20):
    """Return a summary dict of eBay sold comps for `query`.

    On a captcha block, returns n=0 with blocked=True rather than raising, so a
    batch run keeps going and can report the block at the end.
    """
    out = {"query": query, "n": 0, "median": None, "prices": [], "blocked": False,
           "url": sold_url(query)}
    try:
        prices = parse_sold(fetch_sold(query), min_price=min_price, max_comps=max_comps)
    except BlockedError:
        out["blocked"] = True
        return out
    if prices:
        out.update(n=len(prices), median=round(statistics.median(prices), 2),
                   low=min(prices), high=max(prices), prices=prices)
    return out
