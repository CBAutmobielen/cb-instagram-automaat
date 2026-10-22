"""Website cbautomobielen.nl uitlezen. Gebaseerd op cb/fetch.py uit de kit (zelfde selectors)."""
import os, re, time, json, hashlib, urllib.request, concurrent.futures as cf
from bs4 import BeautifulSoup
from PIL import Image
from . import config

UA = {'User-Agent': 'Mozilla/5.0 (CB Automobielen Instagram-automaat; +https://www.cbautomobielen.nl)'}
FOTO_RE = re.compile(r'https://cdn1\.grbx\.app/images/[0-9a-f-]+/full\.jpg')


class SiteFout(Exception):
    pass


def voertuig_id(slug):
    """Uniek, stabiel ID: het nummer aan het eind van de URL (bv. ...-941609)."""
    m = re.search(r'-(\d{5,})$', slug)
    return m.group(1) if m else 'u' + hashlib.sha1(slug.encode()).hexdigest()[:10]


def get(url, tries=6):
    laatste = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e:
            laatste = e
            time.sleep(2 * (i + 1))
    raise SiteFout(f'{url} niet bereikbaar: {laatste}')


def _prijs(text):
    m = re.search(r'€\s?\d{1,3}(?:\.\d{3})+|€\s?\d{3,}', text)
    return m.group(0).replace('€', '€ ').replace('  ', ' ') if m else None


def _km(text):
    m = re.search(r'(\d{1,3}(?:\.\d{3})+|\d{1,6})\s?km(?![a-z])', text, re.I)
    return (m.group(1) + ' km') if m else None


def aanbod():
    """Alle auto's uit het overzicht. Geeft {id: {...}} terug. Beschikbaar = prijs met €."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA['User-Agent'])
        try:
            pg.goto(config.SITE_BASE + '/aanbod/', wait_until='networkidle', timeout=90000)
        except Exception as e:
            b.close(); raise SiteFout(f'aanbodpagina niet bereikbaar: {e}')
        for _ in range(30):
            btn = pg.locator('button:has-text("Meer resultaten laden"), a:has-text("Meer resultaten laden")')
            if btn.count() == 0 or not btn.first.is_visible():
                break
            btn.first.click(); pg.wait_for_timeout(2500)
        cards = pg.evaluate("""() => [...document.querySelectorAll('.cadar-offer__container')].map(c => {
            const a = c.querySelector('a[href*="/aanbod/"]') || c.closest('a');
            return {href: a ? a.getAttribute('href').split('?')[0] : '', text: c.innerText.replace(/\\s+/g,' ').trim()} })""")
        b.close()
    out = {}
    for c in cards:
        m = re.search(r'/aanbod/([a-z0-9-]+-\d{5,})/?$', c['href'])
        if not m:
            continue
        slug = m.group(1)
        titel = re.split(r'\s\d{1,3}(?:\.\d{3})*\s?km|€|op aanvraag', c['text'], maxsplit=1, flags=re.I)[0].strip()
        titel = re.sub(r'\s(?:19|20)\d{2}$', '', titel)
        out[voertuig_id(slug)] = {
            'titel': titel[:90] or slug,
            'slug': slug, 'url': f'{config.SITE_BASE}/aanbod/{slug}', 'tekst': c['text'],
            'beschikbaar': '€' in c['text'], 'prijs': _prijs(c['text']), 'km': _km(c['text']),
        }
    if not out:
        # Nooit concluderen dat alles verkocht is als de pagina niets oplevert (storing of nieuwe website)
        raise SiteFout('aanbodpagina gaf 0 auto\'s; mogelijk storing of gewijzigde website. Er is niets aangepast.')
    return out


def voertuig(slug):
    """Voertuigpagina uitlezen: specificaties, opties, prijs en foto-URL's."""
    s = BeautifulSoup(get(f'{config.SITE_BASE}/aanbod/{slug}'), 'html.parser')
    tx = lambda el: el.get_text(' ', strip=True) if el else ''
    d = {'slug': slug, 'id': voertuig_id(slug), 'url': f'{config.SITE_BASE}/aanbod/{slug}'}
    d['title'] = tx(s.find('h1'))
    d['table'] = {tx(e.select_one('.cadar-table__key')): tx(e.select_one('.cadar-table__value'))
                  for e in s.select('.cadar-table__entry')}
    d['bijzondere_opties'] = [tx(x) for x in s.select('.cadar-special-feature')]
    d['opties'] = list(dict.fromkeys(tx(x) for x in s.select('.cadar-feature')))
    pagetext = s.get_text(' ', strip=True)
    prices = re.findall(r'€\s?\d{1,3}(?:\.\d{3})+', pagetext)
    d['prijs'] = prices[0].replace('€', '€ ').replace('  ', ' ') if prices else ''
    d['op_aanvraag'] = not prices and 'op aanvraag' in pagetext.lower()
    imgs = []
    for e in s.select('.cadar-gallery__entry-image'):
        m = FOTO_RE.search(str(e))
        if m and m.group(0) not in imgs:
            imgs.append(m.group(0))
    d['fotos'] = imgs
    if not d['title'] or not d['table']:
        raise SiteFout(f'voertuigpagina {slug} kon niet worden gelezen (structuur gewijzigd?)')
    return d


def download_fotos(v, folder):
    """Alle verkoopfoto's van DEZE auto in hoogste kwaliteit. Bewaart herkomst per bestand."""
    os.makedirs(folder, exist_ok=True)
    herkomst = {}

    def one(job):
        i, u = job
        f = os.path.join(folder, f'{i:02d}.jpg')
        for _ in range(6):
            try:
                Image.open(f).load(); return
            except Exception:
                try:
                    open(f, 'wb').write(get(u + '?quality=100', tries=2))
                except Exception:
                    time.sleep(2)
    jobs = list(enumerate(v['fotos'], 1))
    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(one, jobs))
    for i, u in jobs:
        f = os.path.join(folder, f'{i:02d}.jpg')
        if os.path.exists(f):
            herkomst[f'{i:02d}'] = {'url': u, 'sha1': hashlib.sha1(open(f, 'rb').read()).hexdigest()}
    json.dump(herkomst, open(os.path.join(folder, 'herkomst.json'), 'w'), indent=1)
    return herkomst
