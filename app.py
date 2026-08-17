"""Lot Scout -- web app.

Scans HiBid for a watchlist and values each lot against the eBay API.
Stateless backend: the watchlist lives in the browser and is sent with each
scan, so there's no database and the app deploys (and moves hosts) trivially.

Environment:
  SECRET_KEY          Flask session key (set to anything random in production)
  APP_PASSWORD        shared password to reach the app (if unset, no login -- dev only)
  EBAY_CLIENT_ID      free eBay developer App ID   (optional; enables value estimates)
  EBAY_CLIENT_SECRET  free eBay developer Cert ID  (optional)
"""
import functools
import os

from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for)

import ebay_api
import ebay_comps
import hibid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
PASSWORD = os.environ.get("APP_PASSWORD")  # None => no auth (local dev)

MAX_KEYWORDS = 25
MAX_LOTS_PER_KEYWORD = 24


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if PASSWORD and not session.get("ok"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "auth"}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def _grade(bid, est):
    """Signal for a lot given its bid and estimated value."""
    if not est or not bid:
        return None
    ratio = est / bid
    margin = est - bid
    if ratio >= 3 and margin >= 40:
        return "hot"
    if ratio >= 1.8:
        return "good"
    return "watch"


def _build_lot(lot):
    """Shape a HiBid lot (+ eBay estimate) into the JSON the UI expects."""
    title = lot["title"]
    bid = lot.get("current_bid")
    est_info = ebay_api.estimate(hibid.clean_title(title)) if ebay_api.available() else None
    est = est_info["value"] if est_info else None
    margin = round(est - bid, 2) if (est is not None and bid is not None) else None
    return {
        "title": title,
        "lot": lot.get("id"),
        "url": lot.get("url"),
        "source": "HiBid",
        "bid": bid,
        "bids": lot.get("bid_count"),
        "timeLeft": lot.get("time_left"),
        "mins": lot.get("end_minutes"),
        "est": est,
        "estCount": est_info["n"] if est_info else None,
        "margin": margin,
        "signal": _grade(bid, est),
        "ebayUrl": ebay_comps.sold_url(hibid.clean_title(title)),
    }


@app.get("/login")
def login():
    return render_template("login.html", error=None)


@app.post("/login")
def do_login():
    if not PASSWORD or request.form.get("password") == PASSWORD:
        session["ok"] = True
        return redirect(url_for("index"))
    return render_template("login.html", error="That password didn't match."), 401


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return render_template("index.html", ebay_on=ebay_api.available(),
                           auth_on=bool(PASSWORD))


@app.post("/api/scan")
@login_required
def scan():
    data = request.get_json(force=True, silent=True) or {}
    watch = [w.strip() for w in data.get("watchlist", []) if w and w.strip()][:MAX_KEYWORDS]
    cap = min(int(data.get("cap", 20) or 20), MAX_LOTS_PER_KEYWORD)
    try:
        max_bid = float(data["maxBid"]) if data.get("maxBid") not in (None, "") else None
    except (TypeError, ValueError):
        max_bid = None

    results = []
    for kw in watch:
        try:
            lots = hibid.search(kw, pages=1)
        except Exception as e:
            results.append({"keyword": kw, "error": f"HiBid fetch failed: {e}", "lots": []})
            continue
        if max_bid is not None:
            lots = [l for l in lots if (l.get("current_bid") or 0) <= max_bid]
        lots = lots[:cap]
        results.append({"keyword": kw, "lots": [_build_lot(l) for l in lots]})

    return jsonify({"results": results, "ebayOn": ebay_api.available()})


@app.get("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
