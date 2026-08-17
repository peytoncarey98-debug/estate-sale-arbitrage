# Lot Scout

A small hosted web app that finds underpriced collectible lots on **HiBid**
auctions and values them against **eBay**. Open a link, edit your watchlist by
clicking, hit **Scan**, and get lots ranked by how far under estimated value the
current bid is — as cards or a dense list. No install for the people using it.

- **HiBid** is scanned server-side (browser-impersonating fetch; no eBay-style blocking).
- **eBay valuation** uses eBay's **official Browse API** — sanctioned, never captcha-blocked, works from a server. It reports the median current *asking* price as a value signal.
- **Stateless backend**: your watchlist lives in the browser and is sent with each scan, so there's no database and moving hosts is trivial.

## Deploy it free (Render)

1. Push this repo to GitHub (already done) and create a free account at **render.com**.
2. In Render: **New → Blueprint**, connect this repository. Render reads
   `render.yaml` and configures everything.
3. Set the environment variables it asks for:
   - **`APP_PASSWORD`** — the shared password you and your girlfriend type to open the site. Pick anything.
   - `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` — optional now; add them to turn on value estimates (see below). The app runs fine without them (each lot still links to its eBay sold search).
   - `SECRET_KEY` is generated automatically — leave it.
4. Click **Apply / Deploy**. In a few minutes you get a URL like
   `https://lot-scout.onrender.com`. Open it, enter your password, and scan.

> On Render's free plan the site "sleeps" after ~15 min idle, so the first visit
> after a while takes ~30–60s to wake. That's the only free-tier catch.

## Turn on value estimates — the free eBay API key

1. Sign up (free) at **developer.ebay.com** and sign in.
2. Go to **Your Account → Application Keysets**.
3. Under **Production** (not Sandbox), create a keyset. Copy:
   - **App ID (Client ID)** → `EBAY_CLIENT_ID`
   - **Cert ID (Client Secret)** → `EBAY_CLIENT_SECRET`
4. Paste those two into Render's environment variables and redeploy.

The app uses the Browse API's app-token flow — no buyer login or approval needed
for basic search, and the free rate limits are far more than this app will use.

## Moving to Railway later (when you want always-on)

Because the backend is stateless, migrating is: create a Railway project from the
same GitHub repo, copy the same environment variables over, deploy. Nothing to
export, no data to lose. Railway stays awake (no cold-start), for a few $/month.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: export EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... to test valuation
python app.py           # http://127.0.0.1:5000  (no password locally)
```

## How it works / files

| File | Role |
|------|------|
| `app.py` | Flask app: routes, auth, `/api/scan` (HiBid + eBay → JSON) |
| `templates/index.html` | The UI (watchlist, scan, cards/list, value + signals) |
| `templates/login.html` | Password gate |
| `hibid.py` | Scrapes HiBid open-auction lots |
| `net.py` | Browser-impersonating HTTP so HiBid doesn't block us |
| `ebay_api.py` | eBay Browse API client — value estimate from live listings |
| `ebay_comps.py` | Builds eBay sold-listing search links |
| `render.yaml`, `Procfile` | Deployment config |

`arb.py` / `digest.py` remain from the earlier command-line version and are kept
for a future scheduled-email feature; the web app doesn't use them.

## Notes

- **Run the server on a host HiBid allows.** HiBid blocked a corporate/VPN network
  in testing but works from normal connections and cloud hosts. If a scan returns
  a HiBid error, that's the thing to check.
- **Est. value is an asking-price signal, not a sold price** — eBay's true sold
  data is behind their paid API. Treat estimates as a starting point; the per-lot
  eBay sold link is there to confirm.

## Roadmap

- Scheduled email digest (needs the always-on host + a little persistence).
- Track lots across scans so you only see each once.
- More auction sources (AuctionNinja, EstateSales.net) — the UI is already source-aware.
