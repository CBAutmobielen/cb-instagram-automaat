# Instagram-automaat CB Automobielen: handleiding

**Wat het doet:** elke ochtend om 08:00 (Nederlandse tijd) controleert de automaat cbautomobielen.nl. Een nieuwe auto komt in de wachtrij. Op de **publicatiedagen (standaard dinsdag en vrijdag)** maakt de automaat 5 slides in de vaste huisstijl, schrijft hij een caption en controleert hij alles. Als alle controles slagen, plaatst hij de carrousel van de eerstvolgende auto uit de wachtrij op Instagram. Per publicatiedag gaat er maximaal 1 auto online. Een auto die in de tussentijd verkocht wordt, gaat automatisch uit de wachtrij.

Direct na elke carrousel plaatst de automaat ook een **story** (1080x1920, zelfde huisstijl: foto, model, prijs en "Bekijk de nieuwe post op ons profiel"). De officiële API kan geen aanklikbare post- of linksticker toevoegen. Uitzetten: GitHub-variabele `STORY` = `uit`.

Andere dagen kiezen kan via de GitHub-variabele `PUBLICATIE_DAGEN`, bijvoorbeeld `ma,do` of `di,do,za`.

Alles draait op **GitHub Actions**: in de cloud, gratis, en ook als je computer uit staat.

---

## Eenmalige inrichting

### 1. GitHub
1. Maak een gratis account op github.com.
2. Maak een repository aan, bijvoorbeeld `cb-instagram-automaat`, en zet die op **Public**.
   - Instagram moet de afbeeldingen via een openbare link kunnen ophalen. Dat is een eis van Meta.
   - Er staan geen wachtwoorden of tokens in de repository. Die staan versleuteld bij GitHub als "secrets".
3. Upload de inhoud van deze map, of laat Claude dat doen nadat je GitHub hebt gekoppeld.
4. Ga naar Settings › Actions › General › Workflow permissions en kies **Read and write permissions**.

### 2. Instagram koppelen (officiële Instagram API, geen browserbot)
Voorwaarde: je Instagram-account is een **zakelijk account** of **creator-account**. Dit stel je in de Instagram-app in via Instellingen › Accounttype en tools.

1. Ga naar **developers.facebook.com** en log in met het Facebook-account van het bedrijf.
2. Kies **Mijn apps › App maken**. Kies als gebruiksdoel **"Berichten en content beheren op Instagram"** (Instagram API) en als type **Zakelijk**.
3. Open in de app **Instagram › API-instellingen met Instagram-login**.
4. Klik bij "Toegangstokens genereren" op **Account toevoegen**. Log in met het Instagram-account van CB Automobielen en geef toestemming voor:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
5. Kopieer twee dingen:
   - het **toegangstoken** (lange code)
   - het **Instagram-gebruikers-ID** (getal)
6. Ga in GitHub naar Settings › Secrets and variables › Actions › **New repository secret** en maak deze aan:
   - `IG_ACCESS_TOKEN` = het token
   - `IG_USER_ID` = het ID

Het token is 60 dagen geldig. **De automaat verlengt het zelf elke week.** Je hoeft dit alleen opnieuw te doen als het token ongeldig wordt, bijvoorbeeld na een wachtwoordwijziging. Dat zie je dan in het rapport.

> Werkt de app alleen in "ontwikkelmodus"? Dat is voor je eigen account voldoende. Krijg je de melding dat het account geen toegang heeft? Voeg het Instagram-account dan toe als tester via App-rollen › Rollen › Instagram-tester. Accepteer de uitnodiging daarna in Instagram via Instellingen › Apps en websites › Uitnodigingen voor testers.

### 3. Optioneel: Claude voor fotokeuze en teksten (aanbevolen)
Zonder deze sleutel werkt de automaat met vaste regels:
- Vaste fotonummers, volgens de vaste fotovolgorde van de site.
- Opties op prioriteit.
- Vaste zinsopbouw voor de intro.

Met een **Anthropic API-sleutel** bekijkt Claude alle foto's en kiest hij per slide de juiste: voorkant, achterkant, interieur en details. Hij schrijft ook de koppen en de intro. Elke tekst wordt automatisch gecontroleerd. Alleen opties en getallen die op de voertuigpagina staan worden toegelaten, en claims als "garantie", "schadevrij" of "nieuwstaat" worden geweigerd.

- Kosten: betalen per gebruik, ongeveer € 0,03 tot € 0,10 per auto. Bij 1 auto per dag is dat enkele euro's per maand. Er is geen abonnement.
- Instellen:
  1. Maak een sleutel aan op console.anthropic.com.
  2. Zet deze als secret `ANTHROPIC_API_KEY` in GitHub.

### 4. Optioneel: rapport per e-mail
GitHub mailt je automatisch als een run mislukt. Wil je ook een rapport bij elke publicatie? Voeg dan deze secrets toe:
- `SMTP_HOST`
- `SMTP_USER`
- `SMTP_PASS`
- `RAPPORT_EMAIL`

Voor Microsoft 365 is `SMTP_HOST` = `smtp.office365.com`. Je hebt daarvoor een app-wachtwoord nodig, en "SMTP AUTH" moet aan staan voor de mailbox.

---

## Testen (er wordt niets gepubliceerd)
1. Ga in GitHub naar **Actions › Instagram-automaat › Run workflow**.
2. Kies modus **proef**. Vul eventueel een voertuig-ID in: het nummer achter in de URL, bijvoorbeeld `941609`.

De proef doet het volgende:
- Hij leest de website, downloadt de foto's, maakt 5 slides en de caption, en doet alle controles.
- Hij maakt bij Instagram een carrousel-container aan. Daarmee test je de koppeling en of Instagram de beelden accepteert.
- Hij **publiceert die container niet**. Een container die niet gepubliceerd wordt, verdwijnt na 24 uur vanzelf en is nooit zichtbaar.

De slides en caption kun je onderaan de run downloaden onder "Artifacts".

## Activeren
Ga naar Settings › Secrets and variables › Actions › tabblad **Variables** › New variable:
- Naam `PUBLICATIE`, waarde `aan`

Zolang deze variabele niet `aan` is, draait de automaat elke ochtend wel, maar publiceert hij niets.

**Eerste run:** alle auto's die op dat moment op de site staan worden vastgelegd als "bestaand" en worden niet alsnog gepost. Alleen auto's die daarna verschijnen komen in de wachtrij.

Wil je toch een bestaande auto plaatsen? Gebruik dan Run workflow › modus `live` › voertuig-ID.

## Pauzeren
- **Snel:** zet de variabele `PUBLICATIE` op `uit`. De controle en het rapport blijven doorlopen.
- **Helemaal stoppen:** Actions › Instagram-automaat › ⋯ › **Disable workflow**. Met **Enable workflow** zet je hem weer aan.

## Rapport
- `rapport/README.md` in de repository bevat de laatste controle, de wachtrij met geplande datums, de laatst gepubliceerde posts, fouten en prijswijzigingen.
- In `rapport/archief/` staat een rapport per dag.
- `state/database.json` bevat per auto: ID, URL, ontdekdatum, beschikbaarheid, prijs, status van de beelden en de caption, geplande datum, publicatiedatum, Instagram-post-ID en eventuele fouten.

## Veiligheid tegen fouten en dubbele posts
- Een auto wordt herkend aan het vaste nummer in zijn URL. Een prijswijziging maakt het dus geen nieuwe auto.
- Vóór publicatie controleert de automaat:
  - de database;
  - de laatste 50 Instagram-posts: staat de link naar deze auto er al in, dan wordt er niet gepubliceerd.
- Wordt een publicatie halverwege onderbroken? Dan kijkt de volgende run eerst op Instagram of de post toch bestaat.
- Geeft de website 0 auto's of een storing? Dan wordt niets als verkocht gemarkeerd en niets gepubliceerd.
- Mislukt een auto 3 keer? Dan gaat hij uit de automatische wachtrij en komt hij onder "Vraagt aandacht" in het rapport.
- Een auto met te weinig echte foto's (bijvoorbeeld alleen een "verwacht"-afbeelding) wordt overgeslagen tot er foto's zijn.

## Herstelprocedure
| Melding in het rapport | Oplossing |
|---|---|
| `geen geldig Instagram-token` | Maak een nieuw token aan (stap 2.4 en 2.5) en vervang het secret `IG_ACCESS_TOKEN`. |
| `aanbodpagina gaf 0 auto's` | De website is offline of de opbouw van de site is veranderd. Controleer de site. Na een website-update moeten de selectors in `automaat/site.py` mogelijk worden aangepast. |
| `afbeelding niet openbaar bereikbaar` | Staat de repository nog op Public? |
| `... wijkt af` (prijs/km) | De site is tijdens de run gewijzigd. De volgende run pakt het automatisch goed op. |
| auto onder "Vraagt aandacht" | Controleer de voertuigpagina. Zet daarna in `state/database.json` de `status` van die auto terug op `wachtrij` en `pogingen` op `0`. |
