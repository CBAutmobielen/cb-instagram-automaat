"""CB Automobielen - Instagram carrousel renderer (vast designsysteem).

Gebruik:
  python cb/render.py                 # alle actieve auto's, beide formaten
  python cb/render.py --auto polo     # alleen auto's waarvan de slug 'polo' bevat
  python cb/render.py --schaal 1      # alleen 1080x1350 (Instagram)

Invoer : cb/cars.json + photos/<slug>/NN.jpg + assets/
Uitvoer: output/<Merk Model Uitvoering>/Instagram 1080x1350/Slide 0X ....png
         output/<Merk Model Uitvoering>/Master 2160x2700/Slide 0X ....png

Foto's worden per vlak vooraf exact op pixelmaat gesneden (Lanczos), zodat Chrome ze
1:1 tekent. Na elke slide draait een uitlijncontrole; bij fouten stopt het script met exitcode 1.
"""
import os, sys, json, re, asyncio, html, hashlib, argparse
from PIL import Image, ImageFilter, ImageDraw
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.environ.get('CB_PHOTOS', os.path.join(ROOT, 'photos'))
OUTROOT = os.path.join(ROOT, 'output')
TMP = os.path.join(ROOT, '.cache')
FONTDIR = os.path.join(ROOT, 'assets', 'fonts')
FONTS = open(os.path.join(FONTDIR, 'fonts.css')).read().replace("url('", "url('file://" + FONTDIR + "/")
LOGO = 'file://' + os.path.join(ROOT, 'assets', 'logo.png')
E = html.escape
M = 72             # buitenmarge
CW = 1080 - 2 * M  # contentbreedte 936
BASE = 1158        # onderkant content (72 boven footer)
SCALE = 1          # wordt per ronde gezet

CSS = """
%s
*{margin:0;padding:0;box-sizing:border-box}
:root{--orange:#EB5B28;--ink:#0C0E12;--muted:#B3B6BB;--line:rgba(255,255,255,.14)}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--ink)}
body{font-family:'DM Sans',sans-serif;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;color:#fff}
.s{position:relative;width:1080px;height:1350px;overflow:hidden;background:var(--ink)}
.ph{position:absolute;overflow:hidden;background:#000}
.ph img{display:block;width:100%%;height:100%%}
.r{border-radius:5px}
.lab{font-family:'DM Sans';font-weight:700;font-size:23px;line-height:1;letter-spacing:.13em;text-transform:uppercase;color:var(--orange)}
.h{font-family:'Poppins';font-weight:600;letter-spacing:-.01em;line-height:1.1}
.sub{font-family:'Poppins';font-weight:500;color:var(--muted);line-height:1.2}
.foot{position:absolute;left:0;right:0;bottom:0;height:120px;background:var(--ink);display:flex;align-items:center;justify-content:space-between;padding:0 72px;border-top:1px solid rgba(255,255,255,.08)}
.foot img{height:34px;display:block}
.dots{display:flex;gap:10px;align-items:center}
.dots i{width:10px;height:10px;border-radius:50%%;background:#3A3D43;display:block}
.dots i.on{background:var(--orange)}
.pad{position:absolute;left:72px;width:936px}
.meta{display:flex;font-family:'DM Sans';font-weight:500;font-size:28px;color:var(--muted);align-items:center;line-height:1}
.meta span+span:before{content:'';display:inline-block;width:1px;height:22px;background:var(--line);margin:0 22px;vertical-align:-4px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);column-gap:36px}
.cell{border-top:1px solid var(--line);padding-top:24px;height:158px}
.cell .lab{font-size:20px}
.cell .v{font-family:'Poppins';font-weight:600;font-size:38px;margin-top:14px;line-height:1.1;white-space:nowrap}
.cell .v small{display:block;font-family:'DM Sans';font-weight:500;font-size:24px;color:var(--muted);margin-top:6px}
.opts{display:grid;grid-template-columns:1fr 1fr;column-gap:40px}
.opt{display:flex;gap:20px;align-items:baseline;border-top:1px solid var(--line);padding-top:24px;height:112px}
.opt b{font-family:'Poppins';font-weight:600;font-size:23px;color:var(--orange);min-width:30px}
.opt span{font-family:'Poppins';font-weight:500;font-size:27px;line-height:1.25}
.btn{display:inline-flex;align-items:center;background:var(--orange);color:#fff;font-family:'Poppins';font-weight:600;font-size:28px;line-height:1;padding:24px 36px;border-radius:4px}
.cap{display:flex;flex-wrap:nowrap;font-weight:500;font-size:26px;line-height:1;color:var(--muted);margin-top:22px;white-space:nowrap}
.cap span+span:before{content:'';display:inline-block;width:5px;height:5px;border-radius:50%%;background:var(--orange);margin:0 16px;vertical-align:5px}
.ct{font-family:'DM Sans';font-weight:500;font-size:27px;line-height:1.55;color:var(--muted)}
.ct strong{color:#fff;font-weight:600}
""" % FONTS


def prep(c, key, w, h, rounded=False):
    """Snij foto naar exact w x h (css px) * SCALE, cover + object-position."""
    src = f"{IMG}/{c['slug']}/{c['photos'][key]}.jpg"
    px, py = [float(v.strip('%')) / 100 for v in c.get('pos', {}).get(key, '50% 50%').split()]
    W, H = w * SCALE, h * SCALE
    tag = hashlib.md5(f'{src}{W}{H}{px}{py}{rounded}'.encode()).hexdigest()[:12]
    dst = os.path.join(TMP, f'prep_{SCALE}x', tag + '.png')
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(src).convert('RGB')
        s = max(W / im.width, H / im.height)
        nw, nh = round(im.width * s), round(im.height * s)
        im = im.resize((nw, nh), Image.LANCZOS)
        x, y = round((nw - W) * px), round((nh - H) * py)
        im = im.crop((x, y, x + W, y + H))
        # lichte verscherping: meer bij opschalen dan bij verkleinen
        im = im.filter(ImageFilter.UnsharpMask(radius=1.0 if s > 1 else 0.6, percent=45 if s > 1 else 30, threshold=2))
        if rounded:
            # afgeronde hoeken (5px) direct in de foto, zodat de browser niet hoeft te clippen:
            # dat maakt de uitkomst op elke machine bytegelijk
            k = 4; r = 5 * SCALE * k
            mask = Image.new('L', (W * k, H * k), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, W * k - 1, H * k - 1), radius=r, fill=255)
            mask = mask.resize((W, H), Image.LANCZOS)
            bg = Image.new('RGB', (W, H), (12, 14, 18))
            im = Image.composite(im, bg, mask)
        im.save(dst, optimize=False, compress_level=3)
    return 'file://' + dst


def ph(c, key, x, y, w, h, rounded=False):
    return f'<div class="ph" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:none"><img src="{prep(c, key, w, h, rounded)}"></div>'


def foot(n):
    dots = ''.join(f'<i class="{"on" if i == n else ""}"></i>' for i in range(1, 6))
    return f'<div class="foot"><img src="{LOGO}"><div class="dots">{dots}</div></div>'


def page(body, n):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="s">{body}{foot(n)}</div>
<script>
document.fonts.ready.then(()=>document.querySelectorAll('[data-fit]').forEach(el=>{{let s=parseFloat(getComputedStyle(el).fontSize);const max=+el.dataset.fit;while(el.scrollWidth>max&&s>20){{s-=1;el.style.fontSize=s+'px'}}}}));
</script></body></html>"""


def nb(t):
    """Escape + voorkom afbreken op koppeltekens."""
    return re.sub(r'(\S*-\S*)', r'<span style="white-space:nowrap">\1</span>', E(t))


def val(v):
    if '(' in v:
        a, b = v.split('(', 1)
        return f'{E(a.strip())}<small>{E(b.rstrip(")").replace("-drs", " deuren"))}</small>'
    return E(v)


def s1(c):
    meta = ''.join(f'<span>{E(x)}</span>' for x in [c['specs']['Bouwjaar'], c['specs']['Kilometerstand'], c['specs']['Vermogen'], c['specs']['Transmissie']])
    return page(f"""
{ph(c, 'hero', 0, 0, 1080, 810)}
<div class="pad" style="top:858px">
  <div class="lab">Nu beschikbaar</div>
  <div class="h" data-fit="{CW}" style="font-size:76px;margin-top:18px;white-space:nowrap">{E(c['title'])}</div>
  <div class="sub" style="font-size:34px;margin-top:6px;white-space:nowrap">{E(c['sub'])}</div>
</div>
<div class="pad" style="top:1070px;height:1px;background:var(--line)"></div>
<div class="pad" style="top:1102px;height:56px;display:flex;justify-content:space-between;align-items:center">
  <div class="meta">{meta}</div>
  <div class="h" style="font-size:48px;line-height:1;color:var(--orange)">{E(c['price'])}</div>
</div>
""", 1)


def s2(c):
    cells = ''.join(f'<div class="cell"><div class="lab">{E(k)}</div><div class="v">{val(v)}</div></div>' for k, v in c['specs'].items())
    return page(f"""
<div class="pad" style="top:72px;height:110px;display:flex;justify-content:space-between;align-items:flex-end">
  <div><div class="lab">In één oogopslag</div>
  <div class="h" data-fit="620" style="font-size:46px;line-height:1;margin-top:22px;white-space:nowrap">{E(c['title'])}</div></div>
  <div style="text-align:right"><div class="lab" style="font-size:20px;color:var(--muted)">Vraagprijs</div><div class="h" style="font-size:46px;line-height:1;margin-top:22px;color:var(--orange)">{E(c['price'])}</div></div>
</div>
{ph(c, 'specs', M, 232, CW, 560, True)}
<div class="pad grid" style="top:842px">{cells}</div>
""", 2)


def s3(c):
    rows = ''.join(f'<div class="opt"><b>{i:02d}</b><span>{nb(o)}</span></div>' for i, o in enumerate(c['options'], 1))
    top = BASE - 3 * 112
    return page(f"""
{ph(c, 'options', 0, 0, 1080, 540)}
<div class="pad" style="bottom:{1350 - top + 44}px">
  <div class="lab">Belangrijkste opties</div>
  <div class="h" style="font-size:46px;margin-top:18px">{nb(c['opt_head'])}</div>
</div>
<div class="pad opts" style="top:{top}px">{rows}</div>
""", 3)


def s4(c):
    cap = ''.join(f'<span>{E(x)}</span>' for x in c['det_cap'])
    return page(f"""
<div class="pad" style="top:72px">
  <div class="lab">Details</div>
  <div class="h" data-fit="{CW}" style="font-size:46px;line-height:1;margin-top:22px;white-space:nowrap">{E(c['det_head'])}</div>
  <div class="cap" data-fit="936">{cap}</div>
</div>
{ph(c, 'd1', M, 270, CW, 530, True)}
{ph(c, 'd2', M, 816, 460, BASE - 816, True)}
{ph(c, 'd3', M + 476, 816, 460, BASE - 816, True)}
""", 4)


def s5(c):
    return page(f"""
{ph(c, 'contact', 0, 0, 1080, 620)}
<div class="pad" style="top:668px">
  <div class="lab">Nu beschikbaar bij CB Automobielen</div>
  <div class="h" data-fit="{CW}" style="font-size:62px;line-height:1;margin-top:22px;white-space:nowrap">Interesse in {E(c['short'])}?</div>
  <div class="sub" style="font-size:30px;margin-top:16px">Plan een bezichtiging in onze showroom in Sneek.</div>
</div>
<div class="pad" style="bottom:{1350 - BASE}px;display:flex;justify-content:space-between;align-items:flex-end">
  <div>
    <div class="btn">Bel 0515 745 030</div>
    <div class="ct" style="margin-top:26px">{E(c['site_title'])}<br><strong style="color:var(--orange)">{E(c['price'])}</strong> &nbsp;·&nbsp; Rijklaar afgeleverd</div>
  </div>
  <div class="ct" style="text-align:right">
    <strong>CB Automobielen</strong><br>Edisonstraat 1c<br>8606 JH Sneek<br>info@cbautomobielen.nl<br>cbautomobielen.nl
  </div>
</div>
""", 5)


SLIDES = [('Slide 01 Hero', s1), ('Slide 02 Specificaties', s2), ('Slide 03 Opties', s3), ('Slide 04 Details', s4), ('Slide 05 Contact', s5)]

# Controle op overlap/uitlijning: elk tekstblok binnen marges en boven de footer
CHECK = """() => {
 const out=[];const r=e=>e.getBoundingClientRect();
 document.querySelectorAll('.pad, .h, .sub, .lab, .meta, .opt span, .cap, .ct, .btn').forEach(e=>{const b=r(e);
  if(b.width===0) return;
  if(b.left<71.5||b.right>1008.5) out.push('marge:'+e.className+':'+Math.round(b.left)+'-'+Math.round(b.right)+':'+e.innerText.slice(0,30));
  if(b.bottom>1230.5 && !e.closest('.foot')) out.push('footer:'+e.className+':'+Math.round(b.bottom));
  if(e.scrollWidth>e.clientWidth+1 && getComputedStyle(e).whiteSpace==='nowrap') out.push('overflow:'+e.innerText.slice(0,30));
 });
 document.querySelectorAll('.opt span').forEach(e=>{if(r(e).height>70) out.push('3 regels:'+e.innerText)});
 return out;}"""



FORMATS = {1: 'Instagram 1080x1350', 2: 'Master 2160x2700'}


async def render_cars(todo, scales=(1, 2), outroot=None):
    """Rendert de opgegeven auto's. Geeft (bestanden, problemen) terug. Ontwerp ongewijzigd."""
    global SCALE
    outroot = outroot or OUTROOT
    issues, files = [], {}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--force-color-profile=srgb'])
        for SCALE in scales:
            pg = await b.new_page(viewport={'width': 1080, 'height': 1350}, device_scale_factor=SCALE)
            for c in todo:
                d = os.path.join(outroot, c['folder'], FORMATS[SCALE]); os.makedirs(d, exist_ok=True)
                for name, fn in SLIDES:
                    hp = os.path.join(TMP, 'html', c['slug'], name + '.html')
                    os.makedirs(os.path.dirname(hp), exist_ok=True)
                    open(hp, 'w', encoding='utf-8').write(fn(c))
                    await pg.goto('file://' + hp)
                    await pg.evaluate('document.fonts.ready')
                    await pg.evaluate('Promise.all([...document.images].map(i => i.decode()))')
                    await pg.wait_for_timeout(400)
                    for i in await pg.evaluate(CHECK):
                        issues.append(f"{c['folder']} / {name} ({FORMATS[SCALE]}): {i}")
                    out = os.path.join(d, name + '.png')
                    await pg.screenshot(path=out)
                    files.setdefault((c['slug'], SCALE), []).append(out)
                print(f"klaar: {c['folder']} ({FORMATS[SCALE]})")
            await pg.close()
        await b.close()
    return files, issues


def render(todo, scales=(1, 2), outroot=None):
    return asyncio.run(render_cars(todo, scales, outroot))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--auto', default=None, help='filter op (deel van) slug')
    ap.add_argument('--schaal', type=int, choices=[1, 2], default=None, help='1 = 1080x1350, 2 = 2160x2700; leeg = beide')
    ap.add_argument('--ook-review', action='store_true', help='render ook auto\'s met review_nodig=true')
    ARGS = ap.parse_args()
    CARS = json.load(open(os.path.join(ROOT, 'cb', 'cars.json'), encoding='utf-8'))
    todo = [c for c in CARS if c.get('status') == 'actief' and (ARGS.ook_review or not c.get('review_nodig'))
            and (not ARGS.auto or ARGS.auto in c['slug'])]
    skipped = [c['slug'] for c in CARS if c.get('status') == 'actief' and c.get('review_nodig') and not ARGS.ook_review]
    _, issues = render(todo, [ARGS.schaal] if ARGS.schaal else [1, 2])
    if skipped:
        print('\nOVERGESLAGEN (review_nodig=true, eerst teksten controleren):\n  ' + '\n  '.join(skipped))
    if issues:
        print('\nUITLIJNPROBLEMEN:\n' + '\n'.join(issues)); sys.exit(1)
    print('\nGeen uitlijnproblemen. Uitvoer staat in ./output')


if __name__ == '__main__':
    main()
