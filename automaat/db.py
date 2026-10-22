"""Eenvoudige, betrouwbare JSON-database (in git, dus met volledige geschiedenis).

Statussen per voertuig:
  bestaand      - stond al op de site bij de eerste ingebruikname; wordt niet automatisch gepost
  wachtrij      - nieuw ontdekt, wacht op publicatie
  bezig         - publicatie gestart (Instagram-aanroep loopt); bij herstart eerst controleren op Instagram
  gepubliceerd  - staat op Instagram (instagram_post_id ingevuld). Nooit nogmaals als nieuwe-voorraadpost
  verkocht      - verdwenen of 'Op aanvraag' voordat hij gepost is (uit de wachtrij gehaald)
  fout          - na meerdere pogingen niet gelukt; handmatige controle nodig
  geen_fotos    - te weinig echte foto's op de site; wordt opnieuw bekeken zodra er foto's zijn
"""
import json, os, tempfile
from . import config

LEEG = {'versie': 1, 'baseline_gedaan': False, 'voertuigen': {}, 'runs': []}


def laad():
    if not os.path.exists(config.DB_PATH):
        return json.loads(json.dumps(LEEG))
    with open(config.DB_PATH, encoding='utf-8') as f:
        return json.load(f)


def bewaar(db):
    """Atomisch schrijven: eerst tijdelijk bestand, dan hernoemen. Nooit een halve database."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    db['runs'] = db['runs'][-120:]
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(config.DB_PATH), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write('\n')
    os.replace(tmp, config.DB_PATH)


def nieuw_voertuig(vid, slug, url, titel, prijs, km, status):
    return {
        'id': vid, 'slug': slug, 'url': url, 'titel': titel,
        'status': status, 'beschikbaar': True,
        'ontdekt': config.vandaag(), 'laatst_gezien': config.vandaag(),
        'prijs': prijs, 'kilometerstand': km, 'bouwjaar': None,
        'afbeeldingen_status': 'nog niet gemaakt', 'caption_status': 'nog niet gemaakt',
        'gepland': None, 'gepubliceerd_op': None, 'instagram_post_id': None, 'instagram_permalink': None,
        'pogingen': 0, 'fouten': [], 'wijzigingen': [],
    }


def fout(v, melding):
    v['fouten'].append({'datum': config.nu().strftime('%Y-%m-%d %H:%M'), 'melding': str(melding)[:500]})
    v['fouten'] = v['fouten'][-20:]


def wijziging(v, veld, oud, nieuw):
    v['wijzigingen'].append({'datum': config.vandaag(), 'veld': veld, 'oud': oud, 'nieuw': nieuw})
    v['wijzigingen'] = v['wijzigingen'][-50:]


def wachtrij(db):
    q = [v for v in db['voertuigen'].values() if v['status'] == 'wachtrij' and v['beschikbaar']]
    return sorted(q, key=lambda v: (v['ontdekt'], v['id']))


def vandaag_gepubliceerd(db):
    d = config.vandaag()
    return [v for v in db['voertuigen'].values() if (v.get('gepubliceerd_op') or '').startswith(d)]
