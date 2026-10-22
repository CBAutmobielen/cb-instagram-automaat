# Prompt voor Claude (Cowork of Claude Code)

Zet de map `CB_Instagram_Kit` in je werkmap, open een sessie met Claude en plak de tekst hieronder. Claude doet dan het hele proces zelf: aanbod ophalen, nieuwe auto's uitwerken, renderen en controleren.

---

Je werkt in de map `CB_Instagram_Kit`. Dit is het vaste Instagram-designsysteem van CB Automobielen (occasiondealer in Sneek, cbautomobielen.nl). Lees eerst `README.md` volledig. Volg daarna exact deze stappen.

**1. Omgeving**
- Maak een Python-omgeving en installeer `requirements.txt`, zonder andere versies te kiezen.
- Draai `python -m playwright install chromium`. Gebruik Docker als dat beschikbaar is (zie README).
- Pas `cb/render.py`, `assets/` en het designsysteem niet aan.

**2. Controle vooraf**
- Draai `python cb/render.py --schaal 1` en daarna `python cb/verify.py`.
- Meld hoeveel slides identiek zijn aan de referentie.

**3. Aanbod verversen**
- Draai `python cb/fetch.py`.
- Meld welke auto's verkocht zijn, welke prijzen of kilometerstanden zijn gewijzigd en welke auto's nieuw zijn.

**4. Nieuwe auto's uitwerken** (elke invoer in `cb/cars.json` met `review_nodig: true`):
- Lees `data/<slug>.json`. Gebruik uitsluitend deze gegevens en verzin niets. Controleer elk cijfer.
- Bekijk alle foto's in `photos/<slug>/`, bijvoorbeeld via een contactsheet, en kies:
  - `hero`: sterkste foto schuin van voren. Niet 01, daar staat een watermerk op.
  - `specs`: achterzijde schuin.
  - `options`: interieur of dashboard, bij voorkeur passend bij de opties.
  - `d1`: velg- of koplampdetail.
  - `d2` en `d3`: interieurdetail, stoelen, bagageruimte of badge.
  - `contact`: een andere vooraanzicht-foto.
  - Nooit foto 06 (verkoper) en nooit de laatste twee (showroom en pand). Elke foto maximaal één keer.
- Vul de teksten in:
  - `title` = merk en model.
  - `sub` = uitvoering zoals op de site.
  - `short` = "deze <model>" (vermijd een dubbel leesteken zoals "up!?").
- `options`: precies 6 sterke verkoopargumenten uit de optielijst, kort geformuleerd. Bijvoorbeeld "Apple CarPlay / Android Auto" of "Stoelverwarming voor".
- `opt_head`: één korte zin met de 2 à 3 sterkste opties, bijvoorbeeld "Panoramadak, Harman Kardon en Aero-pakket.".
- `det_head`: korte, feitelijke kop over uitvoering of kenmerk. Geen loze verkooppraat zoals "ongekende rijervaring".
- `det_cap`: 3 korte feiten van de pagina, zoals kleur, velgmaat of onderhoudshistorie.
- Gebruik geen fabrieksgarantie uit de feed; die datum is onbetrouwbaar.
- Kies bij een praktische auto voor ruimte en gebruiksgemak, bij een sportieve auto voor prestaties. Houd de stijl gelijk.
- Zet `review_nodig` op `false`.

**5. Renderen**
- Draai `python cb/render.py`.
- Het script controleert zelf de marges, de footer en afgekapte tekst. Bij een melding pas je de tekst in `cars.json` aan (korter) en render je opnieuw.

**6. Visuele controle**
- Bekijk per auto alle 5 slides.
- Klopt de auto bij de foto's?
- Kloppen merk, model, prijs, kilometerstand en bouwjaar met de site?
- Staan er geen foto's van een andere auto tussen?
- Werkt de eerste slide als cover?

**7. Opleveren**
- Lever de map `output/` op.
- Meld dat de map `Instagram 1080x1350` de uploadversie is.

Regels die altijd gelden:
- De auto blijft volledig waarheidsgetrouw: kleur, velgen, uitvoering en opties worden nooit veranderd.
- Gebruik geen gegenereerde beelden.
- Mix nooit gegevens van twee auto's.
- Schrijf geen em dashes in teksten.
