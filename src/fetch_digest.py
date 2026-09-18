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
from email.utils import parsedate_to_datetime

BASE = Path(__file__).resolve().parent.parent
DOCS = BASE / "docs"
DATA_FILE = BASE / "data" / "history.json"

FINNISH_MONTHS_SHORT = None  # placeholder, we use numeric dd.mm. format instead

# Väripiste per kategoria - kulta/pronssi-sävyt, yhtenäinen ja tyylikäs kirjavuuden sijaan
ACCENTS = ["#C9A227", "#8C6B3F"]


def format_date(raw):
    """RSS-päivämäärä -> '17.9. klo 09:15' tyyliseksi. Palauttaa tyhjän jos ei onnistu."""
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        return dt.strftime("%-d.%-m. klo %H:%M")
    except Exception:
        return raw[:16]

# Seurattavat yksittäiset brändit - muokkaa listaa vapaasti.
# Don Papa: Diageo on jakelija (ei omistaja) - silti relevantti työn kannalta.
BRANDS = [
    "Johnnie Walker", "Tanqueray", "Guinness", "Smirnoff", "Captain Morgan",
    "Ketel One", "Don Julio", "Casamigos", "Baileys", "Cîroc",
    "Roe & Co", "Caol Ila", "Bulleit", "Singleton", "Seedlip",
    "Pimm's", "Don Papa", "Santiago de Cuba",
]

# Isoimmat brändit saavat oman, kohdennetun haun (uutuudet, kasvot, julkaisut)
# geneerisen Diageo-massahaun sijaan. Muokkaa listaa vapaasti.
FLAGSHIP_BRANDS = [
    "Johnnie Walker", "Guinness", "Baileys", "Tanqueray",
    "Don Julio", "Ketel One", "Captain Morgan", "Smirnoff",
]
FLAGSHIP_LABEL = "Brändiuutiset: uutuudet, kasvot & julkaisut"
OTHER_BRANDS = [b for b in BRANDS if b not in FLAGSHIP_BRANDS]

# Suorat RSS-feedit alan omista kauppalehdistä - laadukkaampia kuin Google Newsin
# yleishaku. Nämä yhdistetään "Väkevien alan uutiset"-kategoriaan Google Newsin lisäksi.
TRADE_FEEDS = {
    "Väkevien alan uutiset ja ennusteet": [
        ("The Spirits Business", "https://www.thespiritsbusiness.com/feed/"),
    ],
}

# Muokkaa näitä hakuja vapaasti - jokainen on oma osio sivulla.
# hl/gl ohjaavat kieltä ja aluetta: fi/FI = suomenkieliset tulokset, en/US = globaalit tulokset.
QUERIES = {
    "Diageo Suomessa": {"q": '"Diageo" Suomi', "hl": "fi", "gl": "FI"},
    "Diageo maailmalla": {"q": '"Diageo"', "hl": "en", "gl": "US"},
    "Muut tarkkailtavat brändit": {
        "q": " OR ".join(f'"{b}"' for b in OTHER_BRANDS),
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
    "Suomen alan tapahtumat": {
        "q": '"Helsinki Drink Festival" OR "HDF Week" OR cocktailtapahtuma OR drinkkitapahtuma OR viskitapahtuma OR baarifestivaali',
        "hl": "fi",
        "gl": "FI",
    },
    "Alan tapahtumat maailmalla": {
        "q": "cocktail festival OR bar show OR drinks industry awards",
        "hl": "en",
        "gl": "US",
    },
}

DRINKS = [
    # Talvi
    {"season": "talvi", "tag": "Lämmittävä klassikko", "name": "Savustettu Old Fashioned",
     "note": "Sopii pimeään kauteen ja joulun ympärille.",
     "base": "Viski 5cl", "mixer": "Siirappi, angostura", "finish": "Savustettu appelsiininkuori"},
    {"season": "talvi", "tag": "Ilta-annos", "name": "Espresso Martini -variaatio",
     "note": "Ikivihreä, toimii erityisesti pimeän kauden ilta-annoksena.",
     "base": "Vodka 4cl, kahvilikööri 2cl", "mixer": "Tuore espresso", "finish": "Kolme kahvipapua"},
    {"season": "talvi", "tag": "Comfort drink", "name": "Konjakki-Toddy",
     "note": "Kuuma, rauhoittava - toimii myös alkoholittomana pohjalla.",
     "base": "Viski 4cl", "mixer": "Kuuma vesi, hunaja, sitruuna", "finish": "Kanelitanko"},
    {"season": "talvi", "tag": "Juhlava", "name": "Joulupippuri Sour",
     "note": "Terävä ja mausteinen, hyvä lisä joulusesongin listalle.",
     "base": "Gin 4cl", "mixer": "Sitruuna, siirappi, valkuainen", "finish": "Rouhittu mustapippuri"},
    # Kevät
    {"season": "kevät", "tag": "Raikas", "name": "Yrttinen Gin Fizz",
     "note": "Kevyt ja raikas, hyödyntää kevään yrttejä listalla.",
     "base": "Gin 4cl", "mixer": "Sooda, sitruuna", "finish": "Tuore tilli tai minttu"},
    {"season": "kevät", "tag": "Kausituote", "name": "Rabarperi Collins",
     "note": "Suomalainen kevätrabarperi tuo paikallisen twistin klassikkoon.",
     "base": "Vodka 4cl", "mixer": "Rabarperisiirappi, sooda", "finish": "Rabarperitikku"},
    {"season": "kevät", "tag": "Kevyt", "name": "Elderflower Highball",
     "note": "Kukkainen ja matalakalorinen, sopii aperitiiviksi.",
     "base": "Gin 4cl", "mixer": "Sambuca-sooda, samppanjahiiva-liköri", "finish": "Sitruunatwist"},
    {"season": "kevät", "tag": "Yrttinen", "name": "Basil Smash -variaatio",
     "note": "Tuoreen yrtin ja sitruksen tasapaino, näyttää hyvältä lasissa.",
     "base": "Gin 4cl", "mixer": "Sitruuna, siirappi", "finish": "Tuore basilika"},
    # Kesä
    {"season": "kesä", "tag": "Low & no", "name": "Matala-alkoholinen spritz",
     "note": "Vastaa low/no-trendiin kesäterassilla ilman että makuprofiili kärsii.",
     "base": "Aperitiivi 3cl", "mixer": "Kuohuva, soodaa", "finish": "Appelsiiniviipale"},
    {"season": "kesä", "tag": "Terassiklassikko", "name": "Highball-klassikko",
     "note": "Japanilaistyylinen highball - kevyt ja helposti skaalattava terassikäyttöön.",
     "base": "Viski 4cl", "mixer": "Runsaasti soodaa", "finish": "Sitruunatwist"},
    {"season": "kesä", "tag": "Kesäjuhla", "name": "Vesimeloni-Margarita",
     "note": "Näyttävä ja kesäinen, toimii hyvin myös isommille pöytäseurueille.",
     "base": "Tequila 4cl", "mixer": "Tuore vesimelonimehu, limetti", "finish": "Suolareunus"},
    {"season": "kesä", "tag": "Raikas", "name": "Kurkku-Gin Collins",
     "note": "Kevyt ja raikas, suosittu erityisesti lounasaikaan.",
     "base": "Gin 4cl", "mixer": "Kurkkumehu, sooda, limetti", "finish": "Kurkkuviipale"},
    # Syksy
    {"season": "syksy", "tag": "Syksyn suosikki", "name": "Savustettu Mule",
     "note": "Moscow Mulen syksyinen versio - helppo lisä listalle sellaisenaan.",
     "base": "Vodka 4cl", "mixer": "Inkiväärikaljaa, limeä", "finish": "Savustettu rosmariini"},
    {"season": "syksy", "tag": "Kausituote", "name": "Omena-Old Fashioned",
     "note": "Syksyinen twist klassikkoon, sopii ruokalistan kausivaihtoon.",
     "base": "Viski 5cl", "mixer": "Omenasiirappi, angostura", "finish": "Kaneli"},
    {"season": "syksy", "tag": "Ylellinen", "name": "Viikuna-Saksanpähkinä Old Fashioned",
     "note": "Syvä ja pähkinäinen, sopii hyvin illallisen jälkeiseksi.",
     "base": "Viski 5cl", "mixer": "Viikunasiirappi, angostura", "finish": "Saksanpähkinän kuori"},
    {"season": "syksy", "tag": "Mausteinen", "name": "Chai-Espresso Martini",
     "note": "Espresso Martinin mausteinen syksyversio - erottuu listalla.",
     "base": "Vodka 4cl, kahvilikööri 2cl", "mixer": "Tuore espresso, chai-siirappi", "finish": "Rouhittu kardemumma"},
]

SEASON_BY_MONTH = {
    12: "talvi", 1: "talvi", 2: "talvi",
    3: "kevät", 4: "kevät", 5: "kevät",
    6: "kesä", 7: "kesä", 8: "kesä",
    9: "syksy", 10: "syksy", 11: "syksy",
}


def fetch_category(query, hl="fi", gl="FI", limit=4):
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


def fetch_direct_rss(source_name, url, limit=4):
    """Hakee suoraan yhdestä RSS-feedistä (ei Google News -wrapperia)."""
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    items = []
    for entry in feed.entries[:limit]:
        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": source_name,
            }
        )
    return items


def fetch_flagship_news(brands, seen_titles, per_brand=2):
    """Hakee jokaiselle isolle brändille kohdennetusti uutuuksia, kasvoja ja julkaisuja
    - ei geneeristä 'Diageo'-mainintaa vaan nimenomaan tuote-/markkinointiuutisia."""
    items = []
    for brand in brands:
        q = (
            f'"{brand}" ambassador OR "{brand}" "limited edition" OR '
            f'"{brand}" launch OR "{brand}" campaign OR "{brand}" "new release"'
        )
        raw = fetch_category(q, hl="en", gl="US", limit=per_brand)
        items += dedup_items(raw, seen_titles)
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


def pick_drinks(n=3):
    now = datetime.now(timezone.utc)
    season = SEASON_BY_MONTH[now.month]
    pool = [d for d in DRINKS if d["season"] == season]
    week_num = now.isocalendar()[1]
    start = week_num % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(n)], season


def compute_trending(history, days=7, top_n=3):
    """Laskee mitkä seuratut brändit ovat esiintyneet useimmin otsikoissa viime päivinä."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    recent_titles = [
        h["title"].lower() for h in history if h.get("fetched_at", 0) >= cutoff
    ]
    counts = {}
    for brand in BRANDS:
        b = brand.lower()
        count = sum(1 for t in recent_titles if b in t)
        if count >= 2:
            counts[brand] = count
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return top


def dedup_items(items, seen_titles):
    """Poistaa duplikaatit sekä listan sisältä että aiemmin nähdyistä otsikoista (eri kategoriat)."""
    unique = []
    for it in items:
        key = it["title"].strip().lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(it)
    return unique


def render_items(items):
    if not items:
        return '<p class="item-body">Ei tuoreita osumia tällä haulla juuri nyt.</p>'
    html = ""
    for it in items:
        title = escape(it["title"])
        link = escape(it["link"])
        meta_parts = [p for p in [it["source"], format_date(it["published"])] if p]
        meta = escape(" · ".join(meta_parts))
        html += f"""
        <div class="item">
          <a class="item-title" href="{link}" target="_blank" rel="noopener">{title}</a>
          <p class="item-meta">{meta}</p>
        </div>"""
    return html


def render_highlights(all_results):
    """Yksi poiminta per kategoria, kompaktina korttina ylös - nopea yleiskuva."""
    cards = ""
    for i, (label, items) in enumerate(all_results.items()):
        if not items:
            continue
        top = items[0]
        color = "var(--wine)" if label == FLAGSHIP_LABEL else ACCENTS[i % len(ACCENTS)]
        cards += f"""
        <a class="hl-card" href="{escape(top['link'])}" target="_blank" rel="noopener" style="--dot: {color}">
          <span class="hl-label">{escape(label)}</span>
          <span class="hl-title">{escape(top['title'])}</span>
        </a>"""
    return cards


def render_trending(trending):
    if not trending:
        return ""
    chips = "".join(
        f'<span class="chip">{escape(brand)} <span class="chip-count">{count}</span></span>'
        for brand, count in trending
    )
    return f'<div class="trending"><span class="trending-label">Nousussa tällä viikolla</span>{chips}</div>'


def build_html(all_results, drinks, season, updated_at, trending):
    highlights_html = render_highlights(all_results)
    trending_html = render_trending(trending)

    sections_html = ""
    for i, (label, items) in enumerate(all_results.items()):
        color = "var(--wine)" if label == FLAGSHIP_LABEL else ACCENTS[i % len(ACCENTS)]
        # Brändiuutiset ja kolme ensimmäistä auki oletuksena, loput kiinni (klikillä auki)
        open_attr = "open" if (label == FLAGSHIP_LABEL or i < 3) else ""
        sections_html += f"""
        <details class="section" {open_attr}>
          <summary class="section-head" style="--dot: {color}">
            <span class="dot"></span>
            <h2>{escape(label)}</h2>
            <span class="count">{len(items)}</span>
          </summary>
          <div class="section-body">
            {render_items(items)}
          </div>
        </details>"""

    drink_cards = ""
    for d in drinks:
        drink_cards += f"""
        <div class="drink">
          <span class="drink-tag">{escape(d['tag'])}</span>
          <div class="drink-name">{escape(d['name'])}</div>
          <p class="drink-note">{escape(d['note'])}</p>
          <div class="drink-specs">
            <div><span>Pohja</span>{escape(d['base'])}</div>
            <div><span>Lisäys</span>{escape(d['mixer'])}</div>
            <div><span>Viimeistely</span>{escape(d['finish'])}</div>
          </div>
        </div>"""

    drink_html = f"""
    <section class="drink-wrap">
      <div class="section-head static"><span class="dot" style="--dot: var(--copper)"></span><h2>{escape(season.capitalize())}kauden drinkki-ideat</h2></div>
      <div class="drink-grid">
        {drink_cards}
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
    --bg: #100D0A; --bg-raised: #1A1510; --ink: #F2E9DA; --ink-dim: #9C8D78;
    --copper: #C9A227; --wine: #8B3A3A; --line: #2B241D;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg); color: var(--ink);
    font-family: 'Work Sans', sans-serif; font-size: 16px; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}
  a {{ color: inherit; }}
  .wrap {{ max-width: 800px; margin: 0 auto; padding: 48px 24px 80px; }}
  header {{ margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid var(--line); }}
  .kicker {{ color: var(--copper); font-size: 13px; margin-bottom: 8px; }}
  h1 {{ font-family: 'Fraunces', serif; font-weight: 500; font-size: clamp(28px, 5vw, 40px); line-height: 1.1; max-width: 16ch; }}
  .subhead {{ color: var(--ink-dim); font-size: 15px; margin-top: 10px; max-width: 46ch; }}

  /* Trendit */
  .trending {{ display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
  .trending-label {{ font-size: 12.5px; color: var(--ink-dim); margin-right: 4px; }}
  .chip {{
    display: inline-flex; align-items: center; gap: 5px; font-size: 13px;
    background: var(--bg-raised); border: 1px solid var(--line); border-radius: 999px;
    padding: 4px 10px;
  }}
  .chip-count {{ color: var(--copper); font-weight: 600; }}

  /* Haku */
  .search-wrap {{ margin-bottom: 24px; }}
  #search {{
    width: 100%; background: var(--bg-raised); border: 1px solid var(--line); color: var(--ink);
    border-radius: 6px; padding: 10px 14px; font-size: 14px; font-family: inherit;
  }}
  #search::placeholder {{ color: var(--ink-dim); }}
  #search:focus {{ outline: none; border-color: var(--copper); }}

  /* Nostot */
  .highlights {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-bottom: 40px; }}
  .hl-card {{
    display: block; text-decoration: none; background: var(--bg-raised);
    border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px;
    position: relative; padding-left: 20px;
  }}
  .hl-card::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--dot); border-radius: 3px 0 0 3px;
  }}
  .hl-label {{ display: block; font-size: 11px; color: var(--ink-dim); margin-bottom: 4px; }}
  .hl-title {{ display: block; font-size: 14px; font-weight: 500; line-height: 1.35; }}
  .hl-card:hover .hl-title {{ color: var(--copper); }}

  /* Sektiot */
  .section {{ border-bottom: 1px solid var(--line); }}
  .section-head {{
    display: flex; align-items: center; gap: 10px; padding: 16px 0;
    cursor: pointer; list-style: none; user-select: none;
  }}
  .section-head::-webkit-details-marker {{ display: none; }}
  .section-head.static {{ cursor: default; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--dot); flex-shrink: 0; }}
  h2 {{ font-family: 'Fraunces', serif; font-weight: 500; font-size: 18px; flex: 1; }}
  .count {{ color: var(--ink-dim); font-size: 13px; }}
  .section-body {{ padding-bottom: 18px; }}
  .item {{ padding: 10px 0 10px 18px; border-left: 1px solid var(--line); margin-left: 3px; }}
  .item-title {{ display: block; font-size: 15px; font-weight: 500; text-decoration: none; line-height: 1.4; }}
  .item-title:hover {{ color: var(--copper); }}
  .item-meta {{ color: var(--ink-dim); font-size: 12.5px; margin-top: 3px; }}

  /* Drinkki */
  .drink-wrap {{ margin-top: 28px; }}
  .drink-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
  .drink {{ background: var(--bg-raised); border: 1px solid var(--line); border-radius: 6px; padding: 20px; }}
  .drink-tag {{
    display: inline-block; font-size: 11px; color: var(--copper); border: 1px solid var(--copper);
    border-radius: 999px; padding: 2px 9px; margin-bottom: 10px;
  }}
  .drink-name {{ font-family: 'Fraunces', serif; font-size: 19px; font-weight: 500; margin-bottom: 6px; }}
  .drink-note {{ color: var(--ink-dim); font-size: 13.5px; margin-bottom: 14px; }}
  .drink-specs {{ display: flex; flex-direction: column; gap: 8px; font-size: 13px; }}
  .drink-specs div span {{ display: block; color: var(--ink-dim); font-size: 11px; margin-bottom: 2px; }}

  footer {{ color: var(--ink-dim); font-size: 12.5px; margin-top: 32px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="kicker">Päivitetty {escape(updated_at)}</div>
    <h1>Diageo & Alcohol Industry News</h1>
    <p class="subhead">Brändiuutiset, kilpailijat ja ravintolakentän liikkeet samassa näkymässä.</p>
  </header>

  {trending_html}

  <div class="search-wrap">
    <input type="text" id="search" placeholder="Hae brändi, tapahtuma tai aihe...">
  </div>

  <div class="highlights">
    {highlights_html}
  </div>

  {sections_html}

  {drink_html}

  <footer>Lähteet: Google News, The Spirits Business · päivittyy automaattisesti</footer>
</div>
<script>
(function () {{
  var input = document.getElementById('search');
  if (!input) return;
  input.addEventListener('input', function () {{
    var q = input.value.trim().toLowerCase();
    document.querySelectorAll('.item, .hl-card').forEach(function (el) {{
      var match = q === '' || el.textContent.toLowerCase().indexOf(q) !== -1;
      el.style.display = match ? '' : 'none';
    }});
    document.querySelectorAll('.section').forEach(function (section) {{
      var anyVisible = Array.prototype.some.call(
        section.querySelectorAll('.item'),
        function (el) {{ return el.style.display !== 'none'; }}
      );
      if (q !== '') section.open = anyVisible;
      section.style.display = (q === '' || anyVisible) ? '' : 'none';
    }});
  }});
}})();
</script>
</body>
</html>"""


def record_history(history, items, label, now_ts):
    for it in items:
        already_seen = any(
            h["link"] == it["link"] and h.get("category") == label for h in history
        )
        if not already_seen:
            entry = dict(it)
            entry["category"] = label
            entry["fetched_at"] = now_ts
            history.append(entry)


def main():
    all_results = {}
    history = load_history()
    now_ts = datetime.now(timezone.utc).timestamp()
    seen_titles = set()

    # Brändiuutiset ensin - kohdennetut haut isoimmille brändeille
    flagship_items = fetch_flagship_news(FLAGSHIP_BRANDS, seen_titles, per_brand=2)[:10]
    all_results[FLAGSHIP_LABEL] = flagship_items
    record_history(history, flagship_items, FLAGSHIP_LABEL, now_ts)

    for label, spec in QUERIES.items():
        trade_items = []
        for source_name, feed_url in TRADE_FEEDS.get(label, []):
            trade_items += dedup_items(
                fetch_direct_rss(source_name, feed_url), seen_titles
            )
        gnews_items = dedup_items(
            fetch_category(spec["q"], hl=spec["hl"], gl=spec["gl"]), seen_titles
        )
        items = (trade_items + gnews_items)[:6]
        all_results[label] = items
        record_history(history, items, label, now_ts)

    save_history(history)

    trending = compute_trending(history)
    drinks, season = pick_drinks()
    updated_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    html = build_html(all_results, drinks, season, updated_at, trending)

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"Sivu päivitetty: {DOCS / 'index.html'}")


if __name__ == "__main__":
    main()
