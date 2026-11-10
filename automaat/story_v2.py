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
.s{background:radial-gradient(900px 520px at 50% 1500px,rgba(235,91,40,.07),rgba(12,14,18,0) 70%),#0C0E12!important}
/* huisstijl cbautomobielen.nl: kaart #171A20, radius 14, rand 8% wit; Poppins 600 zonder hoofdletters; prijs wit */
.eyebrow{font-family:'Poppins';font-weight:600;font-size:24px;letter-spacing:.14em;text-transform:uppercase;color:var(--o);line-height:1}
.pill{display:inline-flex;align-items:center;gap:14px;background:rgba(12,14,18,.72);border:1px solid rgba(255,255,255,.14);
      border-radius:999px;padding:14px 24px 14px 20px;font-family:'Poppins';font-weight:600;font-size:24px;letter-spacing:.14em;
      text-transform:uppercase;color:#fff;line-height:1}
.pill i{width:12px;height:12px;border-radius:50%;background:var(--o);display:block;box-shadow:0 0 0 6px rgba(235,91,40,.25)}
.kaart{position:absolute;left:56px;right:56px;background:#171A20;border:1px solid rgba(255,255,255,.08);border-radius:14px;
       box-shadow:0 30px 80px rgba(0,0,0,.55);padding:38px 44px 40px}
.titel{font-family:'Poppins';font-weight:600;font-size:70px;letter-spacing:-.015em;line-height:1.02;color:#F5F5F4;white-space:nowrap}
.uitv{font-family:'Poppins';font-weight:500;font-size:32px;color:#94979C;margin-top:8px;white-space:nowrap}
.meta{display:flex;align-items:center;gap:18px;font-family:'DM Sans';font-weight:500;font-size:30px;color:#F5F5F4;margin-top:20px;white-space:nowrap}
.meta b{width:1px;height:26px;background:rgba(255,255,255,.22);display:block}
.onder{display:flex;justify-content:space-between;align-items:flex-end;margin-top:26px;border-top:1px solid rgba(255,255,255,.08);padding-top:26px}
.lijst{display:flex;flex-direction:column;gap:16px}
.punt{display:flex;align-items:center;gap:16px;font-family:'Poppins';font-weight:500;font-size:29px;color:#F5F5F4;white-space:nowrap}
.punt svg{flex:none}
.prijsrij{display:flex;justify-content:space-between;align-items:flex-end;margin-top:30px;border-top:1px solid rgba(255,255,255,.08);padding-top:28px}
.prijs{font-family:'Poppins';font-weight:600;font-size:66px;letter-spacing:-.015em;line-height:1;color:#F5F5F4;white-space:nowrap}
.rk{font-family:'DM Sans';font-weight:500;font-size:24px;color:#94979C;text-align:right;margin-top:12px;white-space:nowrap}
.hint{position:absolute;left:0;right:0;text-align:center;font-family:'Poppins';font-weight:600;font-size:26px;letter-spacing:.14em;
      text-transform:uppercase;color:#94979C}
.hint em{font-style:normal;color:var(--o)}
"""

VINK = ('<svg width="34" height="34" viewBox="0 0 34 34"><rect width="34" height="34" rx="9" fill="rgba(235,91,40,.14)"/>'
        '<path d="M10 17.5l4.6 4.6 9.4-9.8" stroke="#EB5B28" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def hoogtepunten(opts, n=4):
    """Cruise control altijd vooraan als de auto het heeft; daarna de sterkste opties uit de post."""
    eerst = [o for o in opts if re.search(r'cruise', o, re.I)]
    rest = [o for o in opts if o not in eerst]
    return (eerst + rest)[:n]


def html(c):
    """Opbouw (1080x1920), van boven naar beneden:
    - bovenste 250 px leeg (Instagram-profielbalk)
    - logo + 'Nieuw binnen'
    - grote foto van de voorkant, rand tot rand
    - kaart in de stijl van de autokaarten op cbautomobielen.nl: naam, uitvoering, km | bouwjaar | pk,
      drie hoogtepunten, vraagprijs
    - vrije ruimte voor de linksticker met een korte aanwijzing
    - onderste 250 px leeg (antwoordveld)"""
    import render as R
    v2 = c['v2']
    kern = [k for k in v2['kern'] if k]
    km = next((k for k in kern if 'km' in k), '')
    jaar = next((k for k in kern if re.fullmatch(r'(19|20)\d\d', k)), '')
    pk = next((k for k in kern if 'pk' in k), '')
    meta = '<b></b>'.join(f'<span>{E(x)}</span>' for x in (km, jaar, pk) if x)
    naam = v2['kop'].title() if v2['kop'].isupper() else v2['kop']
    naam = re.sub(r'\bUp!', 'up!', naam)
    naam = re.sub(r'\bBmw\b', 'BMW', re.sub(r'\bVw\b', 'VW', re.sub(r'(?<=-)Benz', 'Benz', naam)))
    punten = ''.join(f'<div class="punt">{VINK}<span data-fit="470">{E(o)}</span></div>' for o in hoogtepunten(v2['opties'], 3))
    rk = '<div class="rk">Rijklaar afgeleverd</div>' if v2.get('rijklaar') else ''   # alleen als het op de site staat
    body = f"""
<div class="pad" style="top:262px;display:flex;justify-content:space-between;align-items:center">
  <img src="{R.LOGO}" style="height:42px;display:block"><div class="pill"><i></i>Nieuw binnen</div>
</div>
{R.ph(c, 'hero', 0, 340, 1080, 810)}
<div class="fade" style="top:340px;height:90px;transform:rotate(180deg)"></div>
<div class="fade" style="top:1030px;height:120px"></div>
<div class="kaart" style="top:1096px">
  <div class="titel" data-fit="880">{E(naam)}</div>
  <div class="uitv" data-fit="880">{E(v2['ondertitel'])}</div>
  <div class="meta">{meta}</div>
  <div class="onder">
    <div class="lijst">{punten}</div>
    <div style="text-align:right"><div class="eyebrow" style="font-size:22px">Vraagprijs</div>
      <div class="prijs" style="margin-top:14px">{E(c['price'])}</div>{rk}</div>
  </div>
</div>
<div class="hint" style="top:1616px">Alle foto's via de link <em>&#8595;</em></div>
"""
    import render_v2 as V
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{V.css()}{EXTRA}</style></head>
<body><div class="s">{body}</div>
<script>document.fonts.ready.then(()=>document.querySelectorAll('[data-fit]').forEach(el=>{{let s=parseFloat(getComputedStyle(el).fontSize);const max=+el.dataset.fit;while(el.scrollWidth>max&&s>20){{s-=1;el.style.fontSize=s+'px'}}}}));</script>
</body></html>"""


CHECK = """() => {
 const out=[];const r=e=>e.getBoundingClientRect();
 document.querySelectorAll('.titel,.uitv,.meta,.punt,.prijs,.rk,.eyebrow,.pill,.hint,.kaart').forEach(e=>{const b=r(e);
  if(!e.classList.contains('hint')&&(b.left<55.5||b.right>1024.5)) out.push('marge:'+e.className+':'+e.innerText.slice(0,30));
  if(b.top<250||b.bottom>1670) out.push('buiten veilige zone:'+e.className+':'+Math.round(b.top)+'-'+Math.round(b.bottom));
  if(e.scrollWidth>e.clientWidth+1) out.push('afgesneden:'+e.innerText.slice(0,30));
  const fs=parseFloat(getComputedStyle(e).fontSize); if(!e.classList.contains('kaart')&&fs<22) out.push('te klein:'+e.innerText.slice(0,30));
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


def tekst_ideeen(titel, v2, prijs):
    """Twee korte tekstvoorstellen voor in het verhaal, alleen met gegevens van de website (geen verzinsels)."""
    naam = v2['kop'].title() if v2['kop'].isupper() else v2['kop']
    naam = re.sub(r'\bUp!', 'up!', re.sub(r'\bBmw\b', 'BMW', naam))
    hp = hoogtepunten(v2['opties'], 3)
    kern = ' · '.join(k for k in v2['kern'] if k)
    klein = lambda o: o[0].lower() + o[1:] if len(o) > 1 and o[1].islower() and not o.split()[0] in ('Apple', 'Android') else o
    hp = [hp[0]] + [klein(o) for o in hp[1:]] if hp else []
    lijst = ', '.join(hp[:-1]) + (' en ' + hp[-1] if len(hp) > 1 else (hp[0] if hp else ''))
    a = f"Net binnen! 🔥 {naam} {v2['ondertitel']}\n{lijst}.\n{kern} · {prijs}\nTik op de link voor alle foto's 👆"
    b = f"Wie wordt de nieuwe eigenaar? 🔑\n{naam}: {klein(lijst) if lijst else ''}.\nNu bij CB Automobielen in Sneek · {prijs}"
    return [a, b]
