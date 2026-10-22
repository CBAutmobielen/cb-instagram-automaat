"""Van voertuigdata naar een carrousel-invoer (zelfde velden als cb/cars.json) en caption-bouwstenen.

Alles komt uitsluitend uit de voertuigpagina. Er wordt niets verzonnen: optionele AI-teksten
(automaat/ai.py) worden per veld gecontroleerd en anders vervangen door deze vaste regels.
"""
import re, hashlib
from . import config

MEERWOORDIGE_MERKEN = ['Land Rover', 'Alfa Romeo', 'Aston Martin', 'Mercedes Benz', 'Range Rover', 'Lynk & Co']
MERKWOORDEN = {'apple', 'android', 'carplay', 'harman', 'kardon', 'fender', 'dynaudio', 'burmester', 'bose', 'beats',
               'bang', 'led', 'climatronic', 'climatic', 'keyless', 'audi', 'mmi', 'amg', 'bmw', 'volkswagen', 'vw',
               'mercedes', 'mercedes-benz', 'seat', 'skoda', 'kia', 'fiat', 'ford', 'opel', 'peugeot', 'renault',
               'toyota', 'volvo', 'mini', 'cupra', 'tesla', 'hyundai', 'mazda', 'nissan', 'porsche', 'jbl', 'dab',
               'dab+', 'isofix', 'xenon', 'bi-xenon', 'matrix', 'head-up', 'virtual', 'digital', 'drive', 'light',
               'aero', 'gti', 'gtd', 'r-line', 's', 'line', 'm', 'rs', 'st', 'st-line', 'amg-line', 'start/stop'}

# Hoe aantrekkelijk een optie is als verkoopargument. Groep = voorkom dubbele (airco + climate control).
PRIORITEIT = [
    (r'panorama', 10, 'dak'), (r'schuif.?kanteldak|schuifdak', 8, 'dak'),
    (r'head.?up', 9, 'hud'), (r'carplay|android auto', 9, 'phone'),
    (r'harman|bang|fender|dynaudio|burmester|bose|beats|jbl|premium sound|meridian', 9, 'audio'),
    (r'virtual cockpit|digital cockpit|active info|digitaal (instrument|dashboard)', 8, 'cockpit'),
    (r'adaptieve cruise|adaptive cruise|\bacc\b', 8, 'cruise'),
    (r'360|rondomzicht|area view', 8, 'cam'), (r'achteruitrijcamera|camera', 7, 'cam'),
    (r'leder|leer\b|alcantara', 8, 'leder'), (r'navigatie|navigation', 8, 'nav'),
    (r'matrix|led koplamp|led-koplamp|xenon', 7, 'licht'),
    (r'stoelverwarming|verwarmde voorstoelen|verwarmde stoelen', 7, 'stoelverw'),
    (r'sportstoel|sportstoelen|kuipstoel', 6, 'stoel'), (r'massage|elektrisch verstelbare (voor)?stoel', 6, 'stoel2'),
    (r'keyless|comfort access|kessy', 6, 'key'),
    (r'lichtmetalen velgen|lm velgen|inch', 6, 'velg'),
    (r'climate control|climatronic|klimaatregeling|automatische airco', 6, 'airco'),
    (r'elektrische achterklep', 5, 'klep'), (r'trekhaak', 5, 'trek'),
    (r'parkeersensor|parkeerhulp|park distance|pdc', 5, 'pdc'), (r'dodehoek|blind spot|side assist', 5, 'bsm'),
    (r'stuurverwarming', 5, 'stuurverw'), (r'cruise control', 4, 'cruise'), (r'airco', 4, 'airco'),
    (r'lane assist|rijstrook', 4, 'lane'), (r'multifunctioneel', 3, 'stuur'),
    (r'bluetooth|telefoon', 3, 'phone'), (r'dakrail', 2, 'dakrail'), (r'getinte', 2, 'tint'),
]


def _norm_num(s):
    return {re.sub(r'[.,]', '', n) for n in re.findall(r'\d+(?:[.,]\d+)*', s)}


def toegestane_getallen(v):
    """Alle getallen die in de data van deze auto voorkomen. Tekst mag alleen deze getallen bevatten."""
    bron = ' '.join([v.get('title', ''), v.get('prijs', ''), ' '.join(v.get('table', {}).values()),
                     ' '.join(v.get('opties', [])), ' '.join(v.get('bijzondere_opties', []))])
    return _norm_num(bron)


def getallen_ok(tekst, v):
    return _norm_num(tekst) <= toegestane_getallen(v)


def _kap(o):
    return o[:1].upper() + o[1:]


def _klein(o):
    """Eerste letter klein in lopende tekst, behalve bij merknamen/afkortingen."""
    w = o.split()[0]
    if w.lower() in MERKWOORDEN or any(ch.isupper() for ch in w[1:]) or w.isupper() or re.match(r'\d', w):
        return o
    return o[:1].lower() + o[1:]


def splits_titel(v):
    t = v.get('table', {})
    titel = v['title'].strip()
    merk, model = t.get('Merk', '').strip(), t.get('Model', '').strip()
    if merk and model and titel.lower().startswith(f'{merk} {model}'.lower()):
        n = len(f'{merk} {model}')
        return titel[:n], titel[n:].strip()
    for mm in MEERWOORDIGE_MERKEN:
        if titel.lower().startswith(mm.lower() + ' '):
            rest = titel[len(mm):].split()
            return f'{titel[:len(mm)]} {rest[0]}', ' '.join(rest[1:])
    w = titel.split()
    return ' '.join(w[:2]), ' '.join(w[2:])


def _vermogen(s):
    m = re.search(r'(\d+)\s*pk', s, re.I)
    if m:
        return f'{m.group(1)} pk'
    m = re.search(r'(\d+)\s*kw', s, re.I)
    return f'{m.group(1)} kW' if m else s   # niet omrekenen: alleen getallen die op de site staan


HERSCHRIJF = [
    (r'^audio[- ]?navigati\w*.*$', 'Navigatie'),
    (r'^lichtmetalen velgen\s*(\d{2})\s*(inch|"|”|\'\')?$', r'\1 inch lichtmetalen velgen'),
    (r'^(\d{2})\s*(inch|"|”)\s*lichtmetalen velgen$', r'\1 inch lichtmetalen velgen'),
    (r'^comfortairconditioning$', 'Comfort airconditioning'),
    (r'^bluetooth telefoonvoorbereiding$', 'Bluetooth telefoon'),
    (r'^lederen stuurwiel$', 'Lederen stuur'),
]
RUIS = r'\b(full map|hard ?disk|hdd|sd[- ]?kaart|cd[- ]?speler|mp3|dvd|met afstandsbediening)\b'


def netjes(o):
    """Technische optienamen van de site omzetten naar korte, nette Nederlandse tekst. Betekenis blijft gelijk."""
    t = re.sub(r'\s*\([^)]*\)', '', o)                    # (866) e.d. weg
    t = re.sub(r',\s*metaallak', ' metaallak', t, flags=re.I)
    t = re.sub(r'(\d{2})\s*(?:"|”|\'\')', r'\1 inch', t)       # 18" -> 18 inch
    t = re.sub(RUIS, '', t, flags=re.I)
    t = re.sub(r'\s*[+/&,-]\s*$', '', re.sub(r'\s+', ' ', t)).strip(' +,-/')
    for pat, nieuw in HERSCHRIJF:
        if re.match(pat, t, re.I):
            t = re.sub(pat, nieuw, t, flags=re.I); break
    return _kap(t.strip()) if len(t.strip()) >= 3 else _kap(o.strip())


def scoor_opties(v):
    """Kandidaat-opties op volgorde van aantrekkelijkheid, zonder dubbele groepen."""
    bijzonder = [o for o in v.get('bijzondere_opties', []) if o]
    rest = [o for o in v.get('opties', []) if o and o not in bijzonder]
    scored = []
    for i, o in enumerate(bijzonder + rest):
        lo = o.lower(); score, groep = 0, None
        for pat, s, g in PRIORITEIT:
            if re.search(pat, lo):
                score, groep = s, g; break
        if o in bijzonder:
            score += 3
        if len(o) > 38:
            score -= 3          # lange optienamen passen minder goed
        scored.append((-score, i, o, groep or o.lower()))
    scored.sort()
    gekozen, groepen = [], set()
    for _, _, o, g in scored:
        if g in groepen:
            continue
        groepen.add(g)
        n = netjes(o)
        if n not in gekozen:
            gekozen.append(n)
    return gekozen


def kies_fotos(n):
    """Vaste fotokeuze volgens de kit-regels (zonder AI). n = aantal foto's in de galerij."""
    verboden = {1, 6, n - 1, n}
    pref = dict(hero=4, specs=8, options=2, d1=9, d2=10, d3=11, contact=7)
    gebruikt, uit = set(), {}
    vrij = [i for i in range(2, n - 1) if i not in verboden]
    for k, i in pref.items():
        if i in verboden or i > n or i in gebruikt:
            i = next(j for j in vrij if j not in gebruikt)
        gebruikt.add(i); uit[k] = f'{i:02d}'
    return uit


def toegestane_fotos(n):
    return [f'{i:02d}' for i in range(2, n - 1) if i != 6]


def _velg(v):
    for o in v.get('bijzondere_opties', []) + v.get('opties', []):
        m = re.search(r'(\d{2})\s?(?:inch|"|”)', o, re.I)
        if m and re.search(r'velg|lichtmeta|lm', o, re.I):
            return f'{m.group(1)} inch lichtmetaal'
    return None


def detail_feiten(v):
    t = v.get('table', {}); f = []
    kleur = t.get('Kleur') or t.get('Kleur exterieur') or ''
    if kleur and len(kleur) <= 28:
        f.append(_kap(kleur))
    velg = _velg(v)
    if velg:
        f.append(velg)
    ob = (t.get('Onderhoudsboekje') or '').lower()
    if ob in ('ja', 'aanwezig', 'compleet', 'volledig'):
        f.append('Onderhoudsboekje aanwezig')
    if any(re.search(r'led (koplamp|verlichting)|led-koplamp', o, re.I) for o in v.get('opties', [])):
        f.append('LED koplampen')
    el = t.get('Energielabel', '')
    if re.fullmatch(r'[A-G]\+*', el.strip()):
        f.append(f'Energielabel {el.strip()}')
    f.append('Rijklaar afgeleverd')
    uniek = list(dict.fromkeys(x for x in f if x))
    while len(uniek) < 3:
        uniek.append(['Rijklaar afgeleverd', 'Direct beschikbaar', 'Bezichtiging in Sneek'][len(uniek) % 3])
        uniek = list(dict.fromkeys(uniek))
    return uniek[:3]


def koppen(car, v):
    opts = car['options']
    def lijst(items):
        items = [items[0]] + [_klein(x) for x in items[1:]]
        return (', '.join(items[:-1]) + ' en ' + items[-1] + '.') if len(items) > 1 else items[0] + '.'
    opt_head = None
    kort = [o for o in opts if len(o) <= 20] or opts   # korte, krachtige opties voor de kop
    for k in (3, 2, 1):
        kand = lijst(kort[:k])
        if len(kand) <= 38:                               # past op één regel
            opt_head = kand; break
    opt_head = opt_head or (opts[0][:44] + '.')
    kleur = v.get('table', {}).get('Kleur', '')
    velg = _velg(v)
    model = car['title'].split()[-1] if len(car['title'].split()) > 1 else car['title']
    if kleur and velg and len(f'{kleur} op {velg}.') <= 34:
        det_head = f'{_kap(kleur)} op {velg}.'
    else:
        det_head = f'De {model}, tot in het detail.'
    return opt_head, det_head


def concept(v):
    """Volledige, feitelijke carrousel-invoer zonder AI."""
    t = v['table']
    title, sub = splits_titel(v)
    model = title.split(' ', 1)[1] if ' ' in title else title
    short = 'deze ' + model.rstrip('!?.')
    if model.endswith('!'):
        short = 'deze ' + model[:-1]
    km = t.get('Kilometerstand', '').replace(' Km', ' km').replace(' KM', ' km')
    car = dict(
        id=v['id'], slug=v['slug'], url=v['url'], status='actief', review_nodig=False,
        folder=v['title'], site_title=v['title'], title=title, sub=sub or ' ', short=short,
        price=v['prijs'],
        specs={'Bouwjaar': t.get('Bouwjaar', ''), 'Kilometerstand': km,
               'Vermogen': _vermogen(t.get('Vermogen', '')), 'Transmissie': t.get('Transmissie', ''),
               'Brandstof': t.get('Brandstof', ''), 'Carrosserie': t.get('Carrosserievorm', t.get('Carrosserie', ''))},
        photos=kies_fotos(len(v['fotos'])), pos={},
    )
    kand = scoor_opties(v)
    car['optie_kandidaten'] = kand
    car['options'] = kand[:6]
    while len(car['options']) < 6:
        car['options'].append(['Rijklaar afgeleverd', 'Inruil mogelijk'][len(car['options']) % 2])  # zelden: < 6 opties
    car['opt_head'], car['det_head'] = koppen(car, v)
    car['det_cap'] = detail_feiten(v)
    car['intro'] = intro(car, v)
    car['merk_hashtags'] = merk_hashtags(car)
    car['bron'] = 'regels'
    return car


def intro(car, v):
    """Korte, feitelijke introductie (max. 2 zinnen). Variatie op basis van het voertuig."""
    s = car['specs']
    kort = [x for x in car['options'] if len(x) <= 26] + [x for x in car['options'] if len(x) > 26]
    o = [_klein(x) for x in kort[:2]]
    naam = f"{car['title']} {car['sub']}".strip()
    carr = (s.get('Carrosserie') or '').split('(')[0].strip().lower()
    h = int(hashlib.md5(car['id'].encode()).hexdigest(), 16)
    sjablonen = [
        f'Deze {naam} uit {s["Bouwjaar"]} staat nu bij ons in de showroom in Sneek. Uitgerust met onder meer {o[0]} en {o[1]}.',
        f'Nieuw in ons aanbod: een {naam} met {s["Kilometerstand"]} op de teller. Met onder andere {o[0]} en {o[1]}.',
        f'De {naam} uit {s["Bouwjaar"]} is nu te bezichtigen in Sneek. Inclusief {o[0]} en {o[1]}.',
        f'Deze {naam} is net binnengekomen bij CB Automobielen. Met {s["Vermogen"]} en onder meer {o[0]}.',
    ]
    if carr in ('stationwagon', 'suv', 'mpv'):
        sjablonen.append(f'Een ruime {carr} met {s["Kilometerstand"]}: de {naam} uit {s["Bouwjaar"]}. Met onder meer {o[0]} en {o[1]}.')
    return sjablonen[h % len(sjablonen)]


def merk_hashtags(car):
    def tag(x):
        return '#' + re.sub(r'[^0-9A-Za-zÀ-ÿ]', '', x)
    merk = car['title'].split()[0]
    tags = [tag(merk), tag(car['title'].replace(' ', ''))]
    if merk.lower().startswith('mercedes'):
        tags[0] = '#MercedesBenz'
    return list(dict.fromkeys(t for t in tags if len(t) > 2))
