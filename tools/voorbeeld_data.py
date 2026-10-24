"""Alleen voor de audit: haalt actuele websitedata + foto's van een paar auto's op (raakt de database niet)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automaat import site, config
from bs4 import BeautifulSoup

OUT = os.path.join(config.ROOT, 'voorbeeld', 'data')
IDS = ['952652', '939529', '943067', '917880', '951379']
os.makedirs(OUT, exist_ok=True)
lst = site.aanbod()
json.dump(lst, open(os.path.join(OUT, 'aanbod.json'), 'w'), ensure_ascii=False, indent=1)
for vid in IDS:
    if vid not in lst:
        print('niet in aanbod:', vid); continue
    slug = lst[vid]['slug']
    v = site.voertuig(slug)
    html = site.get(f'{config.SITE_BASE}/aanbod/{slug}')
    s = BeautifulSoup(html, 'html.parser')
    v['paginatekst'] = s.get_text('\n', strip=True)
    v['omschrijving'] = [x.get_text(' ', strip=True) for x in s.select('.cadar-description, .cadar-offer-description, [class*=description]')][:5]
    d = os.path.join(OUT, vid); os.makedirs(d, exist_ok=True)
    site.download_fotos(v, os.path.join(d, 'fotos'))
    json.dump(v, open(os.path.join(d, 'voertuig.json'), 'w'), ensure_ascii=False, indent=1)
    print('ok', vid, v['title'], len(v['fotos']))
