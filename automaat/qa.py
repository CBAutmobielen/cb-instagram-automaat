"""Automatische kwaliteitscontrole vóór iedere publicatie. Elke functie geeft een lijst met fouten terug."""
import os, json, hashlib
from PIL import Image, ImageChops, ImageStat
from . import config

LOGO_BOX = (70, 1270, 360, 1312)
LOGO_REF = os.path.join(config.ROOT, 'assets', 'qa_logo_ref.png')


def site_actueel(car, vers, listing_item):
    """Staat de auto nog op de site, is hij beschikbaar en kloppen prijs/bouwjaar/km?"""
    f = []
    if not listing_item:
        f.append('auto staat niet (meer) in het aanbod op de website')
    elif not listing_item['beschikbaar']:
        f.append('auto is niet meer beschikbaar (Op aanvraag / verkocht)')
    if vers.get('op_aanvraag') or not vers.get('prijs'):
        f.append('voertuigpagina toont geen vraagprijs (verkocht?)')
    if vers.get('prijs') != car['price']:
        f.append(f"prijs wijkt af: slide {car['price']} vs site {vers.get('prijs')}")
    t = vers.get('table', {})
    if t.get('Bouwjaar', '') != car['specs']['Bouwjaar']:
        f.append(f"bouwjaar wijkt af: {car['specs']['Bouwjaar']} vs {t.get('Bouwjaar')}")
    km = t.get('Kilometerstand', '').replace(' Km', ' km').replace(' KM', ' km')
    if km != car['specs']['Kilometerstand']:
        f.append(f"kilometerstand wijkt af: {car['specs']['Kilometerstand']} vs {km}")
    if vers['id'] != car['id']:
        f.append('voertuig-ID wijkt af')
    return f


def fotos_herkomst(car, vers, fotodir):
    """Elke gebruikte foto moet uit de galerij van precies deze auto komen en ongewijzigd zijn."""
    f = []
    hk_path = os.path.join(fotodir, 'herkomst.json')
    if not os.path.exists(hk_path):
        return ['herkomst van foto\'s onbekend']
    hk = json.load(open(hk_path))
    galerij = set(vers['fotos'])
    gebruikt = list(car['photos'].values())
    if len(set(gebruikt)) != len(gebruikt):
        f.append('dezelfde foto wordt meerdere keren gebruikt')
    for rol, nr in car['photos'].items():
        p = os.path.join(fotodir, nr + '.jpg')
        h = hk.get(nr)
        if not h or not os.path.exists(p):
            f.append(f'foto {nr} ({rol}) ontbreekt'); continue
        if h['url'] not in galerij:
            f.append(f'foto {nr} ({rol}) hoort niet bij de galerij van deze auto')
        if hashlib.sha1(open(p, 'rb').read()).hexdigest() != h['sha1']:
            f.append(f'foto {nr} ({rol}) is gewijzigd na downloaden')
        try:
            im = Image.open(p)
            if min(im.size) < 600:
                f.append(f'foto {nr} ({rol}) te lage resolutie {im.size}')
        except Exception as e:
            f.append(f'foto {nr} ({rol}) onleesbaar: {e}')
    return f


def slides(paden, render_issues):
    f = list(f'tekst/uitlijning: {i}' for i in render_issues)
    if len(paden) != 5:
        f.append(f'{len(paden)} slides gegenereerd in plaats van 5')
    ref = Image.open(LOGO_REF).convert('RGB') if os.path.exists(LOGO_REF) else None
    for p in paden:
        try:
            im = Image.open(p).convert('RGB')
        except Exception as e:
            f.append(f'{os.path.basename(p)} onleesbaar: {e}'); continue
        if im.size != (1080, 1350):
            f.append(f'{os.path.basename(p)} heeft formaat {im.size} i.p.v. 1080x1350')
        if ref is not None:
            diff = ImageStat.Stat(ImageChops.difference(im.crop(LOGO_BOX), ref)).mean
            if sum(diff) / 3 > 1.5:
                f.append(f'{os.path.basename(p)}: CB Automobielen-logo niet correct zichtbaar (afwijking {sum(diff)/3:.1f})')
        # foto-vlak mag niet leeg/zwart zijn (mislukte foto)
        top = ImageStat.Stat(im.crop((72, 72, 1008, 700)).convert('L'))
        if top.stddev[0] < 8:
            f.append(f'{os.path.basename(p)}: fotovlak lijkt leeg')
    return f


def dubbel(car, db, ig_recent):
    f = []
    v = db['voertuigen'].get(car['id'])
    if v and v.get('instagram_post_id'):
        f.append(f"auto is al gepubliceerd (post {v['instagram_post_id']})")
    for m in ig_recent or []:
        cap = m.get('caption') or ''
        if car['slug'] in cap or f"/{car['id']}" in cap or car['url'].replace('https://', '') in cap:
            f.append(f"auto staat al op Instagram: {m.get('permalink') or m.get('id')}")
            break
    return f
