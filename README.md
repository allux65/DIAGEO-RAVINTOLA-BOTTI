# Diageo & Ravintola-ala -botti

Automaattinen briiffi, joka päivittyy 3x viikossa nettisivulle ja lähettää
kerran kuussa yhteenvedon sähköpostiin. Ei vaadi mitään maksullisia API-avaimia.

## Käyttöönotto

1. **Luo uusi GitHub-repo** (esim. `diageo-ravintola-botti`), julkinen tai yksityinen.
2. **Lataa nämä tiedostot repoon** samassa kansiorakenteessa kuin ne ovat tässä paketissa.
3. **Ota GitHub Pages käyttöön:**
   - Repo → Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `main`, kansio: `/docs`
   - Tallenna. Sivu ilmestyy osoitteeseen `https://KÄYTTÄJÄNIMI.github.io/REPON-NIMI/`
4. **Lisää salaisuudet kuukausiyhteenvetoa varten:**
   - Repo → Settings → Secrets and variables → Actions → New repository secret
   - `EMAIL_ADDRESS` — Gmail-osoitteesi (sama jota käytit lentobotissa käy hyvin)
   - `EMAIL_APP_PASSWORD` — Gmailin sovellussalasana (sama kuin lentobotissa jos haluat)
   - `EMAIL_TO` — mihin osoitteeseen yhteenveto lähetetään (voi olla sama kuin EMAIL_ADDRESS)
5. **Testaa manuaalisesti:**
   - Repo → Actions → "Päivitä Diageo & ravintola-ala -briiffi" → Run workflow
   - Tarkista että `docs/index.html` päivittyy ja sivu latautuu
   - Testaa myös "Kuukausiyhteenveto sähköpostiin" → Run workflow, tarkista että meili tulee perille

## Ajastukset

- **Sivun päivitys:** maanantai, keskiviikko, perjantai klo 6:00 UTC
- **Sähköposti:** joka kuukauden 1. päivä klo 7:00 UTC

Molempia voi muokata `.github/workflows/*.yml` -tiedostojen cron-riveiltä.

## Datalähteet

Kaikki haetaan Google News RSS:n kautta (ei vaadi API-avainta):
- Diageo Suomessa & maailmalla
- Kilpailijat (Pernod Ricard, Bacardi, Brown-Forman, Suntory, Campari)
- Uudet ravintolat ja baarit Suomessa
- Suomen ravintola-alan uutiset
- Cocktail-trendit maailmalla
- Väkevien alan uutiset ja ennusteet
- Alan tapahtumat

Hakusanoja voi muokata `src/fetch_digest.py` -tiedoston `QUERIES`-sanakirjasta.

## Drinkki-idea

Vaihtuu automaattisesti kauden mukaan (kevät/kesä/syksy/talvi) ja rotaatiolla
viikkonumeron mukaan saman kauden sisällä. Lista löytyy `DRINKS`-muuttujasta
samasta tiedostosta — voit lisätä tai muokata ideoita vapaasti.
