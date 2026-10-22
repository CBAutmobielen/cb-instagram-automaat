# CB Automobielen: Instagram-automaat

Nieuwe auto op cbautomobielen.nl → automatisch herkennen → 5 slides in de vaste huisstijl → Nederlandse caption → controles → publicatie op Instagram. Dit gebeurt elke ochtend om 08:00 via GitHub Actions.

- **Inrichten, testen, activeren en pauzeren:** zie [HANDLEIDING.md](HANDLEIDING.md)
- **Laatste rapport en wachtrij:** zie [rapport/README.md](rapport/README.md)
- **Code:** `automaat/`. Het ontwerp staat ongewijzigd in `cb/render.py`.
- **Lokale test zonder internet:** `python tests/test_lokaal.py`

---

# CB Automobielen - Instagram carrousel kit

Met deze kit maak je voor elke beschikbare occasion van cbautomobielen.nl een Instagram-carrousel van 5 slides, in de vaste CB Automobielen-stijl. Je krijgt exact hetzelfde resultaat als de opgeleverde set. Het bewijs daarvoor zit erin: `cb/verify.py` vergelijkt elke slide pixel voor pixel met het origineel.

## Wat zit erin

```
CB_Instagram_Kit/
├── README.md                 dit bestand
├── PROMPT_voor_Claude.md     prompt om het werk door Claude te laten doen (Cowork / Claude Code)
├── Dockerfile                vaste omgeving voor een pixel-identiek resultaat
├── requirements.txt          vaste versies: playwright 1.56.0, pillow 12.3.0, beautifulsoup4 4.15.0
├── run.sh                    render + controle in één keer (bash run.sh --fetch = eerst aanbod verversen)
├── cb/
│   ├── cars.json             alle auto's: specs, prijs, opties, teksten, fotokeuze, status
│   ├── render.py             maakt de slides (1080x1350 en 2160x2700)
│   ├── fetch.py              haalt het actuele aanbod en de foto's op, werkt cars.json bij
│   ├── verify.py             controleert of de uitkomst identiek is aan de referentie
│   └── reference_hashes.json vingerafdrukken van de 110 referentieslides
├── assets/
│   ├── logo.png              origineel CB Automobielen-logo (wit/oranje, transparant)
│   └── fonts/                Poppins (400 t/m 700) en DM Sans (variabel), lokaal, geen internet nodig
└── photos/<slug>/NN.jpg      de gebruikte originele verkoopfoto's (hoogste kwaliteit van de site)
```

## Snelstart

### Optie A: Docker (aanbevolen, gegarandeerd identiek)

```bash
cd CB_Instagram_Kit
docker build -t cb-insta .
docker run --rm -v "$PWD/output:/kit/output" cb-insta
```

De slides komen in `output/`. Aan het eind staat `identiek: 110  afwijkend: 0`.

### Optie B: Lokaal met Python 3.11+

```bash
cd CB_Instagram_Kit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
bash run.sh
```

Lokaal is de uitkomst visueel gelijk. Kleine verschillen in anti-aliasing zijn mogelijk als het besturingssysteem anders rendert. Wil je bytegelijke bestanden, gebruik dan Docker.

## Uitvoer

```
output/<Merk Model Uitvoering>/Instagram 1080x1350/Slide 01 Hero.png ... Slide 05 Contact.png
output/<Merk Model Uitvoering>/Master 2160x2700/Slide 01 Hero.png ... Slide 05 Contact.png
```

**Upload naar Instagram altijd de map `Instagram 1080x1350`.** Krijgt Instagram een groter bestand, dan verkleint het dat zelf en wordt de tekst zachter. Zet in de Instagram-app ook aan: Instellingen › Datagebruik en mediakwaliteit › **Uploaden in hoogste kwaliteit**.

## Nieuwe auto's toevoegen (aanbod verversen)

```bash
python cb/fetch.py          # of eerst kijken: python cb/fetch.py --droog
```

- Verkochte auto's (prijs "Op aanvraag" op de site) krijgen `status: "verkocht"` en worden niet meer gerenderd.
- Prijs en kilometerstand van bestaande auto's worden automatisch bijgewerkt.
- Nieuwe auto's komen als concept in `cars.json` met `review_nodig: true`. Alle specificaties en opties van de voertuigpagina staan in `data/<slug>.json`.
- Een auto met minder dan 8 echte foto's (bijvoorbeeld een "verwacht"-afbeelding) krijgt `status: "geen_fotos"` en wordt overgeslagen.

Een concept vul je zo aan, met de hand of met `PROMPT_voor_Claude.md`:

1. **Teksten:**
   - `title` = merk en model, bijvoorbeeld "Volkswagen Polo".
   - `sub` = de uitvoering.
   - `short` = "deze Polo", dat komt in "Interesse in deze Polo?".
2. **Opties:** precies 6 `options`, alleen uit `data/<slug>.json`.
3. **Koppen:**
   - `opt_head` = één korte zin met de 2 à 3 sterkste opties.
   - `det_head` = een korte, feitelijke detailkop.
   - `det_cap` = 3 korte feiten.
4. **Foto's:** kies de nummers in `photos`, aan de hand van `photos/<slug>/`:
   - `hero`: sterkste foto schuin van voren. Niet 01: daar staat een watermerk op.
   - `specs`: achterzijde schuin.
   - `options`: interieur of dashboard.
   - `d1`: detail van velg of koplamp.
   - `d2` en `d3`: interieurdetails, bagageruimte of badges.
   - `contact`: een andere vooraanzicht-foto.
   - Gebruik nooit foto 06 (verkoper) of de laatste twee (showroom en pand).
5. **Uitsnede:** pas eventueel `pos` aan, bijvoorbeeld `"contact": "50% 0%"` toont de bovenkant van de foto.
6. **Vrijgeven:** zet `review_nodig` op `false` en draai `python cb/render.py`.

Een concept bekijk je vooraf met `python cb/render.py --auto <deel-van-slug> --schaal 1 --ook-review`.

## Het designsysteem (niet aanpassen zonder akkoord)

| Element | Waarde |
|---|---|
| Formaat | 1080x1350 (4:5), master 2160x2700 |
| Achtergrond | #0C0E12 |
| Accent | #EB5B28 (oranje van cbautomobielen.nl) |
| Secundaire tekst | #B3B6BB |
| Lijnen | wit 14% |
| Koppen | Poppins 600 |
| Labels | DM Sans 700, hoofdletters, spatiëring 0,13em, oranje |
| Lopende tekst | DM Sans 500 |
| Marges | 72 px rondom; content eindigt 72 px boven de footer |
| Footer | 120 px, logo links, 5 slide-stippen rechts (actieve stip oranje) |
| Hoeken | foto's 5 px, knop 4 px |

Slides:
1. Hero: foto 1080x810, merk/model, uitvoering, bouwjaar, km, pk, transmissie, prijs.
2. Specificaties: foto plus raster van 6 specs.
3. Opties: interieurfoto plus 6 genummerde opties.
4. Details: kop, 3 feiten, 1 grote en 2 kleine foto's.
5. Contact: foto, "Interesse in …?", belknop, adres en contactgegevens.

`render.py` controleert na elke slide automatisch of alle tekst binnen de marges blijft, niet over de footer valt en niet wordt afgekapt. Bij een probleem stopt het script en meldt het welke slide het is.

## Spelregels voor inhoud

- Gebruik alleen informatie die op de eigen voertuigpagina van cbautomobielen.nl staat. Verzin niets.
- Gebruik alleen echte verkoopfoto's van die ene auto, nooit gegenereerde of bewerkte autobeelden.
- Maak een uitvoering nooit luxer dan hij is. Mix nooit gegevens van twee auto's.
- Houd teksten kort en zakelijk, zonder verkooppraat.
- Gebruik geen fabrieksgarantie uit de feed: daar staat bij alle auto's dezelfde, onjuiste datum.
