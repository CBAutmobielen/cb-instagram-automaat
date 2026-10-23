"""Hoofdprogramma: website controleren -> wachtrij -> carrousel + caption -> controles -> Instagram.

  python -m automaat.run --modus dagelijks   # geplande run (publiceert alleen als variabele PUBLICATIE=aan)
  python -m automaat.run --modus proef       # alles behalve publiceren (Instagram-container wordt wel getest)
  python -m automaat.run --modus live        # handmatig: nu publiceren (max. 1 per dag blijft gelden)
  python -m automaat.run --modus proef --auto 941609   # specifieke auto (ID = nummer achter in de URL)
"""
import argparse, json, os, shutil, sys, traceback
from datetime import timedelta
from . import config, db as dbm, site, content, ai, caption, qa, hosting, fotokeuze, story
from .rapport import Rapport

sys.path.insert(0, os.path.join(config.ROOT, 'cb'))


def render(car):
    os.environ.setdefault('CB_PHOTOS', os.path.join(config.WORK_DIR, 'fotos'))
    import render as R   # cb/render.py: vaste huisstijl, ongewijzigd ontwerp
    R.IMG = os.path.join(config.WORK_DIR, 'fotos')
    out = os.path.join(config.WORK_DIR, 'slides')
    files, issues = R.render([dict(car, slug=car['id'])], scales=[1], outroot=out)
    return files.get((car['id'], 1), []), issues


def render_met_herstel(car, R):
    """Rendert; bij afgekapte/te lange teksten automatisch kortere (echte) alternatieven proberen."""
    for ronde in range(5):
        paden, issues = render(car)
        if not issues:
            return paden, []
        R.log(f'  render ronde {ronde + 1}: {len(issues)} tekstprobleem/-problemen, automatisch inkorten')
        aangepast = False
        for i in issues:
            if 'Opties' in i and ('3 regels' in i or 'marge' in i):
                lang = max(car['options'], key=len)
                rest = [o for o in car.get('optie_kandidaten', []) if o not in car['options'] and len(o) < len(lang)]
                if rest:
                    car['options'][car['options'].index(lang)] = min(rest, key=len) if len(rest[0]) > 30 else rest[0]
                    aangepast = True
                if 'opt_head' in i or 'h:' in i:
                    car['opt_head'] = car['options'][0] + '.'; aangepast = True
            if 'Details' in i and ('overflow' in i or 'marge' in i):
                car['det_cap'] = [x for x in car['det_cap'] if len(x) <= 22][:3] or car['det_cap'][:2]
                car['det_head'] = car['det_head'][:30].rstrip(' ,') + ('.' if not car['det_head'][:30].endswith('.') else '')
                aangepast = True
            if 'Opties' in i and 'footer' not in i and not aangepast:
                car['opt_head'] = car['options'][0] + '.'; aangepast = True
        if not aangepast:
            return paden, issues
    return paden, issues


def sync(db, listing, R):
    eerste = not db['baseline_gedaan']
    R.op_site = len(listing)
    R.beschikbaar = sum(1 for x in listing.values() if x['beschikbaar'])
    for vid, it in listing.items():
        v = db['voertuigen'].get(vid)
        titel = it.get('titel') or it['tekst'][:80]
        if v is None:
            status = 'bestaand' if eerste else ('wachtrij' if it['beschikbaar'] else 'verkocht')
            v = dbm.nieuw_voertuig(vid, it['slug'], it['url'], titel, it['prijs'], it['km'], status)
            v['beschikbaar'] = it['beschikbaar']
            db['voertuigen'][vid] = v
            if status == 'wachtrij':
                R.nieuw.append(titel); R.log(f'NIEUW: {titel} -> wachtrij')
            continue
        v['laatst_gezien'] = config.vandaag()
        if it.get('titel') and v['titel'] != it['titel'] and not v.get('instagram_post_id'):
            v['titel'] = it['titel']
        if it['slug'] != v['slug']:
            dbm.wijziging(v, 'url', v['url'], it['url']); v['slug'], v['url'] = it['slug'], it['url']
        for veld, nieuw in (('prijs', it['prijs']), ('kilometerstand', it['km'])):
            if nieuw and v.get(veld) and nieuw != v[veld]:
                dbm.wijziging(v, veld, v[veld], nieuw)
                R.wijzigingen.append(f"{v['titel']}: {veld} {v[veld]} -> {nieuw}")
            if nieuw:
                v[veld] = nieuw
        if v['beschikbaar'] and not it['beschikbaar']:
            v['beschikbaar'] = False
            if v['status'] == 'wachtrij':
                v['status'] = 'verkocht'; R.verkocht.append(v['titel']); R.log(f"VERKOCHT (uit wachtrij): {v['titel']}")
        elif not v['beschikbaar'] and it['beschikbaar']:
            v['beschikbaar'] = True
            if v['status'] == 'verkocht' and not v.get('instagram_post_id'):
                v['status'] = 'wachtrij'; R.log(f"weer beschikbaar, terug in wachtrij: {v['titel']}")
        if v['status'] == 'geen_fotos' and it['beschikbaar']:
            v['status'] = 'wachtrij'   # opnieuw proberen; misschien zijn er nu foto's
    for vid, v in db['voertuigen'].items():
        if vid not in listing and v['beschikbaar']:
            v['beschikbaar'] = False
            if v['status'] == 'wachtrij':
                v['status'] = 'verkocht'; R.verkocht.append(v['titel']); R.log(f"VERWIJDERD van site (uit wachtrij): {v['titel']}")
    if eerste:
        db['baseline_gedaan'] = True
        R.log(f'Eerste run: {len(listing)} bestaande auto\'s vastgelegd als "bestaand" (worden niet automatisch gepost). '
              'Alleen auto\'s die hierna op de site verschijnen komen in de wachtrij.')


def publicatiedagen(start, n):
    """De eerstvolgende n publicatiedagen vanaf start (inclusief)."""
    dagen, d = [], start
    while len(dagen) < n:
        if d.weekday() in config.PUBLICATIE_DAGEN:
            dagen.append(d)
        d += timedelta(days=1)
    return dagen


def plan(db, vandaag_klaar):
    start = config.nu().date() + timedelta(days=1 if vandaag_klaar else 0)
    per = max(config.POSTS_PER_DAG, 1)
    q = dbm.wachtrij(db)
    dagen = publicatiedagen(start, len(q) // per + 1)
    for i, v in enumerate(q):
        v['gepland'] = dagen[i // per].isoformat()


def herstel_bezig(db, ig, R):
    """Een vorige run is midden in het publiceren gestopt: eerst op Instagram kijken of de post bestaat."""
    bezig = [v for v in db['voertuigen'].values() if v['status'] == 'bezig']
    if not bezig:
        return
    recent = ig.recente_posts() if ig else None
    for v in bezig:
        hit = next((m for m in (recent or []) if v['slug'] in (m.get('caption') or '')), None)
        if hit:
            v.update(status='gepubliceerd', instagram_post_id=hit['id'], instagram_permalink=hit.get('permalink'),
                     gepubliceerd_op=v.get('gepubliceerd_op') or hit.get('timestamp', config.vandaag()))
            R.log(f"herstel: {v['titel']} bleek al gepubliceerd ({hit.get('permalink')})")
        elif recent is not None:
            v['status'] = 'wachtrij'; R.log(f"herstel: {v['titel']} niet op Instagram gevonden, terug in wachtrij")


def verwerk(v, listing, db, ig, R, publiceren, proef):
    """Eén auto volledig afhandelen. Geeft True bij succes."""
    R.log(f"--- {v['titel']} (ID {v['id']}) ---")
    vers = site.voertuig(v['slug'])
    v['titel'], v['bouwjaar'] = vers['title'] or v['titel'], vers['table'].get('Bouwjaar')
    v['prijs'] = vers['prijs'] or v['prijs']
    if len(vers['fotos']) < config.MIN_FOTOS:
        v['status'] = 'geen_fotos'; dbm.fout(v, f"slechts {len(vers['fotos'])} foto's op de site")
        R.waarschuwing(f"{v['titel']}: te weinig echte foto's ({len(vers['fotos'])}), overgeslagen tot er foto's zijn")
        return False
    fotodir = os.path.join(config.WORK_DIR, 'fotos', v['id'])
    shutil.rmtree(fotodir, ignore_errors=True)
    site.download_fotos(vers, fotodir)

    car = content.concept(vers)
    notities, labels = fotokeuze.kies(car, vers, fotodir)        # gratis beeldherkenning
    for n in notities + (ai.verrijk(car, vers, fotodir) if config.ANTHROPIC_API_KEY else []):
        R.log('  ' + n)
    fouten = qa.fotos_herkomst(car, vers, fotodir)
    if fouten:   # eerst foto's in orde, anders niet eens renderen
        paden, issues = [], []
    else:
        paden, issues = render_met_herstel(car, R)
        fouten += qa.slides(paden, issues)
    fouten += qa.site_actueel(car, vers, listing.get(v['id']))
    story_png = None
    if config.STORY and paden:
        try:
            story_png, s_issues = story.maak(car, os.path.join(config.WORK_DIR, 'story', v['id'], 'story.png'))
            s_fouten = story.controleer(story_png, s_issues)
            if s_fouten:
                for f in s_fouten:
                    R.waarschuwing(f"{car['site_title']}: {f} (story wordt overgeslagen, post gaat wel door)")
                story_png = None
        except Exception as e:
            R.waarschuwing(f"{car['site_title']}: story maken mislukt ({e}); post gaat wel door")
            story_png = None
    tekst = caption.maak(car)
    fouten += caption.controleer(tekst, car, vers)
    recent = None
    if ig:
        recent = ig.recente_posts()
    if not proef:
        fouten += qa.dubbel(car, db, recent)
    v['afbeeldingen_status'] = 'OK' if not any('slide' in f.lower() or 'foto' in f.lower() or 'tekst' in f.lower() for f in fouten) else 'fout'
    v['caption_status'] = 'OK' if not any('caption' in f for f in fouten) else 'fout'

    # altijd een kopie voor controle (GitHub-artefact)
    proefmap = os.path.join(config.WORK_DIR, 'uitvoer', f"{v['id']} {car['site_title']}")
    shutil.rmtree(proefmap, ignore_errors=True); os.makedirs(proefmap, exist_ok=True)
    jpgs = hosting.naar_jpeg(paden, proefmap) if paden else []
    open(os.path.join(proefmap, 'caption.txt'), 'w', encoding='utf-8').write(tekst)
    if story_png:
        hosting.naar_jpeg([story_png], proefmap, 'story')
    if labels:
        fotokeuze.contactsheet(fotodir, labels, car['photos'], os.path.join(proefmap, 'fotoherkenning.jpg'))
    json.dump({k: car[k] for k in car if k != 'optie_kandidaten'}, open(os.path.join(proefmap, 'carrousel.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    if fouten:
        for f in fouten:
            R.fout(f"{car['site_title']}: {f}"); dbm.fout(v, f)
        if not proef:
            v['pogingen'] += 1
            if v['pogingen'] >= config.MAX_POGINGEN:
                v['status'] = 'fout'; R.fout(f"{car['site_title']}: {config.MAX_POGINGEN}x mislukt, uit de automatische wachtrij gehaald")
        return False
    R.log(f'  alle controles geslaagd ({len(paden)} slides, caption {len(tekst)} tekens)')

    if proef:
        R.proef = f"**{car['site_title']}** ({car['price']}): 5 slides en caption gemaakt, alle controles geslaagd."
        if config.GITHUB_REPOSITORY:
            doel = os.path.join(config.ROOT, 'proef', v['id'])
            shutil.rmtree(doel, ignore_errors=True)
            pj = hosting.naar_jpeg(paden, doel)
            sj = hosting.naar_jpeg([story_png], doel, 'story') if story_png else []
            open(os.path.join(doel, 'caption.txt'), 'w', encoding='utf-8').write(tekst)
            if labels:
                fotokeuze.contactsheet(fotodir, labels, car['photos'], os.path.join(doel, 'fotoherkenning.jpg'))
            R.proef += f" Bekijk de slides in de map `proef/{v['id']}/`."
        if ig and config.GITHUB_REPOSITORY:
            sha = hosting.commit_push(f"proef: slides {car['site_title']}", [doel])
            urls = hosting.publiceer_beelden(pj + sj, sha)
            cid = ig.maak_carrousel(urls[:len(pj)], tekst)
            if sj:
                scid = ig.maak_story(urls[-1])
                R.proef += f" Story-container `{scid}` ook goedgekeurd (niet geplaatst)."
            R.proef += (f" Instagram-koppeling getest: carrousel-container `{cid}` aangemaakt en goedgekeurd door Instagram"
                        f" (status FINISHED). **Niet gepubliceerd**; de container vervalt automatisch na 24 uur.")
            R.log(f'  proef: Instagram-container {cid} OK, niet gepubliceerd')
        return True

    if not publiceren:
        R.log('  publiceren staat UIT (variabele PUBLICATIE): slides gemaakt maar niet geplaatst')
        R.proef = f"**{car['site_title']}** zou vandaag gepubliceerd worden; publiceren staat uit."
        return True

    # --- live publiceren ---
    doel = os.path.join(config.PUBLISH_DIR, v['id'])
    shutil.rmtree(doel, ignore_errors=True)
    pj = hosting.naar_jpeg(paden, doel)
    sj = hosting.naar_jpeg([story_png], doel, 'story') if story_png else []
    open(os.path.join(doel, 'caption.txt'), 'w', encoding='utf-8').write(tekst)
    v['status'] = 'bezig'; v['gepubliceerd_op'] = config.nu().strftime('%Y-%m-%d %H:%M')
    dbm.bewaar(db)
    sha = hosting.commit_push(f"publicatie gestart: {car['site_title']}", [doel, config.DB_PATH])
    urls = hosting.publiceer_beelden(pj + sj, sha)
    cid = ig.maak_carrousel(urls[:len(pj)], tekst)
    # allerlaatste controle vlak voor publiceren: is de auto nog niet op Instagram gezet?
    dub = qa.dubbel(car, {'voertuigen': {}}, ig.recente_posts(25))
    if dub:
        raise RuntimeError('; '.join(dub))
    mid, link = ig.publiceer(cid)
    v.update(status='gepubliceerd', instagram_post_id=mid, instagram_permalink=link,
             gepubliceerd_op=config.nu().strftime('%Y-%m-%d %H:%M'), gepland=None)
    R.gepubliceerd = f"[{car['site_title']}]({link or v['url']})"
    R.log(f'  GEPUBLICEERD op Instagram: {link or mid}')
    if sj:
        try:   # story is een extraatje: mislukt hij, dan blijft de post gewoon staan
            dbm.bewaar(db)
            sid, _ = ig.publiceer(ig.maak_story(urls[-1]))
            v['instagram_story_id'] = sid
            R.gepubliceerd += ' + story'
            R.log(f'  story geplaatst ({sid})')
        except Exception as e:
            R.waarschuwing(f"{car['site_title']}: story plaatsen mislukt ({e}); de post staat wel online")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modus', choices=['dagelijks', 'proef', 'live'], default='proef')
    ap.add_argument('--auto', default='', help='voertuig-ID (nummer achter in de URL) om te forceren')
    ap.add_argument('--negeer-tijd', action='store_true')
    a = ap.parse_args()

    publicatie_aan = os.environ.get('PUBLICATIE', '').strip().lower() == 'aan'
    proef = a.modus == 'proef'
    publiceren = a.modus == 'live' or (a.modus == 'dagelijks' and publicatie_aan)
    R = Rapport(a.modus + ('' if a.modus != 'dagelijks' else (' (publiceren AAN)' if publicatie_aan else ' (publiceren UIT)')))
    db = dbm.laad()

    if a.modus == 'dagelijks' and not a.negeer_tijd:
        # GitHub start om 06:00 én 07:00 UTC (zomer- en wintertijd). Alleen de run vanaf 08:00 NL-tijd telt.
        if config.nu().hour < config.PUBLICATIE_UUR:
            print(f'Het is {config.nu():%H:%M} in Nederland, nog geen {config.PUBLICATIE_UUR}:00. Niets gedaan.'); return 0
        if any(r.get('modus') == 'dagelijks' and r.get('datum') == config.vandaag() and not r.get('fouten') for r in db['runs']):
            print('Dagelijkse run is vandaag al zonder fouten uitgevoerd. Niets gedaan.'); return 0

    ig = None
    try:
        if config.IG_TOKEN_SECRET and config.IG_USER_ID:
            from .instagram import Instagram
            ig = Instagram()
            info = ig.verbind()
            R.log(f"Instagram verbonden: @{info.get('username')} | token: {ig.vernieuw_token()}")
            lim = ig.limiet()
            if lim:
                R.log(f"Instagram publicatielimiet: {lim.get('quota_usage')} van {lim.get('config', {}).get('quota_total')} gebruikt (24 uur)")
        elif publiceren:
            R.fout('Instagram is nog niet gekoppeld (secrets IG_ACCESS_TOKEN / IG_USER_ID ontbreken): niets gepubliceerd')
            publiceren = False
        else:
            R.waarschuwing('Instagram nog niet gekoppeld: alleen slides en caption gemaakt')
    except Exception as e:
        R.fout(f'Instagram-verbinding: {e}'); ig = None; publiceren = False

    try:
        herstel_bezig(db, ig, R)
        listing = site.aanbod()
        R.log(f'Website: {len(listing)} auto\'s gevonden, {sum(x["beschikbaar"] for x in listing.values())} beschikbaar')
        sync(db, listing, R)

        if a.auto:
            v = db['voertuigen'].get(a.auto)
            if not v or a.auto not in listing:
                raise RuntimeError(f'auto {a.auto} staat niet op de website')
            if not proef and v.get('instagram_post_id'):
                raise RuntimeError(f"auto {a.auto} is al gepubliceerd ({v['instagram_permalink']})")
            kandidaten = [v]
        else:
            kandidaten = dbm.wachtrij(db)
            if proef and not kandidaten:
                kandidaten = [v for v in db['voertuigen'].values() if v['beschikbaar']][:1]
                if kandidaten:
                    R.log(f"Wachtrij leeg: proef met bestaande auto {kandidaten[0]['titel']}")

        al = len(dbm.vandaag_gepubliceerd(db))
        if not proef and not a.auto and config.nu().weekday() not in config.PUBLICATIE_DAGEN:
            dagen = ', '.join(config.DAGNAMEN[i] for i in config.PUBLICATIE_DAGEN)
            R.log(f'Vandaag is geen publicatiedag (publicatiedagen: {dagen}). Website gecontroleerd, wachtrij bijgewerkt.')
            kandidaten = []
        elif not proef and al >= config.POSTS_PER_DAG:
            R.log(f'Vandaag is al {al} auto gepubliceerd; maximum {config.POSTS_PER_DAG} per dag. Overige blijven in de wachtrij.')
            kandidaten = []
        if not kandidaten:
            R.log('Geen nieuwe auto\'s om te publiceren.')
        gelukt = False
        for v in kandidaten[:3]:
            try:
                if verwerk(v, listing, db, ig, R, publiceren, proef):
                    gelukt = True; break
            except Exception as e:
                R.fout(f"{v['titel']}: {e}"); dbm.fout(v, e)
                traceback.print_exc()
                if v['status'] == 'bezig':
                    # publicatie onderbroken: volgende run controleert eerst Instagram (geen dubbele post)
                    pass
                elif not proef:
                    v['pogingen'] += 1
                    if v['pogingen'] >= config.MAX_POGINGEN:
                        v['status'] = 'fout'
            dbm.bewaar(db)
        plan(db, bool(dbm.vandaag_gepubliceerd(db)))
    except site.SiteFout as e:
        R.fout(f'Website: {e}')
    except Exception as e:
        R.fout(f'Onverwachte fout: {e}'); traceback.print_exc()

    db['runs'].append({'datum': config.vandaag(), 'tijd': config.nu().strftime('%H:%M'), 'modus': a.modus,
                       'nieuw': len(R.nieuw), 'gepubliceerd': R.gepubliceerd, 'fouten': R.fouten[:10]})
    dbm.bewaar(db)
    R.schrijf(db)
    return 1 if R.fouten else 0


if __name__ == '__main__':
    sys.exit(main())
