"""Verkoopklaar-controle: wanneer is een auto 'nieuw' voor Instagram?

Een auto is verkoopklaar zodra hij op de website staat met
  1. een geldige vraagprijs (geen 'Op aanvraag'), EN
  2. echte foto's: minimaal config.MIN_FOTOS foto's in de galerij (een 'verwacht'-plaatje of
     een paar standaardfoto's telt niet).
Een Marktplaats-advertentie (link op de voertuigpagina) wordt vastgelegd als extra bevestiging,
maar is niet verplicht.

Het moment dat een auto voor het eerst op de site verscheen speelt GEEN rol: iedere controle
bekijkt alle auto's die nog nooit op Instagram zijn gezet opnieuw.
"""
import re
from . import config, db as dbm

# statussen die betekenen: nog nooit gepost en (nog) niet in de wachtrij -> bij iedere controle opnieuw bekijken
OPNIEUW_BEKIJKEN = ('niet_klaar', 'zonder_prijs', 'geen_fotos', 'verkocht', 'verlopen')
MIN_PRIJS = 500


def geldige_prijs(prijs):
    if not prijs:
        return False
    cijfers = re.sub(r'\D', '', str(prijs))
    return bool(cijfers) and int(cijfers) >= MIN_PRIJS


def beoordeel(vers):
    """Beoordeel een uitgelezen voertuigpagina. Geeft (klaar, reden, details)."""
    n = len(vers.get('fotos') or [])
    mp = bool(vers.get('marktplaats'))
    d = {'datum': config.vandaag(), 'prijs': vers.get('prijs') or None, 'fotos': n, 'marktplaats': mp}
    if vers.get('op_aanvraag') or not geldige_prijs(vers.get('prijs')):
        return False, 'nog geen vraagprijs op de voertuigpagina', d
    if n < config.MIN_FOTOS:
        return False, f"nog geen echte foto's ({n} foto's, minimaal {config.MIN_FOTOS})", d
    return True, 'vraagprijs en echte foto\'s aanwezig' + (' (ook op Marktplaats)' if mp else ''), d


def _handtekening(d):
    return (d or {}).get('prijs'), (d or {}).get('fotos')


def controleer_alle(db, listing, site, R):
    """Draait bij iedere synchronisatie over ALLE auto's op de site die nog nooit gepost zijn."""
    tel = {'gepost': 0, 'wachtrij': 0, 'nieuw_klaar': 0, 'niet_klaar': 0, 'oude_voorraad': 0}
    for vid, it in listing.items():
        v = db['voertuigen'].get(vid)
        if not v:
            continue
        # 4. al op Instagram? Dan nooit opnieuw, ook niet als prijs of foto's veranderen
        if v.get('instagram_post_id') or v['status'] in ('gepubliceerd', 'bezig'):
            tel['gepost'] += 1; continue
        if v['status'] == 'wachtrij':
            tel['wachtrij'] += 1; continue
        oude_voorraad = v['status'] == 'bestaand'
        if oude_voorraad and v.get('klaar'):
            tel['oude_voorraad'] += 1; continue          # stond al verkoopklaar op de site bij de start (22-10)
        if v['status'] not in OPNIEUW_BEKIJKEN + ('bestaand', 'fout'):
            continue

        # 1. prijs in het overzicht: zonder prijs hoeft de voertuigpagina niet eens opgehaald te worden
        if not it['beschikbaar'] or not geldige_prijs(it.get('prijs')):
            if v['status'] == 'verkocht':
                tel['niet_klaar'] += 1; continue          # uit de wachtrij gehaald; komt terug zodra er weer een prijs staat
            _niet_klaar(v, 'nog geen vraagprijs (Op aanvraag)', {'datum': config.vandaag(), 'prijs': None,
                        'fotos': (v.get('klaar') or {}).get('fotos'), 'marktplaats': (v.get('klaar') or {}).get('marktplaats')}, R)
            tel['niet_klaar'] += 1; continue

        # 2. + 3. foto's en Marktplaats: voertuigpagina lezen
        try:
            vers = site.voertuig(v['slug'])
        except Exception as e:
            R.waarschuwing(f"{v['titel']}: voertuigpagina niet te lezen ({e}); volgende controle opnieuw")
            continue
        klaar, reden, d = beoordeel(vers)

        if v['status'] == 'fout':
            # na 3 mislukte pogingen: alleen opnieuw proberen als er iets aan de auto op de site is veranderd
            if klaar and _handtekening(d) != _handtekening(v.get('klaar')):
                v['pogingen'] = 0; v['status'] = 'wachtrij'; v['klaar'] = d
                R.log(f"{v['titel']}: gegevens op de site gewijzigd na eerdere fout, opnieuw in de wachtrij")
                tel['wachtrij'] += 1
            else:
                v['klaar'] = d
            continue

        if oude_voorraad:
            v['klaar'] = d
            if klaar:
                tel['oude_voorraad'] += 1                 # was al verkoopklaar voor de automaat startte
            else:
                v['status'] = 'niet_klaar'; v['niet_klaar_reden'] = reden
                R.log(f"{v['titel']}: stond bij de start op de site maar is nog niet verkoopklaar ({reden}); "
                      'wordt gepost zodra hij dat wel is')
                tel['niet_klaar'] += 1
            continue

        if klaar:
            v.setdefault('eerst_op_site', v.get('ontdekt'))
            v['ontdekt'] = config.vandaag()                # 'nieuw' vanaf het moment dat hij verkoopklaar is
            v['verkoopklaar_sinds'] = config.vandaag()
            v['status'] = 'wachtrij'; v['klaar'] = d; v['pogingen'] = 0; v.pop('niet_klaar_reden', None)
            R.nieuw.append(v['titel'])
            R.log(f"VERKOOPKLAAR: {v['titel']} ({reden}; op de site sinds {v['eerst_op_site']}) -> wachtrij")
            tel['nieuw_klaar'] += 1
        else:
            _niet_klaar(v, reden, d, R)
            tel['niet_klaar'] += 1
    R.klaar_telling = tel
    R.log(f"Verkoopklaar-controle: {sum(tel.values())} auto's bekeken | al op Instagram {tel['gepost']} | "
          f"in wachtrij {tel['wachtrij']} (waarvan {tel['nieuw_klaar']} nieuw) | nog niet verkoopklaar {tel['niet_klaar']} | "
          f"oude voorraad {tel['oude_voorraad']}")
    return tel


def _niet_klaar(v, reden, d, R):
    if v['status'] != 'niet_klaar' or v.get('niet_klaar_reden') != reden:
        R.log(f"nog niet verkoopklaar: {v['titel']} ({reden})")
    v['status'] = 'niet_klaar'; v['niet_klaar_reden'] = reden; v['klaar'] = d
