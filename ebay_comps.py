"""Look up recent eBay SOLD prices ("comps") for a search term.

eBay's genuine sold-price data isn't in their free official API (it lives behind
the access-gated Marketplace Insights API), so this reads the public "Sold
listings" search results page. Run from a residential connection.
"""
import re
import statistics

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.ebay.com/sch/i.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
MONEY_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{1,2})?)")


def _first_price(text):
    m = MONEY_RE.search(text or "")
    return float(m.group(1).replace(",", "")) if m else None


def fetch_sold(query, session=None, timeout=25):
    """Return raw HTML for an eBay sold/completed search."""
    session = session or requests.Session()
    params = {
        "_nkw": query,
        "LH_Sold": 1,      # sold only
        "LH_Complete": 1,  # completed listings
        "_sop": 13,        # sort: recently ended first
        "_ipg": 60,        # results per page
    }
    r = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def parse_sold(html, min_price=5.0, max_comps=20):
    """Return a list of sold prices from an eBay sold-search page."""
    soup = BeautifulSoup(html, "html.parser")
    prices = []
    for item in soup.select("li.s-item"):
        price_el = item.select_one(".s-item__price")
        if not price_el:
            continue
        title_el = item.select_one(".s-item__title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if title.lower().startswith("shop on ebay"):
            continue  # eBay's placeholder first cell
        price = _first_price(price_el.get_text())
        if price is None or price < min_price:
            continue
        prices.append(price)
        if len(prices) >= max_comps:
            break
    return prices


def comps(query, min_price=5.0, max_comps=20):
    """Return a summary dict of eBay sold comps for `query`."""
    prices = parse_sold(fetch_sold(query), min_price=min_price, max_comps=max_comps)
    if not prices:
        return {"query": query, "n": 0, "median": None, "prices": []}
    return {
        "query": query,
        "n": len(prices),
        "median": round(statistics.median(prices), 2),
        "low": min(prices),
        "high": max(prices),
        "prices": prices,
    }
