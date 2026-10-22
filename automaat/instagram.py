"""Officiële Instagram API (Instagram Platform / Graph API): carrousel publiceren, token vernieuwen.

Flow volgens Meta-documentatie:
  1. per slide een item-container  POST /{ig-user-id}/media  image_url=...  is_carousel_item=true
  2. carrousel-container           POST /{ig-user-id}/media  media_type=CAROUSEL children=... caption=...
  3. wachten tot status FINISHED   GET  /{container-id}?fields=status_code
  4. publiceren                    POST /{ig-user-id}/media_publish creation_id=...
Containers die niet gepubliceerd worden verlopen na 24 uur en zijn nooit zichtbaar (gebruikt in proefmodus).
"""
import base64, hashlib, json, os, time
import requests
from cryptography.fernet import Fernet, InvalidToken
from . import config


class IGFout(Exception):
    pass


def _key():
    # sleutel afgeleid van het (geheime) begintoken: geen extra secret nodig
    return base64.urlsafe_b64encode(hashlib.sha256(b'cb-automaat|' + config.IG_TOKEN_SECRET.encode()).digest())


def _lees_store():
    if not os.path.exists(config.TOKEN_STORE) or not config.IG_TOKEN_SECRET:
        return None
    try:
        return json.loads(Fernet(_key()).decrypt(open(config.TOKEN_STORE, 'rb').read()))
    except (InvalidToken, ValueError):
        return None


def _schrijf_store(token, vernieuwd):
    os.makedirs(os.path.dirname(config.TOKEN_STORE), exist_ok=True)
    blob = Fernet(_key()).encrypt(json.dumps({'token': token, 'vernieuwd': vernieuwd}).encode())
    open(config.TOKEN_STORE, 'wb').write(blob)


class Instagram:
    def __init__(self):
        if not config.IG_TOKEN_SECRET or not config.IG_USER_ID:
            raise IGFout('IG_ACCESS_TOKEN en/of IG_USER_ID ontbreken (GitHub secrets)')
        self.base = f'https://{config.IG_HOST}/{config.IG_VERSION}'
        st = _lees_store()
        self.kandidaten = ([st['token']] if st else []) + [config.IG_TOKEN_SECRET]
        self.vernieuwd = st['vernieuwd'] if st else None
        self.token = None
        self.info = None

    # -- basis --
    def _req(self, method, path, **params):
        params['access_token'] = self.token
        for poging in range(4):
            try:
                r = requests.request(method, f'{self.base}/{path}', data=params if method == 'POST' else None,
                                     params=None if method == 'POST' else params, timeout=60)
            except requests.RequestException as e:
                if poging == 3: raise IGFout(f'netwerkfout: {e}')
                time.sleep(5 * (poging + 1)); continue
            j = r.json() if r.content else {}
            if r.status_code >= 500 or (j.get('error', {}).get('is_transient')):
                if poging == 3: raise IGFout(f'Instagram tijdelijk niet beschikbaar: {j}')
                time.sleep(10 * (poging + 1)); continue
            if 'error' in j:
                e = j['error']
                raise IGFout(f"Instagram-fout {e.get('code')}/{e.get('error_subcode')}: {e.get('message')}")
            return j

    def verbind(self):
        """Kies het eerste werkende token en controleer het account."""
        laatste = None
        for t in self.kandidaten:
            self.token = t
            try:
                self.info = self._req('GET', config.IG_USER_ID, fields='id,username')
                return self.info
            except IGFout as e:
                laatste = e
        raise IGFout(f'geen geldig Instagram-token: {laatste}. Maak een nieuw token aan (zie HANDLEIDING.md).')

    def vernieuw_token(self, dagen=7):
        """Long-lived tokens (60 dagen) wekelijks verlengen. Alleen bij Instagram-login (graph.instagram.com)."""
        if config.IG_HOST != 'graph.instagram.com':
            return 'niet nodig (Facebook-login/systeemgebruiker)'
        if self.vernieuwd and (time.time() - self.vernieuwd) < dagen * 86400:
            return 'recent vernieuwd'
        r = requests.get('https://graph.instagram.com/refresh_access_token',
                         params={'grant_type': 'ig_refresh_token', 'access_token': self.token}, timeout=60).json()
        if 'access_token' not in r:
            return f'vernieuwen mislukt: {r.get("error", r)}'
        self.token = r['access_token']; self.vernieuwd = time.time()
        _schrijf_store(self.token, self.vernieuwd)
        return f"vernieuwd, geldig tot ca. {time.strftime('%Y-%m-%d', time.localtime(time.time() + r.get('expires_in', 0)))}"

    def recente_posts(self, n=50):
        j = self._req('GET', f'{config.IG_USER_ID}/media', fields='id,caption,permalink,timestamp', limit=n)
        return j.get('data', [])

    def limiet(self):
        try:
            j = self._req('GET', f'{config.IG_USER_ID}/content_publishing_limit', fields='quota_usage,config')
            return j.get('data', [{}])[0]
        except IGFout:
            return {}

    # -- publiceren --
    def _wacht(self, cid, maxs=300):
        t0 = time.time()
        while time.time() - t0 < maxs:
            s = self._req('GET', cid, fields='status_code,status').get('status_code')
            if s == 'FINISHED':
                return
            if s in ('ERROR', 'EXPIRED'):
                raise IGFout(f'container {cid} status {s}')
            time.sleep(5)
        raise IGFout(f'container {cid} niet klaar binnen {maxs}s')

    def maak_carrousel(self, image_urls, caption):
        """Stap 1-3. Geeft carrousel-container-ID terug (nog NIET zichtbaar)."""
        if not 2 <= len(image_urls) <= 10:
            raise IGFout('carrousel heeft 2 tot 10 afbeeldingen nodig')
        kids = []
        for u in image_urls:
            kids.append(self._req('POST', f'{config.IG_USER_ID}/media', image_url=u, is_carousel_item='true')['id'])
        for k in kids:
            self._wacht(k)
        cid = self._req('POST', f'{config.IG_USER_ID}/media', media_type='CAROUSEL',
                        children=','.join(kids), caption=caption)['id']
        self._wacht(cid)
        return cid

    def publiceer(self, container_id):
        """Stap 4: maakt de post openbaar. Geeft (media_id, permalink)."""
        mid = self._req('POST', f'{config.IG_USER_ID}/media_publish', creation_id=container_id)['id']
        try:
            link = self._req('GET', mid, fields='permalink').get('permalink')
        except IGFout:
            link = None
        return mid, link
