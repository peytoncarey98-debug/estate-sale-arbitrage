"""Render a page with a real headless Chromium (Playwright).

eBay rejects lightweight HTTP clients (curl_cffi included) even from a clean
residential IP, so eBay pages go through an actual browser that runs the site's
JavaScript and looks like a human visitor. HiBid does NOT need this -- it stays
on the fast curl_cffi path in net.py.

The browser is launched once and reused across all lookups in a run; call
shutdown() when done.
"""
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Trim the most obvious "I'm automated" tells before any page script runs.
_STEALTH = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"

_pw = None
_browser = None


def _ensure():
    global _pw, _browser
    if _browser is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
    return _browser


def render(url, wait_for=None, timeout=30000):
    """Return the fully-rendered HTML of `url`.

    If `wait_for` (a CSS selector) is given, wait up to a few seconds for it to
    appear before grabbing the HTML; otherwise just give scripts a moment.
    """
    browser = _ensure()
    ctx = browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900},
                              locale="en-US")
    ctx.add_init_script(_STEALTH)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        if wait_for:
            try:
                page.wait_for_selector(wait_for, timeout=6000)
            except Exception:
                pass  # results never showed (empty search or a block page)
        else:
            page.wait_for_timeout(1500)
        return page.content()
    finally:
        ctx.close()


def shutdown():
    """Close the shared browser. Safe to call more than once."""
    global _pw, _browser
    if _browser is not None:
        try:
            _browser.close()
        finally:
            _browser = None
    if _pw is not None:
        try:
            _pw.stop()
        finally:
            _pw = None
