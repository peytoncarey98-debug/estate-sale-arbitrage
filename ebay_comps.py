"""Build eBay 'sold listings' search URLs for manual price checks.

We don't scrape eBay -- it blocks automated access to sold prices (that data is
behind their paid Marketplace Insights API). Instead the digest links each lot
to eBay's sold-listings search, so you can eyeball recent comps in one click.
"""
import urllib.parse

SEARCH_URL = "https://www.ebay.com/sch/i.html"


def sold_url(query):
    """URL for eBay sold/completed listings, newest first."""
    q = urllib.parse.urlencode({"_nkw": query, "LH_Sold": 1, "LH_Complete": 1, "_sop": 13})
    return f"{SEARCH_URL}?{q}"
