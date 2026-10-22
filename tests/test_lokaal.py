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
from automaat import config, db as dbm, site, ai, hosting, run as runner

KIT = {c['id'] if 'id' in c else c['slug'].rsplit('-', 1)[1]: c for c in json.load(open(os.path.join(ROOT, 'cb', 'cars.json'), encoding='utf-8'))}
TMP = tempfile.mkdtemp(prefix='cbtest_')
config.DB_PATH = os.path.join(TMP, 'database.json'); config.REPORT_DIR = os.path.join(TMP, 'rapport')
config.WORK_DIR = os.path.join(TMP, 'werk'); config.PUBLISH_DIR = os.path.join(TMP, 'gepubliceerd')
config.GITHUB_REPOSITORY = 'test/cb'
config.ROOT = TMP  # proefbestanden niet in de echte map
DAG = ['2026-10-23 08:01']
config.nu = lambda: datetime.strptime(DAG[0], '%Y-%m-%d %H:%M').replace(tzinfo=config.TZ)
config.vandaag = lambda: DAG[0][:10]
N = 32


def vdata(vid, prijs=None):
    c = KIT[vid]; s = c['specs']
    extra = ['Elektrische ramen voor', 'Centrale vergrendeling met afstandsbediening', 'Stuurbekrachtiging',
             'Bluetooth telefoonvoorbereiding', 'Boordcomputer', 'Isofix bevestigingspunten']
    return {'slug': c['slug'], 'id': vid, 'url': c['url'], 'title': c['site_title'],
            'table': {'Bouwjaar': s['Bouwjaar'], 'Kilometerstand': s['Kilometerstand'].replace(' km', ' Km'),
                      'Vermogen': s['Vermogen'], 'Transmissie': s['Transmissie'], 'Brandstof': s['Brandstof'],
                      'Carrosserievorm': s['Carrosserie']},
            'bijzondere_opties': c['options'][:2], 'opties': c['options'][2:] + extra,
            'prijs': prijs or c['price'], 'op_aanvraag': False,
            'fotos': [f'https://cdn1.grbx.app/images/{vid}-{i:02d}/full.jpg' for i in range(1, N + 1)]}


LISTING = {}
PRIJS = {}


def zet_listing(ids, verkocht=()):
    LISTING.clear()
    for vid in ids:
        c = KIT[vid]
        LISTING[vid] = {'slug': c['slug'], 'url': c['url'], 'tekst': c['site_title'],
                        'beschikbaar': vid not in verkocht, 'prijs': PRIJS.get(vid, c['price']), 'km': c['specs']['Kilometerstand']}


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
        return ['AI niet actief: vaste fotokeuze']
    k = KIT[car['id']]; car['photos'] = dict(k['photos']); car['pos'] = dict(k.get('pos', {}))
    return ['fotokeuze: (nagebootste) AI']
ai.verrijk = fake_ai

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
    def publiceer(self, cid):
        mid = f'1789{len(self.posts)}'
        FakeIG.posts.append({'id': mid, 'caption': FakeIG.laatste_caption, 'permalink': f'https://instagram.com/p/{mid}'})
        return mid, f'https://instagram.com/p/{mid}'

import automaat.instagram as igmod
igmod.Instagram = FakeIG
config.IG_TOKEN_SECRET = 'x'; config.IG_USER_ID = '1'
_orig_maak = runner.caption.maak
def _maak(car):
    t = _orig_maak(car); FakeIG.laatste_caption = t; return t
runner.caption.maak = _maak


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
zet_listing([POLO, UP, '930282'])
code, db = draai('dagelijks')
check('alle bestaande auto\'s als "bestaand"', all(v['status'] == 'bestaand' for v in db['voertuigen'].values()))
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

uit = glob.glob(os.path.join(config.WORK_DIR, 'uitvoer', '*'))
print('\nUitvoer:', TMP)
for u in uit: print('  ', u)
print(f'\n{sum(OK)}/{len(OK)} controles geslaagd')
sys.exit(0 if all(OK) else 1)
