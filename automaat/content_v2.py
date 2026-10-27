"""VOORSTEL v2: teksten op beeld + caption. Uitsluitend op basis van de voertuigpagina (niets verzinnen).

Elke uitspraak is terug te voeren op een veld van de website:
- kop/ondertitel: de titel van de advertentie
- kerngegevens/specificaties: de specificatietabel
- opties: de optielijst (opgeschoond, betekenis gelijk)
- 'Plug-in hybride' alleen als PHEV/e-tron/plug-in in de titel staat
- 'Rijklaar' alleen als 'Rijklaar afleveren' in de opties staat
"""
import hashlib, re
from . import content

CARROSSERIE_WOORDEN = {'sportback', 'variant', 'avant', 'touring', 'estate', 'sportsvan', 'tourer', 'coupé', 'coupe',
                       'cabrio', 'cabriolet', 'limousine', 'sedan', 'kombi', 'combi', 'sw', 'shooting', 'gran',
                       'clubman', 'countryman', 'allroad', 'cross'}
PREMIUM = {'audi', 'bmw', 'mercedes-benz', 'mercedes', 'volvo', 'porsche', 'lexus', 'land', 'jaguar', 'mini', 'tesla'}
COMPACT = {'up!', 'picanto', '500', 'aygo', 'i10', 'twingo', 'c1', '108', 'ka', 'spark', 'mii', 'citigo', 'polo',
           'ibiza', 'fabia', 'clio', 'corsa', 'fiesta', 'yaris', 'i20', 'swift', 'a1'}

# v2 prioriteit: echte onderscheidende opties eerst; 'leder' alleen voor bekleding, niet voor een stuurwiel
PRIO = [
    (r'\bamg[- ]?(styling|line|pakket)|\bs[- ]?line\b|r-line|m[- ]sport|aero-pakket', 11, 'pakket'),
    (r'panorama', 12, 'dak'), (r'head.?up', 11, 'hud'), (r'virtual cockpit|digital cockpit|active info', 10, 'cockpit'),
    (r'matrix|laser', 10, 'licht'), (r'harman|bang|b&o|fender|dynaudio|burmester|bose|beats|meridian|sound system', 9, 'audio'),
    (r'adaptieve cruise|adaptive cruise|\bacc\b', 9, 'cruise'), (r'360|rondomzicht|area view', 9, 'cam'),
    (r'(lederen|leder|leer).*(bekleding|interieur|stoelen)|alcantara', 9, 'leder'),
    (r'stoelverwarming|verwarmde (voor)?stoelen', 9, 'stoelverw'), (r'massage', 9, 'massage'),
    (r'sportstoel|kuipstoel', 8, 'stoel'), (r'sportonderstel|sportchassis|adaptief onderstel|dcc|luchtvering', 8, 'onderstel'),
    (r'carplay|android auto', 8, 'phone'), (r'mmi navigatie plus|navigatie (plus|pro)|discover pro', 8, 'nav'),
    (r'navigati', 7, 'nav'), (r'keyless|comfortsleutel|comfort access|kessy', 7, 'key'),
    (r'achteruitrijcamera|camera', 7, 'cam'), (r'led (koplamp|verlichting)|led-koplamp|xenon', 7, 'licht'),
    (r'(\d{2}).{0,3}(inch|")|lichtmetalen velgen', 6, 'velg'), (r'trekhaak', 6, 'trek'),
    (r'elektrische achterklep', 6, 'klep'), (r'climate control|climatronic|klimaatregeling|comfortairco|airco \(automatisch\)|automatische airco', 5, 'airco'),
    (r'parkeerhulp|parkeersensor|pdc|park distance', 5, 'pdc'), (r'dodehoek|side assist|blind spot', 5, 'bsm'),
    (r'stuurverwarming', 5, 'stuurverw'), (r'cruise ?control', 4, 'cruise'), (r'privacy glass|getint', 3, 'tint'),
    # tweede rij: alleen om tot 6 aan te vullen
    (r'dakrail', 2, 'dakrail'), (r'led (achterlicht|dagrijverlichting)', 2, 'led2'), (r'regensensor', 2, 'regen'),
    (r'inklapbaar', 2, 'spiegel'), (r'middenarmsteun|armsteun', 1, 'arm'), (r'multifunctioneel', 1, 'stuur'),
]

HERSCHRIJF = [
    (r'^harman kardon.*$', 'Harman Kardon audio'),
    (r'^.*led-?koplampen.*$', 'LED koplampen'),
    (r'^smartphone-integratie.*carplay.*$', 'Apple CarPlay'),
    (r'^apple carplay ?/ ?android auto$', 'CarPlay / Android Auto'),
    (r'^velgen .*?(\d{2}) inch lichtmetaal$', r'\1 inch lichtmetalen velgen'),
    (r'^navigatiesysteem( full map)?$', 'Navigatie'),
    (r'^airco \(automatisch\)$|^automatische airconditioning.*$|^airco automatisch$', 'Automatische airco'),
    (r'^cruise ?control( met speedtronic)?$', 'Cruise control'),
    (r'^lederen sportstoelen$', 'Lederen sportstoelen'),
    (r'^amg-styling$', 'AMG-styling'),
    (r'^panoramaschuifdak.*$', 'Panoramaschuifdak'),
    (r'^sportstoelen voor.*$', 'Sportstoelen'),
    (r'^mmi navigatie plus$', 'MMI Navigatie plus'),
    (r'^audi sound system$', 'Audi Sound System'),
    (r'^parkeerhulp achter$', 'Parkeersensoren achter'),
    (r'^stoelverwarming.*$', 'Stoelverwarming'),
]


def netjes(o):
    for pat, nieuw in HERSCHRIJF:
        if re.match(pat, o.strip(), re.I):
            return re.sub(pat, nieuw, o.strip(), flags=re.I)
    t = content.netjes(o)
    for pat, nieuw in HERSCHRIJF:
        if re.match(pat, t, re.I):
            return re.sub(pat, nieuw, t, flags=re.I)
    return t


# Duitse/Engelse optieteksten (importfeeds) -> Nederlandse kortere naam, prioriteit, groep.
VERTAAL = [
    (r'r(ü|ue)ckfahrkamera|rear view camera|reversing camera', 'Achteruitrijcamera', 7, 'cam'),
    (r'keyless access|schl(ü|ue)ssellos|keyless entry', 'Keyless entry & start', 7, 'key'),
    (r'einparkhilfe.*front.*heck|park.*front.*rear|parking sensors front and rear', 'Parkeersensoren voor en achter', 6, 'pdc'),
    (r'einparkhilfe|parking sensor', 'Parkeersensoren', 5, 'pdc'),
    (r'wireless charging|induktive', 'Draadloos laden', 6, 'laden'),
    (r'apple carplay.*android auto|android auto.*apple carplay', 'CarPlay / Android Auto', 8, 'phone'),
    (r'(two|2).{0,10}climate control zones|2-zonen', '2-zone climate control', 6, 'airco'),
    (r'automatic air conditioning|klimaautomatik', 'Automatische airco', 5, 'airco'),
    (r'seat.{0,40}heated|sitzheizung', 'Stoelverwarming', 9, 'stoelverw'),
    (r'navigation system "?discover pro', 'Navigatie Discover Pro', 8, 'nav'),
    (r'navigation system "?discover media', 'Navigatie Discover Media', 8, 'nav'),
    (r'navigation system|navigationssystem', 'Navigatie', 7, 'nav'),
    (r'(\d{2}).{0,4}(\'\'|"|inch|zoll).{0,30}alloy|alloy.{0,60}?(\d{2})\s?(\'\'|"|inch)', None, 6, 'velg'),
    (r'privacy glass|privacyverglasung', 'Privacy glass', 3, 'tint'),
    (r'rain sensing|regensensor', 'Regensensor', 2, 'regen'),
    (r'nebelscheinwerfer.*abbiegelicht', 'Mistlampen met bochtverlichting', 3, 'mist'),
    (r'sprachbedienung|voice activat', 'Spraakbediening', 4, 'voice'),
    (r'adaptive cruise|abstandsregel|acc ', 'Adaptieve cruise control', 9, 'cruise'),
    (r'speed limiter|geschwindigkeitsbegrenzer', 'Snelheidsbegrenzer', 2, 'limiter'),
    (r'light sensitive rear view mirror|automatisch abblendend', 'Automatisch dimmende binnenspiegel', 2, 'spiegel2'),
    (r'digital cockpit|active info display', 'Digital Cockpit', 8, 'cockpit'),
]
NIET_NL = re.compile(r'[äöüß]|\b(und|mit|f(ü|ue)r|with|and|the|seat|seats|wheels?|system|front|rear|driver|speakers?|'
                     r'configured|includes|type|mounted|controls?|located)\b', re.I)


def _velg_tekst(o):
    m = re.search(r'(\d{2})\s?(\'\'|"|inch|zoll)', o, re.I)
    return f'{m.group(1)} inch lichtmetalen velgen' if m else None


def opties(v, n=6):
    alle = list(dict.fromkeys([o for o in v.get('bijzondere_opties', []) + v.get('opties', []) if o]))
    scored, groepen, uit = [], set(), []
    vertaald = {}
    for i, o in enumerate(alle):
        for pat, label, s, g in VERTAAL:
            if re.search(pat, o, re.I):
                label = label or _velg_tekst(o)
                if label:
                    vertaald[o] = label
                    scored.append((-s, i, o, g))
                break
    for i, o in enumerate(alle):
        if o in vertaald:
            continue
        lo = o.lower()
        for pat, s, g in PRIO:
            if re.search(pat, lo):
                scored.append((-s, i, o, g)); break
    for _, _, o, g in sorted(scored):
        if g in groepen:
            continue
        t = vertaald.get(o) or netjes(o)
        if len(t) > 26 or t in uit or (o not in vertaald and NIET_NL.search(o)):
            continue
        groepen.add(g); uit.append(t)
        if len(uit) == n:
            break
    # reserve: overige echte opties (geen standaard veiligheid of administratie) in volgorde van de site
    if len(uit) < n:
        for o in alle:
            t = netjes(o)
            if (len(uit) >= n or t in uit or len(t) > 26 or len(t) < 4 or re.search(BASIS, o, re.I)
                    or o in vertaald or NIET_NL.search(o) or re.search(r'diebstahl|airbag|^\[', o, re.I)):
                continue
            uit.append(t)
    return uit[:n]


BASIS = (r'airbag|abs\b|anti blokkeer|anti doorslip|stabiliteit|esp\b|brake assist|remkracht|sper diff|startblokkering|alarm|'
         r'immobiliser|isofix|stuurbekrachtiging|centrale (deur)?vergrendeling|elektrische ramen|boordcomputer|instructieboekje|'
         r'onderhoudsboekje|onderhoudshistorie|rijklaar|nap|bandenspanning|hill hold|start/stop|hoofdsteun|verstelbaar|'
         r'neerklapbaar|radio\b|cd|mp3|voorbereiding|derde remlicht|gordel|kinderslot|pakket$|^.{0,3}$')


def kop_en_ondertitel(v):
    titel = v['title'].split()
    n = 2
    for mm in content.MEERWOORDIGE_MERKEN:
        if v['title'].lower().startswith(mm.lower()):
            n = len(mm.split()) + 1
    if len(titel) > n and titel[n].lower() in CARROSSERIE_WOORDEN:
        n += 1
    return ' '.join(titel[:n]).upper(), ' '.join(titel[n:])


def is_plugin(v):
    return bool(re.search(r'\bphev\b|e-tron|plug-in|plugin|\bgte\b|recharge|e-hybrid', v['title'], re.I))


def _verbruik(t):
    m = re.search(r'(\d+[.,]?\d*)\s*liter', t or '')
    return f"{m.group(1).replace('.', ',')} l/100 km" if m else None


def specs(v):
    t = v['table']; out = []
    brandstof = 'Plug-in hybride' if is_plugin(v) and 'hybr' in t.get('Brandstof', '').lower() else t.get('Brandstof')
    carr = t.get('Carrosserievorm', '')
    if '(' in carr:
        a, b = carr.split('(', 1); d = re.search(r'\d', b)
        carr = f"{a.strip()} · {d.group(0)}-deurs" if d else a.strip()
    kandidaten = [
        ('Transmissie', t.get('Transmissie')), ('Brandstof', brandstof), ('Carrosserie', carr), ('Kleur', t.get('Kleur')),
        ('Energielabel', t.get('Energielabel') if re.fullmatch(r'[A-G]\+*', (t.get('Energielabel') or '').strip()) else None),
        ('Gem. verbruik', _verbruik(t.get('Verbruik (gemiddeld)'))),
        ('Topsnelheid', t.get('Topsnelheid', '').replace('km/h', 'km/u') or None),
        ('APK tot', t.get('APK geldig tot')), ('Zitplaatsen', t.get('Aantal zitplaatsen')),
    ]
    for k, val in kandidaten:
        if val and len(out) < 6:
            out.append((k, val))
    return out


def merkmodel(v):
    kop, _ = kop_en_ondertitel(v)
    return ' '.join(v['title'].split()[:len(kop.split())])


def model_kort(v):
    w = merkmodel(v).split()
    return ' '.join(w[1:2]) if len(w) > 1 else w[0]


def maak_v2(v, nieuw=True):
    t = v['table']
    kop, sub = kop_en_ondertitel(v)
    km = t.get('Kilometerstand', '').replace(' Km', ' km')
    opts = opties(v)
    kort = [o for o in opts if len(o) <= 15]
    optiekop = f"{kort[0]} & {kort[1][0].lower() + kort[1][1:] if kort[1].split()[0].lower() not in content.MERKWOORDEN else kort[1]}" if len(kort) >= 2 else (opts[0] if opts else 'Uitrusting')
    if len(optiekop) > 32:
        optiekop = opts[0]
    return {
        'label': 'Nieuw in voorraad' if nieuw else 'Nu beschikbaar',
        'kop': kop, 'ondertitel': sub,
        'kern': [t.get('Bouwjaar', ''), km, content._vermogen(t.get('Vermogen', ''))],
        'specs': specs(v), 'opties': opts, 'optiekop': optiekop,
        'cta_kop': f"Interesse in deze {model_kort(v)}?",
        'rijklaar': any(re.search(r'rijklaar', o, re.I) for o in v.get('opties', [])),
    }


# ---------------- caption ----------------

def segment(v):
    t = v['table']; titel = v['title'].lower()
    pk = int(re.search(r'\d+', t.get('Vermogen', '0')).group(0)) if re.search(r'\d+', t.get('Vermogen', '')) else 0
    merk = titel.split()[0]
    model = titel.split()[1] if len(titel.split()) > 1 else ''
    carr = t.get('Carrosserievorm', '').lower()
    if is_plugin(v):
        return 'plugin'
    if pk >= 240 or re.search(r'\bamg\b|\bgti\b|\btcr\b|\brs\s?\d|\bs\d\b|\bm\d\b|cupra|\bst\b|type r', titel):
        return 'sportief'
    if merk in PREMIUM:
        return 'premium'
    if re.search(r'stationwagon|suv|mpv|terrein', carr) or re.search(r'variant|avant|touring|estate|tourer', titel):
        return 'praktisch'
    if model in COMPACT:
        return 'compact'
    return 'algemeen'


OPENERS = {
    'plugin': [
        "Elektrisch waar het kan, {pk} wanneer je het nodig hebt.",
        "Plug-in hybride met {pk} en energielabel {label}.",
        "Sportief én zuinig: {pk}, plug-in hybride en energielabel {label}.",
    ],
    'sportief': [
        "{pk} en {transmissie_lc}: gemaakt voor wie van rijden houdt.",
        "Sportief karakter, {pk} en een uitrusting die daarbij past.",
        "Voor de liefhebber: {pk} in een strak pakket.",
    ],
    'premium': [
        "Premium rijcomfort met {opt1} en {opt2}.",
        "Comfortabel, compleet en met {opt1}.",
        "Een premium {carr_lc} met {opt1} en {opt2}.",
    ],
    'praktisch': [
        "Ruimte en comfort voor elke dag, met {opt1}.",
        "Praktisch, ruim en uitgerust met {opt1} en {opt2}.",
        "Veel ruimte voor elke dag, met {opt1} en {opt2}.",
    ],
    'compact': [
        "Compact, wendbaar en uitgerust met {opt1}.",
        "Ideaal in de stad: compact, met {opt1} en {opt2}.",
        "Klein van formaat, compleet uitgerust met {opt1}.",
    ],
    'algemeen': [
        "Nieuw in ons aanbod, met {opt1} en {opt2}.",
        "Een nette {carr_lc} met {opt1} en {opt2}.",
    ],
}

HASH_EXTRA = {'plugin': '#PluginHybride', 'sportief': '#Sportief', 'praktisch': '#Stationwagon', 'compact': '#Stadsauto'}


def _klein(o):
    return content._klein(o)


def caption(v, c2, gebruikte_openers=()):
    t = v['table']; seg = segment(v)
    km = t.get('Kilometerstand', '').replace(' Km', ' km')
    opts = c2['opties']
    data = dict(pk=content._vermogen(t.get('Vermogen', '')), label=t.get('Energielabel', ''),
                transmissie_lc=t.get('Transmissie', '').lower(),
                carr_lc=t.get('Carrosserievorm', '').split('(')[0].strip().lower() or 'auto',
                opt1=_klein(opts[0]) if opts else '', opt2=_klein(opts[1]) if len(opts) > 1 else '')
    keuzes = [o for o in OPENERS[seg] if o not in gebruikte_openers] or OPENERS[seg]
    if seg == 'plugin' and not data['label']:
        keuzes = [o for o in keuzes if '{label}' not in o] or keuzes
    h = int(hashlib.md5(v['id'].encode()).hexdigest(), 16)
    opener = keuzes[h % len(keuzes)]
    zin = opener.format(**data)
    zin = zin[0].upper() + zin[1:]
    rk = ' · rijklaar' if c2.get('rijklaar') else ''
    merkmod = merkmodel(v)
    tags = ['#CBAutomobielen', '#Sneek', '#Friesland', '#Occasion',
            '#' + re.sub(r'[^0-9A-Za-z]', '', merkmod.split()[0]),
            '#' + re.sub(r'[^0-9A-Za-z]', '', ''.join(merkmod.split()[:2]))]
    if seg in HASH_EXTRA:
        tags.append(HASH_EXTRA[seg])
    tags = list(dict.fromkeys(tags))
    kenmerken = '\n'.join(f'• {o}' for o in opts[:5])
    tekst = f"""{zin}

{v['title']}
{t.get('Bouwjaar')} · {km} · {data['pk']} · {t.get('Transmissie')}

Wat deze auto onderscheidt:
{kenmerken}

Vraagprijs {v['prijs']}{rk}

Bekijk alle foto's en specificaties via de link in onze bio. Vragen of een bezichtiging plannen? Bel 0515 745 030 of stuur ons een DM.

📍 CB Automobielen · Edisonstraat 1c, Sneek
Ref. {v['id']}

{' '.join(tags)}"""
    return tekst, opener
