"""CB Automobielen - Instagram-template v2 (VOORSTEL, nog niet actief).

Zelfde huisstijl (kleuren, Poppins/DM Sans, logo, 1080x1350), maar:
- grotere auto en grotere, beter leesbare tekst op mobiel (minimaal 24 px labels, 30 px lopende tekst)
- geen eigen slide-stippen meer (Instagram toont die al)
- geen herhaling van gegevens tussen slides
- vaste plek voor logo + website in de voet van elke slide
"""
import asyncio, os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from playwright.async_api import async_playwright

E = html.escape
M = 72
CW = 1080 - 2 * M

CSS = """
%s
*{margin:0;padding:0;box-sizing:border-box}
:root{--o:#EB5B28;--ink:#0C0E12;--mut:#B3B6BB;--line:rgba(255,255,255,.14)}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--ink)}
body{font-family:'DM Sans',sans-serif;-webkit-font-smoothing:antialiased;color:#fff}
.s{position:relative;width:1080px;height:1350px;overflow:hidden;background:var(--ink)}
.ph{position:absolute;overflow:hidden}.ph img{display:block;width:100%%;height:100%%}
.fade{position:absolute;left:0;right:0;background:linear-gradient(180deg,rgba(12,14,18,0),#0C0E12)}
.pad{position:absolute;left:72px;width:936px}
.lab{font-family:'DM Sans';font-weight:700;font-size:24px;letter-spacing:.16em;text-transform:uppercase;color:var(--o);line-height:1}
.hd{font-family:'Poppins';font-weight:700;letter-spacing:-.005em;line-height:1.02;text-transform:uppercase;white-space:nowrap}
.h2{font-family:'Poppins';font-weight:600;line-height:1.1;white-space:nowrap}
.sub{font-family:'Poppins';font-weight:500;color:var(--mut);line-height:1.2;white-space:nowrap}
.keys{display:flex;align-items:center;font-family:'DM Sans';font-weight:600;font-size:30px;color:#fff;letter-spacing:.02em;white-space:nowrap}
.keys span+span:before{content:'';display:inline-block;width:6px;height:6px;border-radius:50%%;background:var(--o);margin:0 18px;vertical-align:6px}
.price{font-family:'Poppins';font-weight:600;color:var(--o);line-height:1;white-space:nowrap}
.foot{position:absolute;left:72px;right:72px;bottom:56px;height:40px;display:flex;justify-content:space-between;align-items:center}
.foot img{height:36px;display:block}
.foot span{font-family:'DM Sans';font-weight:600;font-size:24px;letter-spacing:.06em;color:var(--mut)}
.grid{display:grid;grid-template-columns:1fr 1fr;column-gap:48px}
.cell{border-top:1px solid var(--line);padding:26px 0 0;height:150px}
.cell .k{font-family:'DM Sans';font-weight:700;font-size:22px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.cell .v{font-family:'Poppins';font-weight:600;font-size:42px;margin-top:14px;white-space:nowrap}
.opt{display:flex;align-items:center;gap:20px;border-top:1px solid var(--line);height:96px;font-family:'Poppins';font-weight:500;font-size:31px;white-space:nowrap}
.opt i{width:10px;height:10px;background:var(--o);border-radius:2px;flex:none}
.btn{display:inline-flex;align-items:center;background:var(--o);color:#fff;font-family:'Poppins';font-weight:600;font-size:32px;line-height:1;padding:26px 40px;border-radius:6px}
.ghost{display:inline-flex;align-items:center;border:2px solid rgba(255,255,255,.35);color:#fff;font-family:'Poppins';font-weight:600;font-size:32px;line-height:1;padding:24px 38px;border-radius:6px;margin-left:16px}
.ct{font-family:'DM Sans';font-weight:500;font-size:28px;line-height:1.55;color:var(--mut)}
.ct b{color:#fff;font-weight:600}
"""


def css():
    return CSS % R.FONTS


def ph(c, key, x, y, w, h, rounded=False):
    return R.ph(c, key, x, y, w, h, rounded)


def foot():
    return f'<div class="foot"><img src="{R.LOGO}"><span>CBAUTOMOBIELEN.NL</span></div>'


def page(body):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{css()}</style></head>
<body><div class="s">{body}{foot()}</div>
<script>document.fonts.ready.then(()=>document.querySelectorAll('[data-fit]').forEach(el=>{{let s=parseFloat(getComputedStyle(el).fontSize);const max=+el.dataset.fit;while(el.scrollWidth>max&&s>20){{s-=1;el.style.fontSize=s+'px'}}}}));</script>
</body></html>"""


def s1(c):
    keys = ''.join(f'<span>{E(k)}</span>' for k in c['v2']['kern'])
    return page(f"""
{ph(c, 'hero', 0, 0, 1080, 900)}
<div class="fade" style="top:700px;height:200px"></div>
<div class="pad" style="top:862px">
  <div class="lab">{E(c['v2']['label'])}</div>
  <div class="hd" data-fit="{CW}" style="font-size:84px;margin-top:20px">{E(c['v2']['kop'])}</div>
  <div class="sub" data-fit="{CW}" style="font-size:32px;margin-top:12px">{E(c['v2']['ondertitel'])}</div>
</div>
<div class="pad" style="top:1124px;display:flex;justify-content:space-between;align-items:center">
  <div class="keys" data-fit="600">{keys}</div>
  <div class="price" style="font-size:60px">{E(c['price'])}</div>
</div>
""")


def s2(c):
    cells = ''.join(f'<div class="cell"><div class="k">{E(k)}</div><div class="v" data-fit="444">{E(v)}</div></div>'
                    for k, v in c['v2']['specs'])
    return page(f"""
{ph(c, 'specs', 0, 0, 1080, 700)}
<div class="fade" style="top:560px;height:140px"></div>
<div class="pad" style="top:724px"><div class="lab">Specificaties</div></div>
<div class="pad grid" style="top:782px">{cells}</div>
""")


def s3(c):
    rows = ''.join(f'<div class="opt"><i></i><span data-fit="380">{E(o)}</span></div>' for o in c['v2']['opties'])
    return page(f"""
{ph(c, 'options', 0, 0, 1080, 640)}
<div class="fade" style="top:500px;height:140px"></div>
<div class="pad" style="top:664px">
  <div class="lab">Uitrusting</div>
  <div class="h2" data-fit="{CW}" style="font-size:50px;margin-top:18px">{E(c['v2']['optiekop'])}</div>
</div>
<div class="pad grid" style="top:842px;column-gap:40px">{rows}</div>
""")


def s4(c):
    return page(f"""
<div class="pad" style="top:72px;display:flex;justify-content:space-between;align-items:baseline">
  <div class="lab">Details</div>
  <div class="sub" style="font-size:28px">{E(c['v2']['kop'].title() if c['v2']['kop'].isupper() else c['v2']['kop'])}</div>
</div>
{ph(c, 'd1', M, 136, CW, 620, True)}
{ph(c, 'd2', M, 772, 460, 410, True)}
{ph(c, 'd3', M + 476, 772, 460, 410, True)}
""")


def s5(c):
    rk = ' &nbsp;·&nbsp; Rijklaar afgeleverd' if c['v2'].get('rijklaar') else ''
    return page(f"""
{ph(c, 'contact', 0, 0, 1080, 640)}
<div class="fade" style="top:500px;height:140px"></div>
<div class="pad" style="top:668px">
  <div class="lab">Interesse?</div>
  <div class="h2" data-fit="{CW}" style="font-size:58px;margin-top:18px">{E(c['v2']['cta_kop'])}</div>
  <div class="sub" style="font-size:30px;margin-top:16px;white-space:normal">Alle foto's en specificaties op cbautomobielen.nl</div>
</div>
<div class="pad" style="top:940px"><div class="btn">Bel 0515 745 030</div><div class="ghost">Stuur een DM</div></div>
<div class="pad" style="top:1068px;display:flex;justify-content:space-between;align-items:flex-end">
  <div class="ct"><b style="color:var(--o)">{E(c['price'])}</b>{rk}</div>
  <div class="ct" style="text-align:right">Edisonstraat 1c, Sneek</div>
</div>
""")


SLIDES = [('Slide 01 Cover', s1), ('Slide 02 Specificaties', s2), ('Slide 03 Uitrusting', s3),
          ('Slide 04 Details', s4), ('Slide 05 Contact', s5)]

CHECK = """() => {const out=[];document.querySelectorAll('.hd,.h2,.sub,.lab,.keys,.price,.opt span,.cell .v,.cell .k,.btn,.ghost,.ct,.foot span').forEach(e=>{const b=e.getBoundingClientRect();if(!b.width)return;
 if(!e.closest('.foot') && (b.left<71.5||b.right>1008.5)) out.push('marge:'+e.className+':'+e.innerText.slice(0,30));
 if(b.bottom>1236 && !e.closest('.foot')) out.push('voet:'+e.className+':'+Math.round(b.bottom));
 if(e.scrollWidth>e.clientWidth+1 && getComputedStyle(e).whiteSpace==='nowrap') out.push('afgekapt:'+e.innerText.slice(0,30));
 const fs=parseFloat(getComputedStyle(e).fontSize); if(fs<22) out.push('te klein ('+fs+'px):'+e.innerText.slice(0,30));});
 return out;}"""


async def _render(c, outdir):
    R.SCALE = 1
    os.makedirs(outdir, exist_ok=True)
    issues, files = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--force-color-profile=srgb'])
        pg = await b.new_page(viewport={'width': 1080, 'height': 1350})
        for name, fn in SLIDES:
            hp = os.path.join(R.TMP, 'html_v2', c['slug'], name + '.html')
            os.makedirs(os.path.dirname(hp), exist_ok=True)
            open(hp, 'w', encoding='utf-8').write(fn(c))
            await pg.goto('file://' + hp)
            await pg.evaluate('document.fonts.ready')
            await pg.evaluate('Promise.all([...document.images].map(i => i.decode()))')
            await pg.wait_for_timeout(400)
            issues += [f'{name}: {i}' for i in await pg.evaluate(CHECK)]
            f = os.path.join(outdir, name + '.png'); await pg.screenshot(path=f); files.append(f)
        await b.close()
    return files, issues


def render(c, outdir):
    return asyncio.run(_render(c, outdir))
