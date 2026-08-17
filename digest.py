"""Build and send the HTML email digest of watchlist matches."""
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _money(v):
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "&mdash;"


def _row(lot):
    cell = 'style="padding:8px;border-top:1px solid #eee"'
    rcell = 'style="padding:8px;border-top:1px solid #eee;text-align:right;white-space:nowrap"'
    ebay = lot.get("ebay_url", "#")
    return f"""<tr>
      <td {cell}><a href="{lot['url']}">{_esc(lot['title'])}</a></td>
      <td {rcell}>{_money(lot.get('current_bid'))}</td>
      <td {rcell}>{lot.get('bid_count') if lot.get('bid_count') is not None else '&mdash;'}</td>
      <td {rcell}>{_esc(lot.get('time_left') or '&mdash;')}</td>
      <td {rcell}><a href="{ebay}">eBay sold &rarr;</a></td>
    </tr>"""


def _section(keyword, lots):
    head = (
        '<tr style="text-align:left;background:#f4f4f4">'
        '<th style="padding:8px">Lot (HiBid)</th>'
        '<th style="padding:8px;text-align:right">Bid</th>'
        '<th style="padding:8px;text-align:right">Bids</th>'
        '<th style="padding:8px;text-align:right">Time left</th>'
        '<th style="padding:8px;text-align:right">Value check</th></tr>'
    )
    if not lots:
        body = ('<tr><td style="padding:8px;color:#999" colspan="5">'
                'No matching lots right now.</td></tr>')
    else:
        body = "".join(_row(l) for l in lots)
    return f"""<h3 style="margin:22px 0 6px">{_esc(keyword)} &mdash; {len(lots)}</h3>
      <table style="border-collapse:collapse;width:100%;font:14px system-ui,Arial">
        <thead>{head}</thead><tbody>{body}</tbody></table>"""


def build_html(results, cfg):
    total = sum(len(v) for v in results.values())
    sections = "".join(_section(kw, lots) for kw, lots in results.items())
    return f"""<div style="font:14px system-ui,Arial;color:#222;max-width:860px">
      <h2 style="margin:0 0 4px">Estate-Sale Watchlist &mdash; {total} lots to check</h2>
      <p style="color:#666;margin:0 0 8px">
        Open HiBid lots matching your watchlist. Click <b>eBay sold &rarr;</b> on any
        row to see recent sold prices for that item and judge whether the current
        bid is a deal.
      </p>
      {sections}
      <p style="color:#999;font-size:12px;margin-top:20px">
        Always check condition, completeness, and shipping on the actual lot
        before bidding. Sold comps are a starting point, not an appraisal.
      </p>
    </div>"""


def send(html, subject, to_addr):
    """Send the digest via Gmail SMTP. Credentials come from the environment."""
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        raise SystemExit(
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables "
            "(a Gmail app password) to send email, or use `run --dry-run`."
        )
    if not to_addr:
        raise SystemExit("No recipient set. Add email.to in config.yaml.")

    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg["Date"] = formatdate(localtime=True)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(user, pw)
        s.sendmail(user, [to_addr], msg.as_string())
