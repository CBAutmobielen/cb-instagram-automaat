"""Instagram-story (1080x1920) in de vaste CB Automobielen-huisstijl, als aankondiging van een nieuwe post.

Hergebruikt de stijl, lettertypes, het logo en de fotobewerking van cb/render.py (ontwerp ongewijzigd).
Tekst blijft binnen de veilige zone van Instagram (niet in de bovenste/onderste ~250 px).
"""
import asyncio, os, sys
from . import config

sys.path.insert(0, os.path.join(config.ROOT, 'cb'))

W, H = 1080, 1920

EXTRA_CSS = """
html,body{width:1080px;height:1920px}
.s{width:1080px;height:1920px}
.story-foot{position:absolute;left:72px;right:72px;bottom:150px;display:flex;justify-content:space-between;align-items:center}
.story-foot img{height:40px;display:block}
.handle{font-family:'Poppins';font-weight:600;font-size:30px;color:#fff}
.verloop{position:absolute;left:0;right:0;top:860px;height:160px;background:linear-gradient(180deg,rgba(12,14,18,0) 0%,#0C0E12 100%)}
"""

CHECK = """() => {
 const out=[];const r=e=>e.getBoundingClientRect();
 document.querySelectorAll('.pad, .h, .sub, .lab, .meta, .btn, .handle').forEach(e=>{const b=r(e);
  if(b.width===0) return;
  if(b.left<71.5||b.right>1008.5) out.push('marge:'+e.className+':'+e.innerText.slice(0,30));
  if(b.bottom>1680 && !e.closest('.story-foot')) out.push('onderkant:'+e.className+':'+Math.round(b.bottom));
  if(e.scrollWidth>e.clientWidth+1 && getComputedStyle(e).whiteSpace==='nowrap') out.push('overflow:'+e.innerText.slice(0,30));
 });
 return out;}"""


def html(c):
    import render as R
    R.SCALE = 1
    E = R.E
    meta = ''.join(f'<span>{E(x)}</span>' for x in [c['specs']['Bouwjaar'], c['specs']['Kilometerstand'],
                                                    c['specs']['Vermogen'], c['specs']['Transmissie']])
    body = f"""
{R.ph(c, 'hero', 0, 120, 1080, 900)}
<div class="verloop"></div>
<div class="pad" style="top:1080px">
  <div class="lab">Nieuw binnen</div>
  <div class="h" data-fit="{R.CW}" style="font-size:84px;margin-top:20px;white-space:nowrap">{E(c['title'])}</div>
  <div class="sub" data-fit="{R.CW}" style="font-size:36px;margin-top:8px;white-space:nowrap">{E(c['sub'])}</div>
</div>
<div class="pad" style="top:1320px;height:1px;background:var(--line)"></div>
<div class="pad" style="top:1354px;display:flex;justify-content:space-between;align-items:center">
  <div class="meta" data-fit="560">{meta}</div>
  <div class="h" style="font-size:56px;line-height:1;color:var(--orange)">{E(c['price'])}</div>
</div>
<div class="pad" style="top:1470px">
  <div class="btn">Bekijk de nieuwe post op ons profiel</div>
</div>
<div class="story-foot"><img src="{R.LOGO}"><div class="handle">@cbautomobielen</div></div>
"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{R.CSS}{EXTRA_CSS}</style></head>
<body><div class="s">{body}</div>
<script>
document.fonts.ready.then(()=>document.querySelectorAll('[data-fit]').forEach(el=>{{let s=parseFloat(getComputedStyle(el).fontSize);const max=+el.dataset.fit;while(el.scrollWidth>max&&s>20){{s-=1;el.style.fontSize=s+'px'}}}}));
</script></body></html>"""


async def _render(c, out_png):
    from playwright.async_api import async_playwright
    import render as R
    hp = os.path.join(R.TMP, 'html', c['slug'], 'Story.html')
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, 'w', encoding='utf-8').write(html(c))
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--force-color-profile=srgb'])
        pg = await b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        await pg.goto('file://' + hp)
        await pg.evaluate('document.fonts.ready')
        await pg.evaluate('Promise.all([...document.images].map(i => i.decode()))')
        await pg.wait_for_timeout(500)
        issues = await pg.evaluate(CHECK)
        await pg.screenshot(path=out_png)
        await b.close()
    return issues


def maak(car, out_png):
    """Rendert de story. Geeft (pad, problemen) terug."""
    import render as R
    R.IMG = os.path.join(config.WORK_DIR, 'fotos')
    c = dict(car, slug=car['id'])
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    issues = asyncio.run(_render(c, out_png))
    return out_png, issues


def controleer(png, issues):
    from PIL import Image
    f = [f'story tekst/uitlijning: {i}' for i in issues]
    try:
        im = Image.open(png)
        if im.size != (W, H):
            f.append(f'story heeft formaat {im.size} i.p.v. 1080x1920')
    except Exception as e:
        f.append(f'story onleesbaar: {e}')
    return f
