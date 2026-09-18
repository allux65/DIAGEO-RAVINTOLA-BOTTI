"""
Kokoaa data/history.json:sta viimeisen 30 päivän tapahtumat kategorioittain
ja lähettää ne kuukausiyhteenvetona sähköpostiin.
Käyttää samaa Gmail-sovellussalasana-mallia kuin lentohakubotti.
"""
import json
import os
import smtplib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from email.mime.text import MIMEText

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "history.json"


def load_month_items():
    if not DATA_FILE.exists():
        return {}
    history = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    grouped = {}
    for h in history:
        if h.get("fetched_at", 0) >= cutoff:
            grouped.setdefault(h["category"], []).append(h)
    return grouped


def build_email_body(grouped):
    month_name = datetime.now().strftime("%B %Y")
    lines = [f"Kuukausiyhteenveto — Diageo & ravintola-ala ({month_name})", ""]

    if not grouped:
        lines.append("Ei kerättyä dataa tältä kuukaudelta. Tarkista että update-site.yml on ajanut ainakin kerran.")
        return "\n".join(lines)

    for category, items in grouped.items():
        lines.append(f"\n== {category} ==")
        seen_titles = set()
        for it in items:
            if it["title"] in seen_titles:
                continue
            seen_titles.add(it["title"])
            lines.append(f"- {it['title']}")
            if it.get("source"):
                lines.append(f"  ({it['source']})")
            lines.append(f"  {it['link']}")

    lines.append("\n---")
    lines.append("Koko sivu ja viimeisimmät päivitykset: [lisää tähän GitHub Pages -osoitteesi]")
    return "\n".join(lines)


def send_email(body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Kuukausiyhteenveto — Diageo & ravintola-ala ({datetime.now().strftime('%B %Y')})"
    msg["From"] = os.environ["EMAIL_ADDRESS"]
    msg["To"] = os.environ["EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_APP_PASSWORD"])
        server.send_message(msg)


def main():
    grouped = load_month_items()
    body = build_email_body(grouped)
    send_email(body)
    print("Kuukausiyhteenveto lähetetty.")


if __name__ == "__main__":
    main()
