"""Dagrapport: rapport/README.md (overzicht op GitHub), archief per dag, GitHub-samenvatting, optioneel e-mail."""
import os, smtplib, ssl
from email.message import EmailMessage
from . import config, db as dbm


class Rapport:
    def __init__(self, modus):
        self.modus = modus
        self.start = config.nu()
        self.regels, self.fouten, self.waarschuwingen = [], [], []
        self.nieuw, self.verkocht, self.wijzigingen = [], [], []
        self.gepubliceerd = None
        self.proef = None
        self.op_site = self.beschikbaar = None

    def log(self, t):
        print(t, flush=True); self.regels.append(t)

    def fout(self, t):
        print('FOUT:', t, flush=True); self.fouten.append(t)

    def waarschuwing(self, t):
        print('LET OP:', t, flush=True); self.waarschuwingen.append(t)

    def markdown(self, db):
        d = self.start.strftime('%A %d-%m-%Y %H:%M').capitalize()
        q = dbm.wachtrij(db)
        L = [f'# Instagram-automaat CB Automobielen', '',
             f'**Laatste controle:** {d} (Europe/Amsterdam) · modus: **{self.modus}** · '
             f'{"✅ geen fouten" if not self.fouten else f"⚠️ {len(self.fouten)} fout(en)"}', '',
             '| | |', '|---|---|',
             f'| Auto\'s op de website | {self.op_site if self.op_site is not None else "onbekend"} '
             f'({self.beschikbaar if self.beschikbaar is not None else "?"} beschikbaar) |',
             f'| Nieuwe auto\'s gevonden | {len(self.nieuw)}{": " + ", ".join(self.nieuw) if self.nieuw else ""} |',
             f'| Vandaag gepubliceerd | {self.gepubliceerd or "niets"} |',
             f'| In de wachtrij | {len(q)} |',
             f'| Verkocht / uit wachtrij | {", ".join(self.verkocht) if self.verkocht else "geen"} |', '']
        if self.proef:
            L += ['## Proefrun (niets gepubliceerd)', '', self.proef, '']
        if self.wijzigingen:
            L += ['## Prijs- en kilometerwijzigingen', ''] + [f'- {w}' for w in self.wijzigingen] + ['']
        if self.fouten:
            L += ['## Fouten', ''] + [f'- {f}' for f in self.fouten] + ['']
        if self.waarschuwingen:
            L += ['## Let op', ''] + [f'- {f}' for f in self.waarschuwingen] + ['']
        L += ['## Wachtrij', '']
        if q:
            L += ['| Gepland | Auto | Prijs | Ontdekt |', '|---|---|---|---|']
            L += [f"| {v.get('gepland') or '-'} | [{v['titel']}]({v['url']}) | {v.get('prijs') or ''} | {v['ontdekt']} |" for v in q]
        else:
            L += ['Leeg. Nieuwe auto\'s op de website komen hier automatisch in.']
        pub = sorted([v for v in db['voertuigen'].values() if v.get('instagram_post_id')],
                     key=lambda v: v['gepubliceerd_op'], reverse=True)[:15]
        L += ['', '## Laatst gepubliceerd', '']
        if pub:
            L += ['| Datum | Auto | Instagram |', '|---|---|---|']
            L += [f"| {v['gepubliceerd_op'][:16]} | {v['titel']} | {('[bekijk](' + v['instagram_permalink'] + ')') if v.get('instagram_permalink') else v['instagram_post_id']} |" for v in pub]
        else:
            L += ['Nog niets.']
        probleem = [v for v in db['voertuigen'].values() if v['status'] in ('fout', 'geen_fotos')]
        if probleem:
            L += ['', '## Vraagt aandacht', '']
            L += [f"- {v['titel']} ({v['status']}): {v['fouten'][-1]['melding'] if v['fouten'] else ''}" for v in probleem]
        L += ['', '## Verloop van deze run', '', '```'] + self.regels[-80:] + ['```', '']
        return '\n'.join(L)

    def schrijf(self, db):
        os.makedirs(os.path.join(config.REPORT_DIR, 'archief'), exist_ok=True)
        md = self.markdown(db)
        open(os.path.join(config.REPORT_DIR, 'README.md'), 'w', encoding='utf-8').write(md)
        open(os.path.join(config.REPORT_DIR, 'archief', self.start.strftime('%Y-%m-%d_%H%M') + f'_{self.modus}.md'),
             'w', encoding='utf-8').write(md)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(md)
        self.mail(md)
        return md

    def mail(self, md):
        """Optioneel: SMTP_HOST, SMTP_USER, SMTP_PASS, RAPPORT_EMAIL als secrets."""
        host, user, pw, to = (os.environ.get(k, '') for k in ('SMTP_HOST', 'SMTP_USER', 'SMTP_PASS', 'RAPPORT_EMAIL'))
        if not (host and user and pw and to):
            return
        alleen_bij = os.environ.get('RAPPORT_ALLEEN_BIJ', 'publicatie_of_fout')
        if alleen_bij == 'publicatie_of_fout' and not (self.gepubliceerd or self.fouten or self.nieuw):
            return
        m = EmailMessage()
        status = 'FOUT' if self.fouten else ('gepubliceerd' if self.gepubliceerd else 'controle')
        m['Subject'] = f'CB Instagram-automaat {self.start:%d-%m}: {status}'
        m['From'], m['To'] = user, to
        m.set_content(md)
        try:
            with smtplib.SMTP(host, int(os.environ.get('SMTP_PORT', '587')), timeout=30) as s:
                s.starttls(context=ssl.create_default_context()); s.login(user, pw); s.send_message(m)
        except Exception as e:
            print('e-mail versturen mislukt:', e)
