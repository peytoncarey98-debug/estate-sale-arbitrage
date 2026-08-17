# estate-sale-arbitrage

Find collectible values in estate-sale auctions online.

This tool scans **HiBid.com** open auctions for the keywords on your watchlist,
prices each lot against recent **eBay sold listings**, and **emails you a digest**
of the lots whose likely resale value beats the current bid. It runs on your own
computer on a schedule.

## How it works

```
watchlist keywords
      │
      ▼
  HiBid search  ──►  for each lot  ──►  eBay "sold" comps  ──►  margin = median − bid
                                                                     │
                                              flag if ratio & margin clear thresholds
                                                                     │
                                                                     ▼
                                                        email digest (Gmail)
```

## Important notes before you start

- **Run it from your own machine, not a server.** HiBid and eBay block automated
  traffic by fingerprinting the HTTP client. The tool uses `curl_cffi` to
  impersonate a real Chrome browser, which gets past HiBid everywhere. eBay is
  stricter and also weighs IP reputation: it usually lets a **residential**
  connection (your home/office wifi) through but challenges datacenter/VPN IPs
  with a captcha. That's the main reason this runs locally, not in the cloud.
- **eBay comps can intermittently get blocked.** If eBay serves a captcha, the
  tool detects it, skips valuing that lot, and tells you at the end of the run
  instead of crashing. Run `python arb.py test-ebay "some item"` to see whether
  your connection is being let through.
- **It scrapes public pages.** eBay's true "sold" prices aren't in their free API,
  and HiBid has no public buyer API, so the tool reads public search-results
  pages. Keep the schedule modest (a few runs a day) to stay a polite guest.
- **Comps are an estimate.** A median of recent sold listings is a starting
  signal, not an appraisal. Always check condition, completeness, and shipping on
  the actual lot before bidding.

## Setup (one time)

You need Python 3.9+.

```bash
git clone https://github.com/peytoncarey98-debug/estate-sale-arbitrage.git
cd estate-sale-arbitrage

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# eBay valuation drives a real headless browser (Playwright). Install it:
playwright install chromium
# Linux / ChromeOS ONLY -- install Chromium's system libraries (macOS skips this):
sudo .venv/bin/playwright install-deps chromium

cp config.example.yaml config.yaml # then edit config.yaml (see below)
```

> **Why a browser for eBay?** HiBid is fetched with a fast lightweight client,
> but eBay blocks lightweight clients even from a home connection, so eBay pages
> are loaded through a real headless Chrome. That's what the two `playwright`
> commands above set up. HiBid needs none of it.

### Edit `config.yaml`

Set your **watchlist** keywords and **thresholds**. A lot is flagged only when
the eBay median is at least `min_value_ratio`× the current bid **and** the dollar
margin is at least `min_margin_dollars`. Start loose, then tighten.

### Set up Gmail for the email digest

Gmail needs an **app password** (not your normal password):

1. Turn on 2-Step Verification: https://myaccount.google.com/security
2. Create an app password: https://myaccount.google.com/apppasswords
   (name it "estate-arb") — you'll get a 16-character code.
3. Make the tool aware of it via environment variables:

```bash
export GMAIL_ADDRESS="peyton.carey98@gmail.com"
export GMAIL_APP_PASSWORD="the16charcode"
```

(These are read from the environment so your password is never stored in the
repo. For scheduling, put them in a `run.sh` wrapper — see below — which is
gitignored.)

## Try it out

```bash
# 1) Confirm the HiBid scraper sees lots (this is the calibration check):
python arb.py test-hibid "roseville pottery"

# 2) Confirm eBay comps come back:
python arb.py test-ebay "roseville pottery vase"

# 3) Full scan with NO email — writes digest_preview.html to open in a browser:
python arb.py run --dry-run

# 4) The real thing — scan and email the digest:
python arb.py run
```

**If `test-ebay` says "BLOCKED":** eBay is challenging your connection. It's
often intermittent — try again, or from a different network. **If it says it got
a real page but parsed 0 comps**, run `python arb.py test-ebay "roseville pottery vase" --dump`
and send me `ebay_dump.html` so I can match the parser to eBay's current markup.

**If `test-hibid` prints "0 lots parsed":** run
`python arb.py test-hibid "roseville pottery" --dump`, which saves
`hibid_dump.html`. Send me that file and I'll calibrate the parser to HiBid's
current markup — this is the one part I couldn't verify remotely because HiBid
blocks the environment I built it in.

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
(On macOS your Mac must be awake at those times. `pmset` or a laptop that's open
during the day is fine.)

**Windows (Task Scheduler)** — Create Task → Trigger: daily 8am/6pm → Action:
Start a program → `python`, arguments `arb.py run`, "Start in" set to the repo
folder. Put the two `set GMAIL_...` lines in a `run.bat` wrapper instead of the
`.sh` if you prefer.

## Running on more than one machine

Each machine is fully independent — nothing syncs automatically, which is the
point. On every computer that should run it (e.g. a Chromebook and a MacBook):

1. `git clone` the repo, make a venv, `pip install -r requirements.txt`.
2. `cp config.example.yaml config.yaml` and set that machine's own watchlist and
   `email.to`. Because `config.yaml` is gitignored, each person can have a
   different watchlist and recipient — or paste in the same one to match.
3. Set that machine's own `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` (each Gmail
   account needs its own app password).

**Which machine should run the schedule?** A machine that's reliably awake and
whose OS keeps cron/launchd running — a MacBook is a better fit than a Chromebook
(whose Linux container sleeps). Treat a Chromebook as a place for on-demand
`python arb.py run --dry-run` checks rather than the automated digest.

To pull the latest version of the tool on any machine later: `git pull`.

## Files

| File | What it does |
|------|--------------|
| `arb.py` | CLI entry point + arbitrage logic (`run`, `test-hibid`, `test-ebay`) |
| `hibid.py` | Scrapes HiBid open-auction lots |
| `ebay_comps.py` | Reads eBay sold prices and computes the median comp |
| `digest.py` | Builds the HTML digest and sends it via Gmail |
| `config.example.yaml` | Template config — copy to `config.yaml` |

## Roadmap ideas

- Track lots across runs so you only get alerted once per lot.
- Per-keyword thresholds (a Rolex and a Pyrex bowl want different rules).
- Add more sources (AuctionNinja, EstateSales.net) behind the same interface.
