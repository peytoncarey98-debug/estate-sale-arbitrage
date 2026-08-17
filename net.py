"""Browser-impersonating HTTP.

Plain `requests` gets blocked (HTTP 403 / captcha) by HiBid and eBay because
they fingerprint the TLS/HTTP2 signature of the client -- a normal Python
request doesn't look like a browser, no matter what IP it comes from. curl_cffi
impersonates a real Chrome signature, which gets past HiBid entirely and past
eBay from a normal residential connection.
"""
from curl_cffi import requests as _cffi

IMPERSONATE = "chrome"


def session(warmup=None, timeout=30):
    """Return a browser-impersonating session.

    If `warmup` is given, hit that URL first to collect cookies (eBay hands out
    a session cookie on the homepage that its search endpoint expects).
    """
    s = _cffi.Session(impersonate=IMPERSONATE)
    if warmup:
        try:
            s.get(warmup, timeout=timeout)
        except Exception:
            pass  # warm-up is best-effort; the real request still tries
    return s
