"""End-to-end test zonder internet: website, Instagram en hosting worden nagebootst.

  python tests/test_lokaal.py

Gebruikt de echte render-engine, content, captions, QA, database en wachtrijlogica.
Scenario's: eerste run, nieuwe auto's, max 1 post per dag, verkocht uit wachtrij, prijswijziging,
herstel na onderbroken publicatie, dubbele-postbeveiliging, foute fotokeuze wordt geblokkeerd.
"""
import os, sys, json, shutil, tempfile, glob
from datetime import datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from automaat import config, db as dbm, site, ai, hosting, fotokeuze, run as runner

KIT = {c['id'] if 'id' in c else c['slug'].rsplit('-', 1)[1]: c for c in json.load(open(os.path.join(ROOT, 'cb', 'cars.json'), encoding='utf-8'))}
TMP = tempfile.mkdtemp(prefix='cbtest_')
config.DB_PATH = os.path.join(TMP, 'database.json'); config.REPORT_DIR = os.path.join(TMP, 'rapport')
config.WORK_DIR = os.path.join(TMP, 'werk'); config.PUBLISH_DIR = os.path.join(TMP, 'gepubliceerd')
config.GITHUB_REPOSITORY = 'test/cb'
config.ROOT = TMP  # proefbestanden niet in de echte map
config.PUBLICATIE_DAGEN = list(range(7))
DAG = ['2026-10-23 08:01']
config.nu = lambda: datetime.strptime(DAG[0], '%Y-%m-%d %H:%M').replace(tzinfo=config.TZ)
config.vandaag = lambda: DAG[0][:10]
N = 32


def vdata(vid, prijs=None):
    c = KIT[vid]; s = c['specs']
    extra = ['Cruise control', 'Climate control', 'Parkeersensoren voor en achter', 'Elektrische ramen voor', 'Centrale vergrendeling met afstandsbediening', 'Stuurbekrachtiging',
             'Bluetooth telefoonvoorbereiding', 'Boordcomputer', 'Isofix bevestigingspunten']
    return {'slug': c['slug'], 'id': vid, 'url': c['url'], 'title': c['site_title'],
            'table': {'Bouwjaar': s['Bouwjaar'], 'Kilometerstand': s['Kilometerstand'].replace(' km', ' Km'),
                      'Vermogen': s['Vermogen'], 'Transmissie': s['Transmissie'], 'Brandstof': s['Brandstof'],
                      'Carrosserievorm': s['Carrosserie']},
            'bijzondere_opties': c['options'][:2], 'opties': c['options'][2:] + extra,
            'prijs': '' if vid in ZONDER_PRIJS else (prijs or c['price']), 'op_aanvraag': vid in ZONDER_PRIJS,
            'marktplaats': MP.get(vid),
            'fotos': [f'https://cdn1.grbx.app/images/{vid}-{i:02d}/full.jpg' for i in range(1, FOTOS.get(vid, N) + 1)]}


LISTING = {}
PRIJS = {}
FOTOS = {}          # aantal foto's per auto (standaard N)
ZONDER_PRIJS = set()  # auto's die 'Op aanvraag' staan
MP = {}             # Marktplaats-link per auto


def zet_listing(ids, verkocht=()):
    LISTING.clear()
    for vid in ids:
        c = KIT[vid]
        LISTING[vid] = {'slug': c['slug'], 'url': c['url'], 'tekst': c['site_title'],
                        'beschikbaar': vid not in verkocht and vid not in ZONDER_PRIJS,
                        'prijs': None if (vid in verkocht or vid in ZONDER_PRIJS) else PRIJS.get(vid, c['price']),
                        'km': c['specs']['Kilometerstand']}


site.aanbod = lambda: json.loads(json.dumps(LISTING))
site.voertuig = lambda slug: vdata(slug.rsplit('-', 1)[1], PRIJS.get(slug.rsplit('-', 1)[1]))


def fake_download(v, folder):
    os.makedirs(folder, exist_ok=True); hk = {}
    import hashlib
    src = os.path.join(ROOT, 'photos', v['slug'])
    for i, u in enumerate(v['fotos'], 1):
        f = os.path.join(src, f'{i:02d}.jpg')
        if os.path.exists(f):
            shutil.copy(f, os.path.join(folder, f'{i:02d}.jpg'))
            hk[f'{i:02d}'] = {'url': u, 'sha1': hashlib.sha1(open(f, 'rb').read()).hexdigest()}
    json.dump(hk, open(os.path.join(folder, 'herkomst.json'), 'w'))
site.download_fotos = fake_download

AI_AAN = [True]
def fake_ai(car, v, fotodir):
    """Bootst de AI-fotokeuze na met de door een mens gemaakte keuze uit de kit."""
    if not AI_AAN[0]:
        return ['herkenning niet actief: vaste fotokeuze'], {}
    k = KIT[car['id']]; car['photos'] = dict(k['photos']); car['pos'] = dict(k.get('pos', {}))
    return ['fotokeuze: (nagebootste) herkenning'], {}
fotokeuze.kies = fake_ai

hosting.commit_push = lambda msg, paden: 'sha123'
hosting.publiceer_beelden = lambda jpgs, sha: [f'https://example/{os.path.basename(j)}' for j in jpgs]


class FakeIG:
    posts = []
    def __init__(self): pass
    def verbind(self): return {'username': 'cbautomobielen'}
    def vernieuw_token(self): return 'recent vernieuwd'
    def limiet(self): return {'quota_usage': len(self.posts), 'config': {'quota_total': 100}}
    def recente_posts(self, n=50): return list(reversed(self.posts))[:n]
    def maak_carrousel(self, urls, cap):
        assert len(urls) == 5, urls
        return 'container1'
    stories = []
    def controleer_post(self, mid, n, ref): return ''
    def maak_story(self, url): return 'story1'
    faal = [0]
    def publiceer(self, cid):
        if FakeIG.faal[0]:
            FakeIG.faal[0] -= 1; raise RuntimeError('Instagram API: tijdelijke storing (nagebootst)')
        if cid == 'story1':
            FakeIG.stories.append(cid); return f's{len(FakeIG.stories)}', None
        mid = f'1789{len(self.posts)}'
        FakeIG.posts.append({'id': mid, 'caption': FakeIG.laatste_caption, 'permalink': f'https://instagram.com/p/{mid}'})
        return mid, f'https://instagram.com/p/{mid}'

import automaat.instagram as igmod
igmod.Instagram = FakeIG
config.IG_TOKEN_SECRET = 'x'; config.IG_USER_ID = '1'
_orig_cap = runner.content_v2.caption
def _cap(*a, **k):
    t, o = _orig_cap(*a, **k); FakeIG.laatste_caption = t; return t, o
runner.content_v2.caption = _cap


def draai(modus, auto=''):
    sys.argv = ['run', '--modus', modus] + (['--auto', auto] if auto else [])
    code = runner.main()
    return code, dbm.laad()


OK = []
def check(naam, cond, info=''):
    print(('  OK   ' if cond else '  FOUT ') + naam + (f'  [{info}]' if info and not cond else ''))
    OK.append(bool(cond))


FIAT, GTI, POLO, UP = '941609', '937307', '942143', '948219'

print('\n=== Dag 1: eerste ingebruikname (3 auto\'s staan al op de site) ===')
AMG = '939529'
FOTOS[AMG] = 2      # stond al op de site, maar nog met een 'verwacht'-plaatje
zet_listing([POLO, UP, '930282', AMG])
code, db = draai('dagelijks')
check('verkoopklare bestaande auto\'s als "bestaand"', all(db['voertuigen'][x]['status'] == 'bestaand' for x in (POLO, UP, '930282')))
check('bestaande auto zonder echte foto\'s: "niet_klaar" (wordt later alsnog gepost)', db['voertuigen'][AMG]['status'] == 'niet_klaar',
      db['voertuigen'][AMG]['status'])
check('niets gepubliceerd', not FakeIG.posts)

print('\n=== Dag 2: twee nieuwe auto\'s verschijnen ===')
DAG[0] = '2026-10-24 08:02'
zet_listing([POLO, UP, '930282', FIAT, GTI])
os.environ['PUBLICATIE'] = 'aan'
code, db = draai('dagelijks')
check('exitcode 0', code == 0, code)
check('precies 1 post geplaatst', len(FakeIG.posts) == 1, len(FakeIG.posts))
gepub = [v for v in db['voertuigen'].values() if v['status'] == 'gepubliceerd']
check('oudste in wachtrij (GTI) gepubliceerd met post-ID', len(gepub) == 1 and gepub[0]['id'] == GTI and gepub[0]['instagram_post_id'])
check('Fiat staat in wachtrij, gepland morgen', db['voertuigen'][FIAT]['status'] == 'wachtrij' and db['voertuigen'][FIAT]['gepland'] == '2026-10-25',
      db['voertuigen'][FIAT].get('gepland'))
check('caption bevat directe link', GTI in FakeIG.posts[0]['caption'])
check('geen story (staat standaard uit)', len(FakeIG.stories) == 0)

print('\n=== Dag 2, nogmaals gestart (handmatig live) ===')
code, db = draai('live')
check('geen tweede post op dezelfde dag', len(FakeIG.posts) == 1, len(FakeIG.posts))

print('\n=== Dag 3: Fiat verkocht, GTI in prijs verlaagd ===')
DAG[0] = '2026-10-25 08:03'
PRIJS[GTI] = '€ 29.950'
zet_listing([POLO, UP, '930282', FIAT, GTI], verkocht=[FIAT])
code, db = draai('dagelijks')
check('Fiat uit wachtrij (verkocht)', db['voertuigen'][FIAT]['status'] == 'verkocht')
check('GTI prijswijziging geregistreerd, geen nieuwe post', db['voertuigen'][GTI]['wijzigingen'] and len(FakeIG.posts) == 1)

print('\n=== Dag 4: Fiat weer beschikbaar, maar al eerder op Instagram gezet (database kwijt-scenario) ===')
DAG[0] = '2026-10-26 08:01'
FakeIG.posts.append({'id': '999', 'caption': 'oude post ' + KIT[FIAT]['url'], 'permalink': 'https://instagram.com/p/999'})
zet_listing([POLO, UP, '930282', FIAT, GTI])
code, db = draai('dagelijks')
check('dubbele post geblokkeerd', len(FakeIG.posts) == 2 and db['voertuigen'][FIAT]['status'] != 'gepubliceerd')
FakeIG.posts.pop()

print('\n=== Herstel na onderbroken publicatie ===')
db = dbm.laad(); db['voertuigen'][FIAT]['status'] = 'bezig'; db['voertuigen'][FIAT]['pogingen'] = 0; dbm.bewaar(db)
FakeIG.posts.append({'id': '555', 'caption': 'x ' + KIT[FIAT]['url'], 'permalink': 'https://instagram.com/p/555'})
DAG[0] = '2026-10-27 08:01'
code, db = draai('dagelijks')
check('onderbroken publicatie herkend als gepubliceerd', db['voertuigen'][FIAT]['status'] == 'gepubliceerd' and db['voertuigen'][FIAT]['instagram_post_id'] == '555')

print('\n=== Foute fotokeuze (zonder AI, foto\'s ontbreken) wordt geblokkeerd ===')
AI_AAN[0] = False
zet_listing([POLO, UP, '930282', FIAT, GTI, '949714'])
DAG[0] = '2026-10-28 08:01'
n0 = len(FakeIG.posts)
code, db = draai('dagelijks')
check('niet gepubliceerd bij ontbrekende foto\'s, fout geregistreerd', len(FakeIG.posts) == n0 and db['voertuigen']['949714']['fouten'] and code == 1)
AI_AAN[0] = True

print('\n=== Proefrun met bestaande auto (niets publiceren) ===')
n0 = len(FakeIG.posts)
code, db = draai('proef', '949714')
check('proef geslaagd zonder publicatie', code == 0 and len(FakeIG.posts) == n0)

print('\n=== Wachtrij-maximum en tekstregels ===')
db = dbm.laad()
db['voertuigen']['949714'].update(status='wachtrij', pogingen=0, ontdekt='2026-09-01')
dbm.bewaar(db)
DAG[0] = '2026-10-30 08:01'
code, db = draai('dagelijks')
check('auto die lang in de wachtrij stond wordt niet overgeslagen maar gepost', db['voertuigen']['949714']['status'] == 'gepubliceerd',
      db['voertuigen']['949714']['status'])
from automaat import content_v2, caption as capmod
vv = vdata(FIAT); vv['opties'] = [o for o in vv['opties'] if 'ijklaar' not in o]
c2 = content_v2.maak_v2(vv, nieuw=False)
check('label "Nu beschikbaar" voor oudere auto', c2['label'] == 'Nu beschikbaar')
check('geen "rijklaar" als de website het niet meldt', not c2['rijklaar'] and 'rijklaar' not in content_v2.caption(vv, c2)[0].lower())
car_t = dict(url=vv['url'], id=FIAT)
check('caption-controle weigert onterecht "rijklaar"', any('rijklaar' in f for f in capmod.controleer(content_v2.caption(vv, c2)[0] + ' rijklaar', car_t, vv)))


# ---------------------------------------------------------------------------------------------
config.PUBLICATIE_DAGEN = [1, 4]   # vanaf hier zoals in het echt: alleen dinsdag en vrijdag
IB = '945297'
def dag(d, ids):
    DAG[0] = d + ' 08:01'; zet_listing(ids); return draai('dagelijks')
BASIS = [POLO, UP, '930282', FIAT, GTI, '949714']

print('\n=== Voorbeeld uit de opdracht: ma zonder prijs/foto\'s, di gezien, do prijs+foto\'s+Marktplaats, vr gepost ===')
n0 = len(FakeIG.posts)
ZONDER_PRIJS.add(IB); FOTOS[IB] = 1
code, db = dag('2026-11-02', BASIS + [IB])          # maandag
check('ma: Ibiza zonder prijs/foto\'s staat op "niet_klaar"', db['voertuigen'][IB]['status'] == 'niet_klaar')
code, db = dag('2026-11-03', BASIS + [IB])          # dinsdag (publicatiedag)
check('di: gezien maar niet gepost (niet verkoopklaar)', db['voertuigen'][IB]['status'] == 'niet_klaar' and len(FakeIG.posts) == n0)
code, db = dag('2026-11-04', BASIS + [IB])          # woensdag
ZONDER_PRIJS.discard(IB); FOTOS[IB] = 32; MP[IB] = 'https://www.marktplaats.nl/v/auto-s/seat/m123-seat-ibiza'
code, db = dag('2026-11-05', BASIS + [IB])          # donderdag: geen publicatiedag
v = db['voertuigen'][IB]
check('do: verkoopklaar herkend -> wachtrij, nog niet gepost (geen publicatiedag)', v['status'] == 'wachtrij' and len(FakeIG.posts) == n0, v['status'])
check('Marktplaats vastgelegd als extra signaal', v['klaar']['marktplaats'])
code, db = dag('2026-11-06', BASIS + [IB])          # vrijdag
v = db['voertuigen'][IB]
check('vr: Ibiza gepost', v['status'] == 'gepubliceerd' and v['instagram_post_id'] and len(FakeIG.posts) == n0 + 1, v['status'])
check('"op de site sinds" bewaard (ma), "nieuw" telt vanaf verkoopklaar (do)', v['eerst_op_site'] == '2026-11-02' and v['ontdekt'] == '2026-11-05')

print('\n=== Gepost: prijs en foto\'s veranderen -> NIET opnieuw posten ===')
PRIJS[IB] = '€ 6.950'; FOTOS[IB] = 20
n0 = len(FakeIG.posts)
code, db = dag('2026-11-10', BASIS + [IB])
check('geen tweede post na prijs-/fotowijziging', len(FakeIG.posts) == n0 and db['voertuigen'][IB]['status'] == 'gepubliceerd')

print('\n=== Auto die weken zonder prijs op de site stond, daarna verkoopklaar zonder Marktplaats ===')
Q3 = '917880'
ZONDER_PRIJS.add(Q3)
code, db = dag('2026-11-11', BASIS + [IB, Q3])
code, db = dag('2026-12-01', BASIS + [IB, Q3])      # 3 weken later nog steeds zonder prijs
check('na weken zonder prijs nog steeds "niet_klaar", niet vergeten', db['voertuigen'][Q3]['status'] == 'niet_klaar')
ZONDER_PRIJS.discard(Q3)
FakeIG.faal[0] = 1                                   # eerste publicatiepoging mislukt bij Instagram
n0 = len(FakeIG.posts)
code, db = dag('2026-12-04', BASIS + [IB, Q3])      # vrijdag
v = db['voertuigen'][Q3]
check('mislukte post NIET als geplaatst geregistreerd', not v.get('instagram_post_id') and v['status'] != 'gepubliceerd' and len(FakeIG.posts) == n0,
      v['status'])
code, db = dag('2026-12-08', BASIS + [IB, Q3])      # dinsdag: opnieuw
v = db['voertuigen'][Q3]
check('volgende publicatiedag alsnog gepost, precies 1 keer', v['status'] == 'gepubliceerd' and len(FakeIG.posts) == n0 + 1, v['status'])

print('\n=== Bestaande auto die bij de start nog een verwacht-plaatje had, krijgt echte foto\'s ===')
FOTOS[AMG] = 40
code, db = dag('2026-12-10', BASIS + [IB, Q3, AMG])
check('AMG nu in de wachtrij', db['voertuigen'][AMG]['status'] == 'wachtrij', db['voertuigen'][AMG]['status'])
code, db = dag('2026-12-11', BASIS + [IB, Q3, AMG])
check('AMG gepost op vrijdag', db['voertuigen'][AMG]['status'] == 'gepubliceerd')
check('oude, al verkoopklare voorraad niet als nieuw gepost', all(db['voertuigen'][x]['status'] == 'bestaand' for x in (POLO, UP, '930282')))
alle_refs = [p['caption'].split('Ref. ')[-1].split()[0] for p in FakeIG.posts if 'Ref. ' in (p['caption'] or '')]
check('geen enkele auto twee keer op Instagram', len(alle_refs) == len(set(alle_refs)), alle_refs)

uit = glob.glob(os.path.join(config.WORK_DIR, 'uitvoer', '*'))
print('\nUitvoer:', TMP)
for u in uit: print('  ', u)
print(f'\n{sum(OK)}/{len(OK)} controles geslaagd')
sys.exit(0 if all(OK) else 1)
