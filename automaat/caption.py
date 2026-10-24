"""Instagram-caption in de vaste CB Automobielen-opbouw. Alle feiten komen rechtstreeks uit de data."""
import re
from . import config, content

MAX_LEN = 2200
MAX_TAGS = 30


def maak(car):
    s = car['specs']
    highlights = '\n'.join(f'- {o}' for o in car['options'][:4])
    tags = list(dict.fromkeys(config.VASTE_HASHTAGS + car.get('merk_hashtags', [])))[:12]
    url = car['url'].replace('https://', '').replace('http://', '')
    tekst = f"""🚗 NIEUW BINNEN BIJ CB AUTOMOBIELEN!

{car['site_title']}

{car['intro']}

📋 Specificaties:
- Bouwjaar: {s['Bouwjaar']}
- Kilometerstand: {s['Kilometerstand']}
- Brandstof: {s['Brandstof']}
- Transmissie: {s['Transmissie']}
- Vermogen: {s['Vermogen']}

✨ Highlights:
{highlights}

💰 Vraagprijs: {car['price']}

📍 CB Automobielen | Sneek

🌐 Bekijk deze auto op cbautomobielen.nl
{url}

📩 Interesse? Neem contact met ons op of stuur een DM!

{' '.join(tags)}"""
    return tekst


def controleer(tekst, car, v):
    """Geeft lijst met fouten terug (leeg = goed)."""
    f = []
    if len(tekst) > MAX_LEN:
        f.append(f'caption te lang ({len(tekst)} tekens)')
    if len(re.findall(r'#\w', tekst)) > MAX_TAGS:
        f.append('te veel hashtags')
    for veld, waarde in (('prijs', v['prijs']), ('bouwjaar', v['table'].get('Bouwjaar', '')),
                         ('kilometerstand', v['table'].get('Kilometerstand', '').replace(' Km', ' km'))):
        if not waarde or waarde not in tekst:
            f.append(f'{veld} "{waarde}" ontbreekt of wijkt af in caption')
    zonder_url = tekst.replace(car['url'].replace('https://', ''), '').replace(f"Ref. {v['id']}", '')
    for vast in ('0515 745 030', 'Edisonstraat 1c'):
        zonder_url = zonder_url.replace(vast, '')
    if not content.getallen_ok(zonder_url, v):
        extra = content._norm_num(zonder_url) - content.toegestane_getallen(v)
        f.append(f'caption bevat getallen die niet in de voertuigdata staan: {sorted(extra)}')
    if re.search(r'garantie', tekst, re.I) and 'garantie' not in ' '.join(v.get('opties', [])).lower():
        f.append('caption noemt garantie')
    if '—' in tekst:
        f.append('em dash in caption')
    if v['slug'] not in tekst and f"Ref. {v['id']}" not in tekst:
        f.append('referentienummer van de auto ontbreekt in de caption')
    if 'rijklaar' in tekst.lower() and not any('rijklaar' in o.lower() for o in v.get('opties', [])):
        f.append('caption noemt rijklaar, maar de website meldt dat niet')
    return f
