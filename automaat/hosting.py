"""Slides openbaar beschikbaar maken zodat Instagram ze kan ophalen (vereiste van de API).

De JPEG's worden in deze (openbare) GitHub-repository gezet onder gepubliceerd/<id>/ en via
raw.githubusercontent.com aangeboden. Er staan geen geheimen in de repository.
"""
import os, shutil, subprocess, time
import requests
from PIL import Image
from . import config


def naar_jpeg(pngs, doelmap):
    os.makedirs(doelmap, exist_ok=True)
    uit = []
    for i, p in enumerate(pngs, 1):
        d = os.path.join(doelmap, f'slide-{i}.jpg')
        Image.open(p).convert('RGB').save(d, 'JPEG', quality=95, subsampling=0, optimize=True)
        uit.append(d)
    return uit


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=config.ROOT, check=check, capture_output=True, text=True)


def commit_push(bericht, paden):
    git('add', '-A', *paden)
    if git('diff', '--cached', '--quiet', check=False).returncode == 0:
        return git('rev-parse', 'HEAD').stdout.strip()
    git('commit', '-m', bericht)
    for poging in range(5):
        r = git('push', check=False)
        if r.returncode == 0:
            break
        git('pull', '--rebase', '-X', 'ours', check=False)
        time.sleep(3 * (poging + 1))
    else:
        raise RuntimeError(f'git push mislukt: {r.stderr[-300:]}')
    return git('rev-parse', 'HEAD').stdout.strip()


def publiceer_beelden(jpgs, sha):
    if not config.GITHUB_REPOSITORY:
        raise RuntimeError('GITHUB_REPOSITORY onbekend: openbare URL kan niet gemaakt worden')
    urls = []
    for p in jpgs:
        rel = os.path.relpath(p, config.ROOT).replace(os.sep, '/')
        urls.append(f'https://raw.githubusercontent.com/{config.GITHUB_REPOSITORY}/{sha}/{rel}')
    # wachten tot de bestanden echt online staan
    for u in urls:
        for poging in range(24):
            try:
                r = requests.head(u, timeout=20)
                if r.status_code == 200 and r.headers.get('content-type', '').startswith('image/jpeg'):
                    break
            except requests.RequestException:
                pass
            time.sleep(5)
        else:
            raise RuntimeError(f'afbeelding niet openbaar bereikbaar: {u} (staat de repository op Openbaar?)')
    return urls
