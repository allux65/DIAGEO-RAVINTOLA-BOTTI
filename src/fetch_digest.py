"""
Hakee Diageo & Suomen ravintola-ala -uutiset Google News RSS:n kautta,
ja rakentaa niistä päivittyvän docs/index.html -sivun (GitHub Pages).
Tallentaa myös kaiken data/history.json-tiedostoon kuukausiyhteenvetoa varten.
"""
import feedparser
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape

BASE = Path(__file__).resolve().parent.parent
DOCS = BASE / "docs"
DATA_FILE = BASE / "data" / "history.json"

# Seurattavat yksittäiset brändit - muokkaa listaa vapaasti.
# Don Papa: Diageo on jakelija (ei omistaja) - silti relevantti työn kannalta.
BRANDS = [
    "Johnnie Walker", "Tanqueray", "Guinness", "Smirnoff", "Captain Morgan",
    "Ketel One", "Don Julio", "Casamigos", "Baileys", "Cîroc",
    "Roe & Co", "Caol Ila", "Bulleit", "Singleton", "Seedlip",
    "Pimm's", "Don Papa", "Santiago de Cuba",
]

# Muokkaa näitä hakuja vapaasti - jokainen on oma osio sivulla.
# hl/gl ohjaavat kieltä ja aluetta: fi/FI = suomenkieliset tulokset, en/US = globaalit tulokset.
QUERIES = {
    "Diageo Suomessa": {"q": '"Diageo" Suomi', "hl": "fi", "gl": "FI"},
    "Diageo maailmalla": {"q": '"Diageo"', "hl": "en", "gl": "US"},
    "Tarkkailtavat brändit": {
        "q": " OR ".join(f'"{b}"' for b in BRANDS),
        "hl": "en",
        "gl": "US",
    },
    "Kilpailijat": {
        "q": '"Pernod Ricard" OR "Bacardi" OR "Brown-Forman" OR "Suntory" OR "Campari Group"',
        "hl": "en",
        "gl": "US",
    },
    "Uudet ravintolat ja baarit Suomessa": {
        "q": '"uusi ravintola" OR "uusi baari" Suomi',
        "hl": "fi",
        "gl": "FI",
    },
    "Suomen ravintola-alan uutiset": {"q": "ravintola-ala Suomi", "hl": "fi", "gl": "FI"},
    "Cocktail-trendit maailmalla": {
        "q": "cocktail trends OR cocktail trend 2026",
        "hl": "en",
        "gl": "US",
    },
    "Väkevien alan uutiset ja ennusteet": {
        "q": "spirits industry news OR drinks industry forecast",
        "hl": "en",
        "gl": "US",
    },
    "Alan tapahtumat": {
        "q": "cocktail festival OR bar show OR drinks industry awards",
        "hl": "en",
        "gl": "US",
    },
}

DRINKS = [
    {"season": "talvi", "name": "Savustettu Old Fashioned",
     "note": "Lämmittävä, sopii pimeään kauteen ja joulun ympärille.",
     "base": "Viski 5cl", "mixer": "Siirappi, angostura", "finish": "Savustettu appelsiininkuori"},
    {"season": "talvi", "name": "Espresso Martini -variaatio",
     "note": "Ikivihreä, toimii erityisesti pimeän kauden ilta-annoksena.",
     "base": "Vodka 4cl, kahvilikööri 2cl", "mixer": "Tuore espresso", "finish": "Kolme kahvipapua"},
    {"season": "kevät", "name": "Yrttinen Gin Fizz",
     "note": "Kevyt ja raikas, hyödyntää kevään yrttejä listalla.",
     "base": "Gin 4cl", "mixer": "Sooda, sitruuna", "finish": "Tuore tilli tai minttu"},
    {"season": "kesä", "name": "Matala-alkoholinen spritz",
     "note": "Vastaa low/no-trendiin kesäterassilla ilman että makuprofiili kärsii.",
     "base": "Aperitiivi 3cl", "mixer": "Kuohuva, soodaa", "finish": "Appelsiiniviipale"},
    {"season": "kesä", "name": "Highball-klassikko",
     "note": "Japanilaistyylinen highball - kevyt ja helposti skaalattava terassikäyttöön.",
     "base": "Viski 4cl", "mixer": "Runsaasti soodaa", "finish": "Sitruunatwist"},
    {"season": "syksy", "name": "Savustettu Mule",
     "note": "Moscow Mulen syksyinen versio - helppo lisä listalle sellaisenaan.",
     "base": "Vodka 4cl", "mixer": "Inkiväärikaljaa, limeä", "finish": "Savustettu rosmariini"},
    {"season": "syksy", "name": "Omena-Old Fashioned",
     "note": "Syksyinen twist klassikkoon, sopii ruokalistan kausivaihtoon.",
     "base": "Viski 5cl", "mixer": "Omenasiirappi, angostura", "finish": "Kaneli"},
]

SEASON_BY_MONTH = {
    12: "talvi", 1: "talvi", 2: "talvi",
    3: "kevät", 4: "kevät", 5: "kevät",
    6: "kesä", 7: "kesä", 8: "kesä",
    9: "syksy", 10: "syksy", 11: "syksy",
}


def fetch_category(query, hl="fi", gl="FI", limit=6):
    ceid = f"{gl}:{hl}"
    url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl={hl}&gl={gl}&ceid={ceid}"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        source = ""
        if entry.get("source"):
            source = entry["source"].get("title", "")
        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": source,
            }
        )
    return items


def load_history():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_history(history):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=45)).timestamp()
    history = [h for h in history if h.get("fetched_at", 0) >= cutoff]
    DATA_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_drink():
    now = datetime.now(timezone.utc)
    season = SEASON_BY_MONTH[now.month]
    season_drinks = [d for d in DRINKS if d["season"] == season]
    week_num = now.isocalendar()[1]
    return season_drinks[week_num % len(season_drinks)]


def render_items(items):
    if not items:
        return '<p class="item-body">Ei tuoreita osumia tällä haulla juuri nyt.</p>'
    html = ""
    for it in items:
        title = escape(it["title"])
        link = escape(it["link"])
        meta = escape(f"{it['source']} · {it['published']}".strip(" ·"))
        html += f"""
        <div class="item">
          <div class="item-top">
            <span class="item-title"><a href="{link}" target="_blank" rel="noopener">{title}</a></span>
          </div>
          <p class="item-body">{meta}</p>
        </div>"""
    return html


def build_html(all_results, drink, updated_at):
    sections_html = ""
    for label, items in all_results.items():
        sections_html += f"""
        <section>
          <div class="section-head">
            <h2>{escape(label)}</h2>
            <span class="count">{len(items)} osumaa</span>
          </div>
          {render_items(items)}
        </section>"""

    drink_html = f"""
    <section>
      <div class="section-head"><h2>Drinkki-idea</h2></div>
      <div class="drink">
        <div class="drink-name">{escape(drink['name'])}</div>
        <p class="drink-note">{escape(drink['note'])}</p>
        <div class="drink-specs">
          <div><span>Pohja</span>{escape(drink['base'])}</div>
          <div><span>Lisäys</span>{escape(drink['mixer'])}</div>
          <div><span>Viimeistely</span>{escape(drink['finish'])}</div>
        </div>
      </div>
    </section>"""

    return f"""<!DOCTYPE html>
<html lang="fi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diageo & Ravintola-ala -briiffi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #1B1713; --bg-raised: #221D18; --ink: #EDE3D3; --ink-dim: #A99A86;
    --copper: #C08A4E; --line: #3A322A; --olive: #6B7355;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg); color: var(--ink);
    font-family: 'Work Sans', sans-serif; font-size: 16px; line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }}
  a {{ color: var(--ink); }}
  .wrap {{ max-width: 880px; margin: 0 auto; padding: 56px 24px 80px; }}
  header {{ border-bottom: 1px solid var(--line); padding-bottom: 32px; margin-bottom: 40px; }}
  .kicker {{ color: var(--copper); font-size: 14px; margin-bottom: 10px; }}
  h1 {{ font-family: 'Fraunces', serif; font-weight: 500; font-size: clamp(30px, 5vw, 44px); line-height: 1.1; max-width: 16ch; }}
  .subhead {{ color: var(--ink-dim); font-size: 16px; margin-top: 12px; max-width: 46ch; }}
  section {{ margin-bottom: 44px; }}
  .section-head {{ display: flex; align-items: baseline; justify-content: space-between; border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 18px; }}
  h2 {{ font-family: 'Fraunces', serif; font-weight: 500; font-size: 21px; }}
  .count {{ color: var(--ink-dim); font-size: 14px; }}
  .item {{ padding: 14px 0; border-bottom: 1px solid var(--line); }}
  .item:last-child {{ border-bottom: none; }}
  .item-title a {{ font-weight: 500; font-size: 16px; text-decoration: none; }}
  .item-title a:hover {{ color: var(--copper); }}
  .item-body {{ color: var(--ink-dim); font-size: 13.5px; margin-top: 4px; }}
  .drink {{ background: var(--bg-raised); border: 1px solid var(--line); border-left: 3px solid var(--copper); padding: 26px; }}
  .drink-name {{ font-family: 'Fraunces', serif; font-size: 24px; font-weight: 500; margin-bottom: 6px; }}
  .drink-note {{ color: var(--ink-dim); font-size: 14.5px; margin-bottom: 16px; max-width: 56ch; }}
  .drink-specs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; font-size: 14px; }}
  .drink-specs div span {{ display: block; color: var(--ink-dim); font-size: 12px; margin-bottom: 3px; }}
  footer {{ color: var(--ink-dim); font-size: 13px; border-top: 1px solid var(--line); padding-top: 20px; margin-top: 12px; }}
  @media (prefers-color-scheme: light) {{
    :root:not([data-theme="dark"]) {{
      --bg: #FBF8F2; --bg-raised: #F2ECE0; --ink: #24201A; --ink-dim: #6B6154;
      --copper: #9C6A34; --line: #E2D9C8; --olive: #6B7355;
    }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Päivitetty {escape(updated_at)}</div>
    <h1>Diageo & ravintola-ala -briiffi</h1>
    <p class="subhead">Automaattisesti koostettu tilannekuva brändiuutisista, ravintolakentän liikkeistä ja trendeistä.</p>
  </header>
  {sections_html}
  {drink_html}
  <footer>Lähde: Google News. Sivu päivittyy automaattisesti GitHub Actionsilla.</footer>
</div>
</body>
</html>"""


def main():
    all_results = {}
    history = load_history()
    now_ts = datetime.now(timezone.utc).timestamp()

    for label, spec in QUERIES.items():
        items = fetch_category(spec["q"], hl=spec["hl"], gl=spec["gl"])
        all_results[label] = items
        for it in items:
            already_seen = any(
                h["link"] == it["link"] and h.get("category") == label for h in history
            )
            if not already_seen:
                entry = dict(it)
                entry["category"] = label
                entry["fetched_at"] = now_ts
                history.append(entry)

    save_history(history)

    drink = pick_drink()
    updated_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    html = build_html(all_results, drink, updated_at)

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"Sivu päivitetty: {DOCS / 'index.html'}")


if __name__ == "__main__":
    main()
