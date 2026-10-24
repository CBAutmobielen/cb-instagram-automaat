"""Render v2-voorbeelden + v2-captions voor de audit (lokaal, niets publiceren)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'cb'))
import render as R
import render_v2 as V
from automaat import content_v2 as C

R.IMG = os.path.join(ROOT, 'voorbeeld', 'data')
KEUZE = {
    '952652': dict(hero='04', specs='03', options='02', d1='17', d2='21', d3='29', contact='01'),
    '939529': dict(hero='04', specs='03', options='02', d1='13', d2='09', d3='38', contact='01'),
    '943067': dict(hero='04', specs='03', options='02', d1='31', d2='12', d3='32', contact='01'),
}
POS = {'939529': {'d1': '50% 60%', 'contact': '50% 0%'}, '952652': {'contact': '50% 0%'}, '943067': {'contact': '50% 0%'}}
for vid in sys.argv[1:] or KEUZE:
    v = json.load(open(os.path.join(ROOT, 'voorbeeld', 'data', vid, 'voertuig.json')))
    v['id'] = vid
    c2 = C.maak_v2(v)
    c = dict(slug=f'{vid}/fotos', price=v['prijs'], photos=KEUZE[vid], pos=POS.get(vid, {}), v2=c2)
    out = os.path.join(ROOT, 'voorbeeld', 'v2', vid)
    files, issues = V.render(c, out)
    tekst, opener = C.caption(v, c2)
    open(os.path.join(out, 'caption.txt'), 'w').write(tekst)
    json.dump(c2, open(os.path.join(out, 'teksten.json'), 'w'), ensure_ascii=False, indent=1)
    print(vid, 'problemen:', issues or 'geen'); print(json.dumps(c2, ensure_ascii=False)); print(tekst); print('-' * 60)
