"""Build and send the HTML email digest of flagged arbitrage lots."""
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(v):
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "&mdash;"


def _ratio(r):
    if r is None:
        return "&mdash;"
    return "&infin;" if r == float("inf") else f"{r:.1f}x"


def _row(d):
    lot, comp = d["lot"], d["comps"]
    cell = 'style="padding:8px;border-top:1px solid #eee"'
    rcell = 'style="padding:8px;border-top:1px solid #eee;text-align:right"'
    median_cell = f"${_num(comp.get('median'))}"
    if comp.get("url"):  # link the median to the eBay sold search behind it
        median_cell = f'<a href="{comp["url"]}">{median_cell}</a>'
    return f"""<tr>
      <td {cell}><a href="{lot['url']}">{_esc(lot['title'])}</a></td>
      <td {rcell}>${_num(lot.get('current_bid'))}</td>
      <td {rcell}>{median_cell}</td>
      <td {rcell}><b>${_num(d.get('margin'))}</b></td>
      <td {rcell}>{_ratio(d.get('ratio'))}</td>
      <td {rcell}>{comp.get('n', 0)}</td>
    </tr>"""


def build_html(flagged, scanned_count, keywords):
    if flagged:
        head = (
            '<tr style="text-align:left;background:#f4f4f4">'
            '<th style="padding:8px">Lot (HiBid)</th>'
            '<th style="padding:8px;text-align:right">Cur. bid</th>'
            '<th style="padding:8px;text-align:right">eBay median</th>'
            '<th style="padding:8px;text-align:right">Margin</th>'
            '<th style="padding:8px;text-align:right">Ratio</th>'
            '<th style="padding:8px;text-align:right"># comps</th></tr>'
        )
        rows = "".join(_row(d) for d in flagged)
        table = (
            '<table style="border-collapse:collapse;width:100%;'
            'font:14px system-ui,Arial">'
            f"<thead>{head}</thead><tbody>{rows}</tbody></table>"
        )
    else:
        table = "<p>No lots cleared the thresholds this run.</p>"

    return f"""<div style="font:14px system-ui,Arial;color:#222;max-width:820px">
      <h2 style="margin:0 0 4px">Estate-Sale Arbitrage &mdash; {len(flagged)} flagged</h2>
      <p style="color:#666;margin:0 0 16px">
        Scanned {scanned_count} HiBid lots across {len(keywords)} keywords.
        Margin = eBay median sold price &minus; current bid.
      </p>
      {table}
      <p style="color:#999;font-size:12px;margin-top:20px">
        Comps are recent eBay <em>sold</em> listings. Always verify item
        condition, completeness, and shipping before bidding.
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
