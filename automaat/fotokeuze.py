"""Gratis automatische fotokeuze met een open beeldherkenningsmodel (OpenAI CLIP via open_clip, draait lokaal).

Elke foto krijgt een type (voorkant schuin, achterkant schuin, dashboard, velg, koplamp, bagageruimte, ...).
Daarna krijgt elke slide-rol de best passende foto. Lukt het model niet (niet geïnstalleerd, fout),
dan blijft de vaste keuze uit content.kies_fotos() staan. Er worden nooit beelden gewijzigd of gemaakt.
"""
import os
from . import content

TYPES = {
    'voor_schuin':  'a photo of a whole car seen from the front three-quarter angle, parked outside',
    'voor_recht':   'a photo of a whole car seen straight from the front',
    'zij':          'a photo of a whole car seen from the side',
    'achter_schuin': 'a photo of a whole car seen from the rear three-quarter angle',
    'achter_recht': 'a photo of a whole car seen straight from the back',
    'dashboard':    'a photo of a car interior with dashboard and steering wheel',
    'stoelen':      'a photo of car seats in the interior of a car',
    'achterbank':   'a photo of the rear seats of a car',
    'bagage':       'a photo of an open car trunk luggage compartment',
    'scherm':       'a close-up photo of a car infotainment touchscreen display',
    'tellers':      'a close-up photo of a car instrument cluster',
    'velg':         'a close-up photo of a car wheel and alloy rim',
    'koplamp':      'a close-up photo of a car headlight',
    'achterlicht':  'a close-up photo of a car tail light',
    'embleem':      'a close-up photo of a car badge emblem logo',
    'motor':        'a photo of a car engine bay',
    'stuur':        'a close-up photo of a car steering wheel',
    'lak_detail':   'a close-up photo of car paint, a door or body panel, not the whole car',
    'versnelling':  'a close-up photo of a car gear shifter',
    'persoon':      'a photo of a person',
    'gebouw':       'a photo of a car dealership building or showroom',
    'document':     'a photo of documents, keys or a service book',
}

ROLLEN = {
    'hero':    ['voor_schuin', 'voor_recht'],
    'specs':   ['achter_schuin', 'achter_recht', 'zij'],
    'options': ['dashboard', 'stoelen'],
    'd1':      ['velg', 'koplamp'],
    'd2':      ['stoelen', 'bagage', 'achterbank', 'scherm', 'tellers', 'embleem', 'achterlicht', 'koplamp', 'velg'],
    'd3':      ['embleem', 'bagage', 'achterlicht', 'stoelen', 'scherm', 'tellers', 'versnelling', 'velg', 'koplamp'],
    'contact': ['voor_schuin', 'zij', 'voor_recht'],
}
NOOIT = {'persoon', 'gebouw', 'document', 'motor'}
HELE_AUTO = {'voor_schuin', 'voor_recht', 'zij', 'achter_schuin', 'achter_recht'}

# Aparte voor/achter-controle: het algemene model haalt 'schuin voor' en 'schuin achter' soms door elkaar.
VOOR_ACHTER = ['a photo of the front of a car, showing the headlights, the front grille and the front bumper',
               'a photo of the back of a car, showing the tail lights, the tailgate and the rear bumper']
MIN_VOORKANT = 0.70     # zekerheid dat de coverfoto de voorkant van de auto laat zien

_model = None
_va = None


def _laad():
    global _model
    if _model is None:
        import torch, open_clip
        torch.set_num_threads(max(os.cpu_count() or 2, 2))
        m, _, pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
        tok = open_clip.get_tokenizer('ViT-B-32')
        m.eval()
        with torch.no_grad():
            t = m.encode_text(tok(list(TYPES.values())))
            t = t / t.norm(dim=-1, keepdim=True)
        _model = (m, pre, t)
    return _model


def classificeer(fotodir, nummers):
    """{nr: (type, zekerheid, {type: score})}"""
    import torch
    from PIL import Image
    m, pre, t = _laad()
    namen = list(TYPES)
    uit = {}
    with torch.no_grad():
        for nr in nummers:
            p = os.path.join(fotodir, nr + '.jpg')
            if not os.path.exists(p):
                continue
            x = pre(Image.open(p).convert('RGB')).unsqueeze(0)
            f = m.encode_image(x); f = f / f.norm(dim=-1, keepdim=True)
            pr = (100.0 * f @ t.T).softmax(dim=-1)[0].tolist()
            scores = dict(zip(namen, pr))
            best = max(scores, key=scores.get)
            uit[nr] = (best, scores[best], scores)
    return uit


def voorkant_kans(fotodir, nummers):
    """{nr: kans (0-1) dat de foto de VOORKANT van de auto toont (t.o.v. de achterkant)}"""
    global _va
    import torch, open_clip
    from PIL import Image
    m, pre, _ = _laad()
    if _va is None:
        with torch.no_grad():
            t = m.encode_text(open_clip.get_tokenizer('ViT-B-32')(VOOR_ACHTER))
            _va = t / t.norm(dim=-1, keepdim=True)
    uit = {}
    with torch.no_grad():
        for nr in nummers:
            p = os.path.join(fotodir, nr + '.jpg')
            if not os.path.exists(p):
                continue
            f = m.encode_image(pre(Image.open(p).convert('RGB')).unsqueeze(0)); f = f / f.norm(dim=-1, keepdim=True)
            uit[nr] = (100.0 * f @ _va.T).softmax(dim=-1)[0].tolist()[0]
    return uit


def kies_cover(labels, vk, bruikbaar):
    """Coverfoto: altijd een hele auto van VOREN (schuin of recht). Geeft (nr, zekerheid)."""
    kand = []
    for nr, l in bruikbaar.items():
        if l[0] not in HELE_AUTO or l[0] in ('achter_schuin', 'achter_recht') or nr not in vk:
            continue
        vooraanzicht = l[2]['voor_schuin'] + l[2]['voor_recht']
        bonus = 0.05 if nr == '04' else 0       # dealervolgorde licht laten meetellen
        kand.append((vk[nr] >= MIN_VOORKANT, vk[nr] * (0.5 + vooraanzicht) + bonus, nr))
    if not kand:   # niets als vooraanzicht herkend: de foto die het zekerst de voorkant toont
        kand = [(vk[nr] >= MIN_VOORKANT, vk[nr], nr) for nr, l in bruikbaar.items() if l[0] in HELE_AUTO and nr in vk]
    if not kand:
        return None, 0.0
    _, _, nr = max(kand)
    return nr, vk[nr]


def kies(car, v, fotodir):
    """Past car['photos'] aan op basis van herkenning. Geeft (notities, labels) terug."""
    n = len(v['fotos'])
    toegestaan = content.toegestane_fotos(n)
    try:
        labels = classificeer(fotodir, toegestaan + ['01'])
    except Exception as e:
        return [f'fotoherkenning niet beschikbaar ({type(e).__name__}: {e}); vaste fotokeuze'], {}
    bruikbaar = {nr: l for nr, l in labels.items() if l[0] not in NOOIT and nr != '01'}
    gekozen, gebruikt = {}, set()
    try:
        vk = voorkant_kans(fotodir, [nr for nr, l in labels.items() if l[0] in HELE_AUTO])
    except Exception as e:
        return [f'voor/achter-controle niet beschikbaar ({e}); vaste fotokeuze'], {}
    hero, zeker = kies_cover(labels, vk, bruikbaar)
    car['cover_voorkant'] = round(zeker, 2)
    if hero:
        gekozen['hero'] = hero; gebruikt.add(hero)

    def beste(rol, voorkeur_nr=None):
        voorkeur = ROLLEN[rol]
        if voorkeur_nr and voorkeur_nr in bruikbaar and bruikbaar[voorkeur_nr][0] in voorkeur and voorkeur_nr not in gebruikt:
            return voorkeur_nr          # dealervolgorde respecteren als die klopt (bv. hero = foto 04)
        for typ in voorkeur:
            kand = [(l[2][typ], nr) for nr, l in bruikbaar.items() if l[0] == typ and nr not in gebruikt]
            if kand:
                return max(kand)[1]
        # geen foto met dit type als beste: hoogste score op de voorkeurstypes
        hele = rol in ('hero', 'specs', 'contact')
        kand = [(max(l[2][t] for t in voorkeur), nr) for nr, l in bruikbaar.items()
                if nr not in gebruikt and (not hele or l[0] in HELE_AUTO)]
        return max(kand)[1] if kand else None

    for rol, pref in (('hero', '04'), ('specs', '03'), ('options', None), ('d1', None),
                      ('d2', None), ('d3', None), ('contact', '07')):
        if rol == 'hero' and 'hero' in gekozen:
            continue
        if rol == 'contact' and labels.get('01', ('',))[0] in ('voor_schuin', 'voor_recht', 'zij'):
            gekozen[rol] = '01'; continue   # andere hoek dan de cover; watermerk valt weg door bovenuitsnede
        nr = beste(rol, pref)
        if nr is None:
            return ['te weinig bruikbare foto\'s voor herkenning; vaste fotokeuze'], labels
        gekozen[rol] = nr; gebruikt.add(nr)
    car['photos'] = gekozen
    car['pos'] = {}
    if gekozen['contact'] == '01':
        car['pos']['contact'] = '50% 0%'
    elif labels.get(gekozen['contact'], ('',))[0] == 'voor_schuin':
        car['pos']['contact'] = '50% 40%'
    beschrijving = ', '.join(f"{r}={nr} ({labels[nr][0]})" for r, nr in gekozen.items())
    car['_voorkant'] = {nr: round(x, 2) for nr, x in vk.items()}
    return [f'fotokeuze via herkenning: {beschrijving}', f"cover {gekozen['hero']}: voorkant-zekerheid {zeker:.2f}"], labels


def contactsheet(fotodir, labels, gekozen, doel, _vk=None):
    """Overzicht van alle foto's met herkend type en gekozen rol (voor controle)."""
    from PIL import Image, ImageDraw
    nrs = sorted(labels)
    if not nrs:
        return
    rol_van = {nr: r for r, nr in gekozen.items()}
    w, h, kol = 300, 225, 6
    rij = (len(nrs) + kol - 1) // kol
    sheet = Image.new('RGB', (kol * w, rij * (h + 40)), (12, 14, 18))
    d = ImageDraw.Draw(sheet)
    for i, nr in enumerate(nrs):
        im = Image.open(os.path.join(fotodir, nr + '.jpg')).convert('RGB'); im.thumbnail((w, h))
        x, y = (i % kol) * w, (i // kol) * (h + 40)
        sheet.paste(im, (x, y))
        t, z, _ = labels[nr]
        if _vk and nr in _vk:
            t += f' v{_vk[nr]:.2f}'
        kleur = (235, 91, 40) if nr in rol_van else (179, 182, 187)
        d.text((x + 4, y + h + 4), f"{nr} {t} {z:.2f}" + (f"  -> {rol_van[nr]}" if nr in rol_van else ''), fill=kleur)
    sheet.save(doel, quality=80)
