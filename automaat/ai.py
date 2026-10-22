"""Optioneel: Claude kiest de foto's en schrijft koppen/intro. Alleen actief met ANTHROPIC_API_KEY.

Elk veld wordt streng gecontroleerd (alleen bestaande opties, alleen getallen uit de data,
geen verboden claims). Afgekeurde velden blijven op de vaste regels uit content.py staan.
"""
import base64, io, json, os, re, urllib.request
from PIL import Image
from . import config, content

VERBODEN = re.compile(r'garantie|schadevrij|nieuwstaat|als nieuw|perfect|uniek|ongekend|droomauto|'
                      r'topstaat|nap\b|eerste eigenaar|1e eigenaar|dealeronderhouden|dealer-onderhouden|'
                      r'onderhoudshistorie|apk|—|–|!{2,}', re.I)

PROMPT = """Je bent de social-media-redacteur van CB Automobielen, occasiondealer in Sneek.
Je maakt de inhoud voor een vaste Instagram-carrousel van 5 slides voor precies deze ene auto.
Gebruik UITSLUITEND de voertuigdata hieronder. Verzin niets: geen opties, geen garantie,
geen onderhoudshistorie, geen staat-claims. Schrijf correct, zakelijk Nederlands, premium en rustig,
zonder overdreven verkooppraat, zonder uitroeptekens en zonder gedachtestreepjes.

VOERTUIGDATA (JSON):
{data}

FOTO'S: hieronder volgen de toegestane foto's, elk voorafgegaan door het nummer.
Kies per rol een fotonummer (elke foto maximaal één keer):
- hero: sterkste foto schuin van voren, hele auto zichtbaar
- specs: achterzijde schuin, hele auto zichtbaar
- options: interieur of dashboard
- d1: detail van velg of koplamp
- d2, d3: interieurdetail, stoelen, bagageruimte of badge
- contact: een andere foto van de voorkant/zijkant van de hele auto
Geef bij een foto eventueel een uitsnede "pos" als "X% Y%" (standaard "50% 50%").

Lever ALLEEN geldige JSON in dit formaat:
{{"photos": {{"hero": "04", "specs": "08", "options": "02", "d1": "09", "d2": "10", "d3": "11", "contact": "07"}},
 "pos": {{}},
 "options": [{{"bron": "<exacte optietekst uit de data>", "tekst": "<korte versie, max 30 tekens>"}}, ... precies 6],
 "opt_head": "<één korte zin met de 2 à 3 sterkste opties, max 46 tekens, eindigt met punt>",
 "det_head": "<korte feitelijke kop over uitvoering/kleur/velgen, max 34 tekens, eindigt met punt>",
 "det_cap": ["<feit 1, max 26 tekens>", "<feit 2>", "<feit 3>"],
 "intro": "<maximaal twee zinnen, max 240 tekens, feitelijk en aantrekkelijk>",
 "hashtags": ["#Merk", "#MerkModel", "... max 4 merk/model-hashtags"]}}
De 6 opties moeten echte verkoopargumenten zijn (comfort, techniek, uitstraling), kies bij een praktische auto
voor gebruiksgemak en bij een sportieve auto voor prestaties."""


def _thumb(path):
    im = Image.open(path).convert('RGB')
    im.thumbnail((512, 512))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=72)
    return base64.b64encode(b.getvalue()).decode()


def _vraag(v, fotodir, toegestaan):
    data = {k: v[k] for k in ('title', 'prijs', 'table', 'bijzondere_opties', 'opties')}
    blocks = [{'type': 'text', 'text': PROMPT.format(data=json.dumps(data, ensure_ascii=False, indent=1))}]
    for nr in toegestaan:
        f = os.path.join(fotodir, nr + '.jpg')
        if os.path.exists(f):
            blocks.append({'type': 'text', 'text': f'Foto {nr}:'})
            blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': _thumb(f)}})
    body = json.dumps({'model': config.CLAUDE_MODEL, 'max_tokens': 2000,
                       'messages': [{'role': 'user', 'content': blocks}]}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=body, headers={
        'x-api-key': config.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    txt = ''.join(b.get('text', '') for b in r.get('content', []))
    m = re.search(r'\{.*\}', txt, re.S)
    return json.loads(m.group(0))


def _tekst_ok(t, v, maxlen):
    return isinstance(t, str) and 0 < len(t) <= maxlen and not VERBODEN.search(t) and content.getallen_ok(t, v)


def verrijk(car, v, fotodir):
    """Past car aan met gecontroleerde AI-velden. Geeft lijst met notities terug."""
    if not config.ANTHROPIC_API_KEY:
        return ['AI niet actief (geen ANTHROPIC_API_KEY): vaste regels gebruikt']
    notes = []
    toegestaan = content.toegestane_fotos(len(v['fotos']))
    try:
        a = _vraag(v, fotodir, toegestaan)
    except Exception as e:
        return [f'AI-aanroep mislukt, vaste regels gebruikt: {e}']

    # foto's
    p = a.get('photos', {})
    rollen = ['hero', 'specs', 'options', 'd1', 'd2', 'd3', 'contact']
    if all(p.get(r) in toegestaan for r in rollen) and len({p[r] for r in rollen}) == 7:
        car['photos'] = {r: p[r] for r in rollen}
        car['pos'] = {k: s for k, s in (a.get('pos') or {}).items()
                      if k in rollen and re.fullmatch(r'\d{1,3}% \d{1,3}%', str(s))}
        notes.append('fotokeuze: AI')
    else:
        notes.append('fotokeuze AI afgekeurd: vaste keuze')

    # opties: bron moet exact bestaan, korte tekst mag geen nieuwe getallen bevatten
    bronnen = set(v.get('opties', [])) | set(v.get('bijzondere_opties', []))
    ok = []
    for o in a.get('options', []):
        b, t = (o or {}).get('bron', ''), (o or {}).get('tekst', '')
        if b in bronnen and _tekst_ok(t, v, 32) and content._norm_num(t) <= content._norm_num(b):
            ok.append(content._kap(t.strip()))
    ok = list(dict.fromkeys(ok))
    if len(ok) >= 4:
        gebruikt_bron = {(o or {}).get('bron', '') for o in a.get('options', [])}
        for o in car['options']:            # aanvullen met vaste keuze (echte opties)
            if len(ok) >= 6: break
            if o not in ok and o not in gebruikt_bron:
                ok.append(o)
        car['options'] = ok[:6]
        notes.append('opties: AI' + (' (aangevuld met vaste keuze)' if len(ok) and len(ok) < 6 else ''))
    else:
        notes.append(f'opties AI afgekeurd ({len(ok)}/6 geldig): vaste keuze')

    for veld, maxlen in (('opt_head', 46), ('det_head', 34)):
        if _tekst_ok(a.get(veld), v, maxlen):
            car[veld] = a[veld].strip()
        else:
            notes.append(f'{veld} AI afgekeurd')
    cap = a.get('det_cap') or []
    if len(cap) == 3 and all(_tekst_ok(x, v, 26) for x in cap):
        car['det_cap'] = [x.strip() for x in cap]
    else:
        notes.append('det_cap AI afgekeurd')
    it = a.get('intro', '')
    if _tekst_ok(it, v, 240) and len(re.findall(r'[.!?](\s|$)', it)) <= 2:
        car['intro'] = it.strip()
    else:
        notes.append('intro AI afgekeurd')
    tags = [t for t in a.get('hashtags', []) if re.fullmatch(r'#[0-9A-Za-zÀ-ÿ]{2,30}', str(t))][:4]
    if tags:
        car['merk_hashtags'] = list(dict.fromkeys(tags))
    car['bron'] = 'ai+controle'
    return notes
