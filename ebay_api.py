"""eBay Browse API client -- estimates an item's value from live listings.

This is eBay's OFFICIAL, sanctioned API (no scraping, never captcha-blocked, works
fine from a server). Auth is the OAuth2 client-credentials flow; you need a free
eBay developer keyset in the environment:

    EBAY_CLIENT_ID       (your App ID / Client ID)
    EBAY_CLIENT_SECRET   (your Cert ID / Client Secret)

Note: the free Browse API returns CURRENT listings (asking prices), not final sold
prices -- so the estimate is a market asking-price signal, which runs a bit high.
We use the median of fixed-price ("Buy It Now") listings as the value estimate.
"""
import base64
import os
import statistics
import time

import requests

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

_token = {"val": None, "exp": 0.0}
_cache = {}                 # query -> (timestamp, result)
CACHE_TTL = 6 * 3600        # re-price the same query at most every 6 hours


def _creds():
    return os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")


def available():
    cid, cs = _creds()
    return bool(cid and cs)


def _get_token():
    if _token["val"] and time.time() < _token["exp"] - 60:
        return _token["val"]
    cid, cs = _creds()
    if not (cid and cs):
        return None
    auth = base64.b64encode(f"{cid}:{cs}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    _token["val"] = j["access_token"]
    _token["exp"] = time.time() + int(j.get("expires_in", 7200))
    return _token["val"]


def estimate(query, limit=50, min_price=5.0):
    """Return {'value','n','low','high'} for `query`, or None if unavailable."""
    now = time.time()
    hit = _cache.get(query)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    result = None
    try:
        tok = _get_token()
        if tok:
            r = requests.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {tok}",
                         "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
                params={"q": query, "limit": limit,
                        "filter": "buyingOptions:{FIXED_PRICE}"},
                timeout=20,
            )
            if r.status_code == 200:
                prices = []
                for it in r.json().get("itemSummaries", []) or []:
                    val = (it.get("price") or {}).get("value")
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        continue
                    if val >= min_price:
                        prices.append(val)
                if prices:
                    prices.sort()
                    result = {"value": round(statistics.median(prices), 2),
                              "n": len(prices), "low": prices[0], "high": prices[-1]}
    except Exception:
        result = None  # never let a valuation hiccup break a scan

    _cache[query] = (now, result)
    return result
