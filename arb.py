#!/usr/bin/env python3
"""Estate-sale arbitrage scanner.

Scans HiBid open auctions for your watchlist keywords, values each lot against
recent eBay sold comps, flags lots whose likely resale value beats the current
bid, and emails you a digest.

Usage:
  python arb.py test-hibid "roseville pottery"   # sanity-check the HiBid scraper
  python arb.py test-ebay  "roseville vase"       # sanity-check the eBay comps
  python arb.py run --dry-run                       # full scan, preview, no email
  python arb.py run                                  # full scan, email the digest
"""
import argparse
import os
import re
import sys
import time

import yaml

import digest
import ebay_comps
import hibid


def load_config(path="config.yaml"):
    if not os.path.exists(path):
        sys.exit(f"Missing {path}. Copy config.example.yaml to config.yaml and edit it.")
    with open(path) as f:
        return yaml.safe_load(f)


def clean_query(title):
    """Trim lot numbers / punctuation so eBay comps match the item itself."""
    t = re.sub(r"lot\s*#?\s*\d+", " ", title, flags=re.I)
    t = re.sub(r"\b[A-Za-z]?\d{2,}-\d+\b", " ", t)  # model numbers like 72-6
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(t.split()[:8])  # first ~8 words is plenty for a comp search


def evaluate(lot, cfg):
    """Attach eBay comps + margin/ratio to a single HiBid lot."""
    ecfg = cfg.get("ebay", {})
    comp = ebay_comps.comps(
        clean_query(lot["title"]),
        min_price=ecfg.get("min_comp_price", 5),
        max_comps=ecfg.get("max_comps", 20),
    )
    bid = lot.get("current_bid")
    res = {"lot": lot, "comps": comp, "margin": None, "ratio": None}
    if comp["median"]:
        if bid and bid > 0:
            res["margin"] = round(comp["median"] - bid, 2)
            res["ratio"] = comp["median"] / bid
        else:  # no bids yet -- the whole median is upside
            res["margin"] = comp["median"]
            res["ratio"] = float("inf")
    return res


def is_flagged(res, cfg):
    th = cfg.get("thresholds", {})
    if res["margin"] is None or res["ratio"] is None:
        return False
    return (
        res["ratio"] >= th.get("min_value_ratio", 3.0)
        and res["margin"] >= th.get("min_margin_dollars", 40)
    )


def cmd_run(cfg, dry_run):
    keywords = cfg.get("watchlist", [])
    pages = cfg.get("hibid_pages_per_keyword", 2)
    scanned, flagged = 0, []

    for kw in keywords:
        try:
            lots = hibid.search(kw, pages=pages)
        except Exception as e:
            print(f"  ! HiBid search failed for {kw!r}: {e}")
            continue
        print(f"  {kw!r}: {len(lots)} lots")
        for lot in lots:
            scanned += 1
            try:
                res = evaluate(lot, cfg)
            except Exception as e:
                print(f"    ! eBay lookup failed for {lot['title'][:40]!r}: {e}")
                continue
            if is_flagged(res, cfg):
                flagged.append(res)
                print(f"    * ${res['margin']} margin: {lot['title'][:60]}")
            time.sleep(1.0)  # be polite to eBay

    flagged.sort(key=lambda r: r["margin"], reverse=True)
    html = digest.build_html(flagged, scanned, keywords)
    prefix = cfg.get("email", {}).get("subject_prefix", "[Estate Arb]")
    subject = f"{prefix} {len(flagged)} deals ({scanned} scanned)"

    if dry_run:
        with open("digest_preview.html", "w") as f:
            f.write(html)
        print(f"\nDRY RUN: {len(flagged)} flagged of {scanned} scanned.")
        print("Wrote digest_preview.html -- open it in a browser to preview the email.")
    else:
        digest.send(html, subject, cfg.get("email", {}).get("to"))
        print(f"\nEmailed {len(flagged)} deals to {cfg.get('email', {}).get('to')}.")


def cmd_test_hibid(query, dump):
    lots = hibid.search(query, pages=1)
    print(f"Parsed {len(lots)} lots for {query!r}:")
    for lot in lots[:15]:
        print(f"  ${lot.get('current_bid')}  ({lot.get('bid_count')} bids)  {lot['title'][:70]}")
        print(f"     {lot['url']}")
    if not lots and dump:
        with open("hibid_dump.html", "w") as f:
            f.write(hibid.fetch(query))
        print("0 lots parsed -- wrote hibid_dump.html so the parser can be calibrated.")


def cmd_test_ebay(query):
    c = ebay_comps.comps(query)
    print(f"eBay sold comps for {query!r}: n={c['n']} median=${c['median']}")
    if c["n"]:
        print(f"  range ${c['low']}-${c['high']}")
        print(f"  prices: {c['prices']}")


def main():
    ap = argparse.ArgumentParser(description="Estate-sale arbitrage scanner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="scan the watchlist and email the digest")
    p_run.add_argument("--dry-run", action="store_true", help="preview to a file instead of emailing")

    p_h = sub.add_parser("test-hibid", help="check the HiBid scraper for one keyword")
    p_h.add_argument("query")
    p_h.add_argument("--dump", action="store_true", help="save raw HTML if 0 lots parse")

    p_e = sub.add_parser("test-ebay", help="check eBay sold comps for one query")
    p_e.add_argument("query")

    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(load_config(), args.dry_run)
    elif args.cmd == "test-hibid":
        cmd_test_hibid(args.query, args.dump)
    elif args.cmd == "test-ebay":
        cmd_test_ebay(args.query)


if __name__ == "__main__":
    main()
