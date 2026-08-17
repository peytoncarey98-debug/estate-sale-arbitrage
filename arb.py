#!/usr/bin/env python3
"""Estate-sale watchlist scanner.

Scans HiBid open auctions for your watchlist keywords and emails you a digest of
matching lots -- current bid, bids, time left, a link to the lot, and a one-click
link to eBay's SOLD listings so you can eyeball resale value.

(eBay blocks automated price scraping, so valuation is one click away rather than
computed for you. See README for why, and options to automate it later.)

Usage:
  python arb.py test-hibid "roseville pottery"   # check the HiBid scraper
  python arb.py run --dry-run                       # scan + preview to a file
  python arb.py run                                  # scan + email the digest
"""
import argparse
import os
import sys

import yaml

import digest
import ebay_comps
import hibid

# How to order lots within each keyword section of the digest.
SORTERS = {
    "ending_soon": lambda l: l.get("end_minutes") if l.get("end_minutes") is not None else 10**12,
    "lowest_bid": lambda l: l.get("current_bid") if l.get("current_bid") is not None else 10**12,
    "fewest_bids": lambda l: l.get("bid_count") if l.get("bid_count") is not None else 10**12,
}


def load_config(path="config.yaml"):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}. Copy config.example.yaml to config.yaml and edit it.")
    with open(path) as f:
        return yaml.safe_load(f)


def collect(cfg):
    """Return {keyword: [lot, ...]} of watchlist matches, filtered and sorted."""
    pages = cfg.get("hibid_pages_per_keyword", 2)
    cap = cfg.get("max_lots_per_keyword", 15)
    max_bid = cfg.get("max_current_bid")  # None -> no cap
    sorter = SORTERS.get(cfg.get("sort_by", "ending_soon"), SORTERS["ending_soon"])

    results = {}
    for kw in cfg.get("watchlist", []):
        try:
            lots = hibid.search(kw, pages=pages)
        except Exception as e:
            print(f"  ! HiBid search failed for {kw!r}: {e}")
            results[kw] = []
            continue
        if max_bid is not None:
            lots = [l for l in lots if (l.get("current_bid") or 0) <= max_bid]
        lots.sort(key=sorter)
        lots = lots[:cap]
        for l in lots:
            l["ebay_url"] = ebay_comps.sold_url(hibid.clean_title(l["title"]))
        results[kw] = lots
        print(f"  {kw!r}: {len(lots)} lots (after filters)")
    return results


def cmd_run(cfg, dry_run):
    results = collect(cfg)
    total = sum(len(v) for v in results.values())
    html = digest.build_html(results, cfg)
    prefix = cfg.get("email", {}).get("subject_prefix", "[Estate Watch]")
    subject = f"{prefix} {total} lots to check"

    if dry_run:
        with open("digest_preview.html", "w") as f:
            f.write(html)
        print(f"\nDRY RUN: {total} lots across {len(results)} keywords.")
        print("Wrote digest_preview.html -- open it in a browser to preview the email.")
    else:
        digest.send(html, subject, cfg.get("email", {}).get("to"))
        print(f"\nEmailed {total} lots to {cfg.get('email', {}).get('to')}.")


def cmd_test_hibid(query, dump):
    lots = hibid.search(query, pages=1)
    print(f"Parsed {len(lots)} lots for {query!r}:")
    for lot in lots[:15]:
        print(f"  ${lot.get('current_bid')}  ({lot.get('bid_count')} bids, {lot.get('time_left')})  {lot['title'][:60]}")
        print(f"     {lot['url']}")
    if not lots and dump:
        with open("hibid_dump.html", "w") as f:
            f.write(hibid.fetch(query))
        print("0 lots parsed -- wrote hibid_dump.html so the parser can be calibrated.")


def main():
    ap = argparse.ArgumentParser(description="Estate-sale watchlist scanner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="scan the watchlist and email the digest")
    p_run.add_argument("--dry-run", action="store_true", help="preview to a file instead of emailing")

    p_h = sub.add_parser("test-hibid", help="check the HiBid scraper for one keyword")
    p_h.add_argument("query")
    p_h.add_argument("--dump", action="store_true", help="save raw HTML if 0 lots parse")

    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(load_config(), args.dry_run)
    elif args.cmd == "test-hibid":
        cmd_test_hibid(args.query, args.dump)


if __name__ == "__main__":
    main()
