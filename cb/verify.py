"""Controleert of de gerenderde slides exact gelijk zijn aan de referentie.

Gebruik:  python cb/verify.py
Vergelijkt output/ met cb/reference_hashes.json (SHA-256 per PNG, gemaakt op 4 okt 2026).
- "identiek": pixel- en bytegelijk aan het origineel.
- "afwijkend": dan is de auto aangepast (nieuwe prijs, nieuwe tekst) of draait een andere
  Chromium/Pillow-versie. Gebruik in dat geval de Docker-omgeving (zie README).
Auto's die niet in de referentie staan (nieuw toegevoegd) worden overgeslagen.
"""
import os, json, hashlib, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ref = json.load(open(os.path.join(ROOT, 'cb', 'reference_hashes.json')))
same = diff = missing = 0
for key, h in ref.items():
    f = os.path.join(ROOT, 'output', key)
    if not os.path.exists(f):
        missing += 1; continue
    if hashlib.sha256(open(f, 'rb').read()).hexdigest() == h: same += 1
    else: diff += 1; print('afwijkend:', key)
print(f'\nidentiek: {same}  afwijkend: {diff}  niet gerenderd: {missing}  (referentie: {len(ref)} slides)')
