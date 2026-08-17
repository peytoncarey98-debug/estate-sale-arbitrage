# estate-sale-arbitrage

Find collectible values in estate-sale auctions online.

This tool scans **HiBid.com** open auctions for the keywords on your watchlist
and **emails you a digest** of matching lots — each with its current bid, number
of bids, time left, a link to the lot, and a **one-click link to eBay's sold
listings** so you can eyeball resale value and spot underpriced items. It runs on
your own computer on a schedule.

## How it works

```
watchlist keywords ─► HiBid search ─► filter (cheap enough?) + sort ─► email digest
                                                                          │
                                        each lot links to its eBay SOLD comps
```

### Why eBay value isn't automatic

eBay blocks automated access to sold prices (that data sits behind their paid
Marketplace Insights API), and it blocks scraping hard — even a real browser from
a home connection gets refused. Rather than fight that, the digest gives you a
**one-click link to eBay's sold search for each lot**, so judging value takes a
couple of seconds per item. Automating it later is possible — see *Roadmap*.

## Important: run it from a normal home connection

HiBid blocks traffic that looks non-residential. In testing, an **office/VPN
network returned nothing**, while **home wifi and a phone hotspot worked
perfectly**. So run this on a machine connected to ordinary home internet — not a
corporate network or VPN.

## Setup (one time)

You need Python 3.9+.

```bash
git clone https://github.com/peytoncarey98-debug/estate-sale-arbitrage.git
cd estate-sale-arbitrage

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp config.example.yaml config.yaml # then edit config.yaml (see below)
```

### Edit `config.yaml`

| Setting | What it does |
|---------|--------------|
| `watchlist` | The keywords to search HiBid for. One search each. |
| `hibid_pages_per_keyword` | Pages to scan per keyword (~100 lots/page). |
| `max_current_bid` | Only include lots at/below this bid (arbitrage = still cheap). `null` = no cap. |
| `max_lots_per_keyword` | How many lots per keyword to put in the email. |
| `sort_by` | `ending_soon`, `lowest_bid`, or `fewest_bids`. |

### Set up Gmail for the email digest

Gmail needs an **app password** (not your normal password):

1. Turn on 2-Step Verification: https://myaccount.google.com/security
2. Create an app password: https://myaccount.google.com/apppasswords
   (name it "estate-arb") — you'll get a 16-character code.
3. Provide it via environment variables (never stored in the repo):

```bash
export GMAIL_ADDRESS="peyton.carey98@gmail.com"
export GMAIL_APP_PASSWORD="the16charcode"
```

## Try it out

```bash
# 1) Confirm the HiBid scraper sees lots:
python arb.py test-hibid "roseville pottery"

# 2) Full scan with NO email — writes digest_preview.html to open in a browser:
python arb.py run --dry-run

# 3) The real thing — scan and email the digest:
python arb.py run
```

**If `test-hibid` prints "0 lots parsed":** you're probably on a blocked network
(office/VPN) — try home wifi or a phone hotspot. If it still fails on a clean
connection, run `python arb.py test-hibid "roseville pottery" --dump` and send me
`hibid_dump.html`.

## Schedule it to run automatically

Create a `run.sh` next to `arb.py` (it's gitignored, so your password stays
private):

```bash
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export GMAIL_ADDRESS="peyton.carey98@gmail.com"
export GMAIL_APP_PASSWORD="the16charcode"
python arb.py run >> arb.log 2>&1
```

`chmod +x run.sh`, then:

**macOS / Linux (cron)** — run at 8am and 6pm daily. `crontab -e`, add:
```
0 8,18 * * * /full/path/to/estate-sale-arbitrage/run.sh
```
The machine must be **awake and on home wifi** at those times — a MacBook that's
open during the day is ideal.

**Windows (Task Scheduler)** — Create Task → daily trigger → Action: run
`python arb.py run` with "Start in" set to the repo folder (use a `run.bat`
wrapper for the `GMAIL_...` variables).

## Running on more than one machine

Each machine is independent. On every computer (e.g. a Chromebook and a MacBook):
clone the repo, make a venv, `pip install -r requirements.txt`, copy
`config.example.yaml` to `config.yaml` and set its own watchlist + `email.to`, and
set its own `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`. Because `config.yaml` is
gitignored, each person can have a different watchlist. Put the automated schedule
on the machine that's reliably awake on home wifi (a MacBook beats a Chromebook,
whose Linux container sleeps). `git pull` updates the tool on any machine.

## Files

| File | What it does |
|------|--------------|
| `arb.py` | CLI + watchlist logic (`run`, `test-hibid`) |
| `hibid.py` | Scrapes HiBid open-auction lots |
| `net.py` | Browser-impersonating HTTP so HiBid doesn't block us |
| `ebay_comps.py` | Builds eBay sold-listing search links |
| `digest.py` | Builds the HTML digest and sends it via Gmail |
| `config.example.yaml` | Template config — copy to `config.yaml` |

## Roadmap

- **Automated eBay valuation** (optional, later): via eBay's free official API
  (reliable, but current asking prices rather than sold), or a paid scraping
  service (true sold comps, hands-off). The digest's per-lot links are the manual
  version of this.
- Track lots across runs so you're only alerted once per lot.
- Add more sources (AuctionNinja, EstateSales.net) behind the same interface.
