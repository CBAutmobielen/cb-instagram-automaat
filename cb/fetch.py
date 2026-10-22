"""CB Automobielen - aanbod ophalen en cars.json bijwerken.

Gebruik:
  python cb/fetch.py            # aanbod controleren, foto's downloaden, cars.json bijwerken
  python cb/fetch.py --droog    # alleen tonen wat er zou veranderen

Wat dit script doet:
  1. Opent https://www.cbautomobielen.nl/aanbod/ in een headless browser en klikt op
     "Meer resultaten laden" tot alle auto's zichtbaar zijn.
  2. Een auto telt als BESCHIKBAAR als de prijs in het overzicht met "€" begint.
     "Op aanvraag" = verkocht (op de site staat dan een VERKOCHT-balk op de foto).
  3. Per beschikbare auto: voertuigpagina ophalen, specificaties en opties opslaan in
     data/<slug>.json en alle verkoopfoto's in hoogste kwaliteit naar photos/<slug>/.
  4. cars.json bijwerken:
     - bestaande auto: prijs en kilometerstand worden gecontroleerd en zo nodig bijgewerkt
     - niet meer beschikbaar: status -> "verkocht" (wordt niet meer gerenderd)
     - nieuwe auto: concept-invoer met review_nodig=true. Teksten, opties en fotokeuze
       eerst laten controleren (zie PROMPT_voor_Claude.md), daarna review_nodig=false.
     - minder dan 8 echte foto's (bv. "verwacht"-afbeelding): status -> "geen_fotos"
"""
import os, re, sys, json, time, argparse, urllib.request, concurrent.futures as cf
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.cbautomobielen.nl'
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/141 Safari/537.36'}
ap = argparse.ArgumentParser(); ap.add_argument('--droog', action='store_true'); ARGS = ap.parse_args()


def get(url, tries=6):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(1.5 * (i + 1))


def listing():
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto(BASE + '/aanbod/', wait_until='networkidle')
        for _ in range(20):
            btn = pg.locator('button:has-text("Meer resultaten laden"), a:has-text("Meer resultaten laden")')
            if btn.count() == 0 or not btn.first.is_visible(): break
            btn.first.click(); pg.wait_for_timeout(2500)
        cards = pg.evaluate("""() => [...document.querySelectorAll('.cadar-offer__container')].map(c => {
            const a = c.querySelector('a[href*="/aanbod/"]') || c.closest('a');
            return {href: a ? a.getAttribute('href').split('?')[0] : '', text: c.innerText.replace(/\\s+/g,' ').trim()} })""")
        b.close()
    out = {}
    for c in cards:
        m = re.search(r'/aanbod/([a-z0-9-]+-\d{5,})$', c['href'])
        if m: out[m.group(1)] = c['text']
    return out


def parse_vehicle(slug):
    s = BeautifulSoup(get(f'{BASE}/aanbod/{slug}'), 'html.parser')
    tx = lambda el: el.get_text(' ', strip=True) if el else ''
    d = {'slug': slug, 'url': f'{BASE}/aanbod/{slug}'}
    d['title'] = tx(s.find('h1'))
    d['table'] = {tx(e.select_one('.cadar-table__key')): tx(e.select_one('.cadar-table__value')) for e in s.select('.cadar-table__entry')}
    d['bijzondere_opties'] = [tx(x) for x in s.select('.cadar-special-feature')]
    d['opties'] = list(dict.fromkeys(tx(x) for x in s.select('.cadar-feature')))
    prices = re.findall(r'€\s?\d{1,3}(?:\.\d{3})+', s.get_text(' ', strip=True))
    d['prijs'] = prices[0] if prices else ''
    imgs = []
    for e in s.select('.cadar-gallery__entry-image'):
        m = re.search(r'https://cdn1\.grbx\.app/images/[0-9a-f-]+/full\.jpg', str(e))
        if m and m.group(0) not in imgs: imgs.append(m.group(0))
    d['fotos'] = imgs
    return d


def download(slug, urls):
    folder = os.path.join(ROOT, 'photos', slug); os.makedirs(folder, exist_ok=True)
    def one(job):
        i, u = job; f = os.path.join(folder, f'{i:02d}.jpg')
        for _ in range(6):
            try:
                Image.open(f).load(); return
            except Exception:
                try: open(f, 'wb').write(get(u + '?quality=100'))
                except Exception: time.sleep(2)
    with cf.ThreadPoolExecutor(6) as ex: list(ex.map(one, enumerate(urls, 1)))


KEYS = r'carplay|navigatie|camera|climat|airco|cruise|stoelverwarming|verwarmd|panorama|velgen|\bled\b|parkeer|keyless|cockpit|sound|harman|dynaudio|fender|sportstoel'


def concept(v):
    t = v['table']; words = v['title'].split()
    opts = list(v['bijzondere_opties'])
    for f in v['opties']:
        if len(opts) >= 6: break
        if f not in opts and re.search(KEYS, f.lower()): opts.append(f)
    opts = [o[:1].upper() + o[1:] for o in opts[:6]]
    return dict(
        slug=v['slug'], url=v['url'], status='actief', review_nodig=True,
        folder=v['title'], site_title=v['title'],
        title=' '.join(words[:2]), sub=' '.join(words[2:]), short='deze ' + (words[1] if len(words) > 1 else words[0]),
        price=v['prijs'],
        specs=dict(Bouwjaar=t.get('Bouwjaar', ''), Kilometerstand=t.get('Kilometerstand', '').replace(' Km', ' km'),
                   Vermogen=t.get('Vermogen', ''), Transmissie=t.get('Transmissie', ''), Brandstof=t.get('Brandstof', ''),
                   Carrosserie=t.get('Carrosserievorm', '')),
        photos=dict(hero='04', specs='08', options='02', d1='09', d2='10', d3='11', contact='07'), pos={},
        options=opts,
        opt_head='CONCEPT: korte kop met 2-3 sterkste opties.',
        det_head='CONCEPT: korte detailkop.',
        det_cap=[t.get('Kleur', ''), 'Rijklaar afgeleverd', t.get('Onderhoudsboekje', '')][:3])


def main():
    path = os.path.join(ROOT, 'cb', 'cars.json')
    cars = json.load(open(path, encoding='utf-8')); by = {c['slug']: c for c in cars}
    lst = listing()
    beschikbaar = {s: t for s, t in lst.items() if '€' in t}
    print(f'{len(lst)} auto\'s in aanbod, {len(beschikbaar)} beschikbaar (rest = "Op aanvraag"/verkocht)')
    for c in cars:
        if c['slug'] not in beschikbaar and c['status'] == 'actief':
            print('  VERKOCHT / weg:', c['folder']); c['status'] = 'verkocht'
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    for slug in beschikbaar:
        v = parse_vehicle(slug)
        json.dump(v, open(os.path.join(ROOT, 'data', slug + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        if slug in by:
            c = by[slug]; km = v['table'].get('Kilometerstand', '').replace(' Km', ' km')
            if v['prijs'] and v['prijs'] != c['price']:
                print(f"  PRIJS gewijzigd {c['folder']}: {c['price']} -> {v['prijs']}"); c['price'] = v['prijs']
            if km and km != c['specs']['Kilometerstand']:
                print(f"  KM gewijzigd {c['folder']}: {c['specs']['Kilometerstand']} -> {km}"); c['specs']['Kilometerstand'] = km
            if c['status'] != 'actief': c['status'] = 'actief'
        else:
            c = concept(v); cars.append(c); by[slug] = c
            print('  NIEUW (concept, review nodig):', v['title'])
        if len(v['fotos']) < 8:
            c['status'] = 'geen_fotos'; print('  GEEN ECHTE FOTO\'S, overgeslagen:', v['title']); continue
        if not ARGS.droog: download(slug, v['fotos'])
    if ARGS.droog:
        print('\n--droog: niets opgeslagen'); return
    json.dump(cars, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('\ncars.json bijgewerkt. Controleer nieuwe auto\'s (review_nodig=true) en draai daarna: python cb/render.py')


if __name__ == '__main__':
    main()
