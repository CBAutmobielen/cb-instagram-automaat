"""Instagram-story (1080x1920) 'Nieuw binnen' in de huisstijl van template v2.

Zelfde kleuren, lettertypes en logo als de posts. Tekst blijft buiten de bovenste en onderste
~250 px (daar zet Instagram profielnaam, antwoordveld en knoppen).
"""
import os, re, sys, html as _html
from . import config

sys.path.insert(0, os.path.join(config.ROOT, 'cb'))
E = _html.escape
W, H = 1080, 1920

EXTRA = """
html,body,.s{width:1080px!important;height:1920px!important}
.tag{display:inline-flex;align-items:center;gap:14px;background:var(--o);color:#fff;font-family:'DM Sans';font-weight:700;
     font-size:26px;letter-spacing:.16em;text-transform:uppercase;padding:16px 26px;border-radius:6px;line-height:1}
.tag i{width:12px;height:12px;border-radius:50%;background:#fff;display:block}
.toplogo{position:absolute;right:72px;top:262px;height:40px}
.stat{flex:1;border-top:1px solid var(--line);padding-top:22px}
.stat .k{font-family:'DM Sans';font-weight:700;font-size:22px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
.stat .v{font-family:'Poppins';font-weight:600;font-size:44px;margin-top:12px;white-space:nowrap}
.hl{display:flex;align-items:center;gap:18px;background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:8px;
    height:78px;padding:0 24px;font-family:'Poppins';font-weight:500;font-size:31px;white-space:nowrap;overflow:hidden}
.hl svg{flex:none}
.cta{position:absolute;left:72px;right:72px;top:1590px;display:flex;align-items:center;justify-content:space-between}
.web{font-family:'DM Sans';font-weight:600;font-size:26px;letter-spacing:.06em;color:var(--mut)}
"""

VINK = ('<svg width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="15" fill="#EB5B28"/>'
        '<path d="M8.5 15.5l4.2 4.2 8.8-9.2" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def hoogtepunten(opts, n=4):
    """Cruise control altijd vooraan als de auto het heeft; daarna de sterkste opties uit de post."""
    eerst = [o for o in opts if re.search(r'cruise', o, re.I)]
    rest = [o for o in opts if o not in eerst]
    return (eerst + rest)[:n]


def html(c):
    import render as R
    import render_v2 as V
    v2 = c['v2']
    km = v2['kern'][1] if len(v2['kern']) > 1 else ''
    jaar = v2['kern'][0]
    hl = ''.join(f'<div class="hl">{VINK}<span data-fit="360">{E(o)}</span></div>' for o in hoogtepunten(v2['opties']))
    body = f"""
{R.ph(c, 'hero', 0, 340, 1080, 760)}
<div class="fade" style="top:340px;height:120px;transform:rotate(180deg)"></div>
<div class="fade" style="top:900px;height:200px"></div>
<div class="pad" style="top:258px;display:flex;justify-content:space-between;align-items:center">
  <div class="tag"><i></i>Nieuw binnen</div><img src="{R.LOGO}" style="height:40px;display:block">
</div>
<div class="pad" style="top:1040px">
  <div class="hd" data-fit="{V.CW}" style="font-size:112px">{E(v2['kop'])}</div>
  <div class="sub" data-fit="{V.CW}" style="font-size:36px;margin-top:10px">{E(v2['ondertitel'])}</div>
</div>
<div class="pad" style="top:1238px;display:flex;gap:40px">
  <div class="stat"><div class="k">Bouwjaar</div><div class="v">{E(jaar)}</div></div>
  <div class="stat"><div class="k">Kilometerstand</div><div class="v">{E(km)}</div></div>
  <div class="stat" style="flex:1.15"><div class="k">Vraagprijs</div><div class="v" style="color:var(--o)">{E(c['price'])}</div></div>
</div>
<div class="pad" style="top:1388px;display:grid;grid-template-columns:1fr 1fr;gap:14px">{hl}</div>
<div class="cta"><div class="btn" style="font-size:30px;padding:22px 34px">Stuur ons een DM</div><div class="web">CBAUTOMOBIELEN.NL</div></div>
"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{V.css()}{EXTRA}</style></head>
<body><div class="s">{body}</div>
<script>document.fonts.ready.then(()=>document.querySelectorAll('[data-fit]').forEach(el=>{{let s=parseFloat(getComputedStyle(el).fontSize);const max=+el.dataset.fit;while(el.scrollWidth>max&&s>20){{s-=1;el.style.fontSize=s+'px'}}}}));</script>
</body></html>"""


CHECK = """() => {
 const out=[];const r=e=>e.getBoundingClientRect();
 document.querySelectorAll('.hd,.sub,.stat .k,.stat .v,.hl,.btn,.web,.tag').forEach(e=>{const b=r(e);
  if(b.left<71.5||b.right>1008.5) out.push('marge:'+e.className+':'+e.innerText.slice(0,30));
  if(b.top<250||b.bottom>1670) out.push('buiten veilige zone:'+e.className+':'+Math.round(b.top)+'-'+Math.round(b.bottom));
  if(e.scrollWidth>e.clientWidth+1) out.push('afgesneden:'+e.innerText.slice(0,30));
  const fs=parseFloat(getComputedStyle(e).fontSize); if(fs<22) out.push('te klein:'+e.innerText.slice(0,30));
 });
 return out;}"""


async def render(c, out_png):
    from playwright.async_api import async_playwright
    import render as R
    hp = os.path.join(R.TMP, 'html', c['slug'], 'Story_v2.html')
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
