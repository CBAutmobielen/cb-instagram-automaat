"""Centrale instellingen. Alles wat per omgeving verschilt komt uit omgevingsvariabelen / GitHub secrets."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = ZoneInfo('Europe/Amsterdam')

SITE_BASE = os.environ.get('CB_SITE', 'https://www.cbautomobielen.nl').rstrip('/')

STATE_DIR = os.path.join(ROOT, 'state')
DB_PATH = os.path.join(STATE_DIR, 'database.json')
TOKEN_STORE = os.path.join(STATE_DIR, 'ig_token.enc')
LOG_DIR = os.path.join(STATE_DIR, 'logs')
REPORT_DIR = os.path.join(ROOT, 'rapport')
WORK_DIR = os.path.join(ROOT, '.werk')            # tijdelijke bestanden (niet in git)
PUBLISH_DIR = os.path.join(ROOT, 'gepubliceerd')  # slides die Instagram ophaalt (wel in git)

# Publicatie
POSTS_PER_DAG = int(os.environ.get('CB_POSTS_PER_DAG', '1'))
PUBLICATIE_UUR = int(os.environ.get('PUBLICATIE_UUR') or os.environ.get('CB_PUBLICATIE_UUR') or '8')   # NL-tijd, GitHub-variabele
NIEUW_DAGEN = 14        # label 'Nieuw in voorraad' alleen zo lang na ontdekking
WACHTRIJ_WAARSCHUWING = 4   # meer auto's in de wachtrij = melding in het rapport (er wordt niets overgeslagen)
DAGNAMEN = ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo']
# Op welke dagen een nieuwe-voorraadpost geplaatst mag worden (GitHub-variabele PUBLICATIE_DAGEN, bv. 'di,vr').
# De website wordt wél elke dag gecontroleerd.
PUBLICATIE_DAGEN = [DAGNAMEN.index(d.strip()[:2].lower()) for d in
                    (os.environ.get('PUBLICATIE_DAGEN') or 'di,vr').split(',') if d.strip()[:2].lower() in DAGNAMEN]
# Story na een post: alleen met GitHub-variabele STORY=aan (niet aanklikbaar via de API)
STORY = (os.environ.get('STORY') or 'uit').strip().lower() == 'aan'   # standaard UIT
MAX_POGINGEN = 3          # na 3 mislukte pogingen: status 'fout', niet meer automatisch proberen
MIN_FOTOS = 8             # minder foto's = nog geen echte foto's ('verwacht'-plaatje): nog niet verkoopklaar

# Instagram
IG_HOST = os.environ.get('IG_API_HOST', 'graph.instagram.com')   # of graph.facebook.com (Facebook-login)
IG_VERSION = os.environ.get('IG_API_VERSION', 'v23.0')
IG_USER_ID = os.environ.get('IG_USER_ID', '').strip()
IG_TOKEN_SECRET = os.environ.get('IG_ACCESS_TOKEN', '').strip()

# Optioneel: Claude API voor fotokeuze en teksten (zonder sleutel: vaste regels)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '').strip()
CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-5-5')

# GitHub (voor openbare beeld-URL's die Instagram kan ophalen)
GITHUB_REPOSITORY = os.environ.get('GITHUB_REPOSITORY', '')

VASTE_HASHTAGS = ['#CBAutomobielen', '#Occasions', '#AutoTeKoop', '#Sneek', '#NieuweVoorraad']


def nu():
    return datetime.now(TZ)


def vandaag():
    return nu().strftime('%Y-%m-%d')
