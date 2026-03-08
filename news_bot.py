"""
CourtKing News Bot v4 — COMPLETO
Genera 3 archivos JSON que el portal lee desde GitHub CDN:
  - noticias.json  → noticias por deporte (Google News RSS)
  - videos.json    → videos YouTube por deporte (YouTube Data API v3)
  - partidos.json  → partidos NBA + Liga MX + Premier Padel (ESPN API)

Se ejecuta automáticamente cada 8 horas via GitHub Actions.
"""

import re, json, time, hashlib, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
YT_API_KEY = 'AIzaSyABQSy5j3HOeFVFxijwZUw5SNFNyLbdAIw'

YT_CHANNELS = {
    'bk': 'UCWJ2lWNubArHWmf3FIHbfcQ',
    'pd': 'UCaJRfYmUhhBjt0VbVuJoNxw',
    'fx': 'UCENlPaQeGAMnDiqByIWyFSQ',
}

YT_QUERIES = {
    'bk': ['NBA highlights 2026', 'basketball mejores jugadas'],
    'pd': ['Premier Padel 2026 highlights', 'padel mejores puntos'],
    'fx': ['Champions League 2026 highlights', 'LaLiga goles 2026'],
}

NEWS_FEEDS = {
    'bk': [
        'https://news.google.com/rss/search?q=NBA+basketball+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=basketball+highlights+NBA+hoy&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'pd': [
        'https://news.google.com/rss/search?q=Premier+Padel+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+torneo+ranking+2026&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'fx': [
        'https://news.google.com/rss/search?q=Champions+League+UEFA+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Premier+League+LaLiga+futbol+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Copa+del+Mundo+FIFA+seleccion+futbol&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
}

ESPN_APIS = {
    'bk': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
    'fx': 'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?limit=10',
}

PADEL_CALENDAR = [
    {'fecha': '1-8 Mar 2026',   'torneo': 'Gijon P2',    'liga': 'Premier Padel Espana',  'url': 'https://www.padelfip.com/es/evento/gijon-p2-2026/',                          'live': True},
    {'fecha': '16-22 Mar 2026', 'torneo': 'Cancun P2',   'liga': 'Premier Padel Mexico',  'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
    {'fecha': '23-29 Mar 2026', 'torneo': 'Miami P1',    'liga': 'Premier Padel EUA',     'url': 'https://www.miamipremierpadel.com/',                                         'live': False},
    {'fecha': '6-11 Abr 2026',  'torneo': 'Qatar Major', 'liga': 'Premier Padel Doha',    'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
    {'fecha': 'Abr 2026',       'torneo': 'Bruselas P2', 'liga': 'Premier Padel Belgica', 'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
    {'fecha': 'May 2026',       'torneo': 'Madrid Major','liga': 'Premier Padel Espana',  'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
    {'fecha': 'Jun 2026',       'torneo': 'Paris P1',    'liga': 'Premier Padel Francia', 'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
    {'fecha': 'Nov 2026',       'torneo': 'Mexico Major','liga': 'Premier Padel Acapulco','url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026',     'live': False},
]

MAX_NEWS    = 6
MAX_VIDEOS  = 8
MAX_MATCHES = 8

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; CourtkingBot/4.0)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f'    aviso fetch: {e}')
        return None

def fetch_json(url):
    data = fetch(url)
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception as e:
        print(f'    aviso json: {e}')
        return None

def format_date(pub_str):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str)
        meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        return f'{dt.day} {meses[dt.month-1]} {dt.year}'
    except:
        return datetime.now().strftime('%d/%m/%Y')

# ══════════════════════════════════════════════════════════════
# 1. NOTICIAS
# ══════════════════════════════════════════════════════════════
def build_noticias():
    print('\nGenerando noticias.json...')
    result = {}
    for sport, urls in NEWS_FEEDS.items():
        print(f'  [{sport.upper()}]')
        raw_items = []
        for url in urls:
            data = fetch(url)
            if not data:
                continue
            try:
                root = ET.fromstring(data)
                for item in root.findall('.//item')[:8]:
                    title = item.findtext('title', '').strip()
                    link  = item.findtext('link',  '').strip()
                    pub   = item.findtext('pubDate', '').strip()
                    desc  = item.findtext('description', '')
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
                    image = img_match.group(1) if img_match else ''
                    title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                    if title and link:
                        raw_items.append({'title': title, 'url': link, 'date': format_date(pub), 'image': image})
            except Exception as e:
                print(f'    aviso parse: {e}')
            time.sleep(0.8)
        seen, unique = set(), []
        for item in raw_items:
            key = hashlib.md5(item['title'].lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        result[sport] = unique[:MAX_NEWS]
        print(f'    OK {len(result[sport])} noticias')
    return result

# ══════════════════════════════════════════════════════════════
# 2. VIDEOS
# ══════════════════════════════════════════════════════════════
def build_videos():
    print('\nGenerando videos.json...')
    result = {}
    for sport in ['bk', 'pd', 'fx']:
        print(f'  [{sport.upper()}]')
        all_videos = []
        channel_id = YT_CHANNELS.get(sport, '')
        if channel_id:
            url = (
                'https://www.googleapis.com/youtube/v3/search'
                f'?part=snippet&channelId={channel_id}'
                f'&maxResults=6&order=date&type=video&key={YT_API_KEY}'
            )
            data = fetch_json(url)
            if data and 'items' in data:
                for item in data['items']:
                    vid_id = item.get('id', {}).get('videoId', '')
                    snip   = item.get('snippet', {})
                    if not vid_id:
                        continue
                    all_videos.append({
                        'vid':   vid_id,
                        'title': snip.get('title', ''),
                        'thumb': snip.get('thumbnails', {}).get('medium', {}).get('url', f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg'),
                        'date':  snip.get('publishedAt', '')[:10],
                        'url':   f'https://www.youtube.com/watch?v={vid_id}',
                    })
                print(f'    OK {len(data["items"])} del canal oficial')
            time.sleep(1)
        for query in YT_QUERIES.get(sport, []):
            if len(all_videos) >= MAX_VIDEOS:
                break
            q = urllib.parse.quote(query)
            url = (
                'https://www.googleapis.com/youtube/v3/search'
                f'?part=snippet&q={q}'
                f'&maxResults=4&order=date&type=video&key={YT_API_KEY}'
            )
            data = fetch_json(url)
            if data and 'items' in data:
                for item in data['items']:
                    vid_id = item.get('id', {}).get('videoId', '')
                    snip   = item.get('snippet', {})
                    if not vid_id:
                        continue
                    all_videos.append({
                        'vid':   vid_id,
                        'title': snip.get('title', ''),
                        'thumb': snip.get('thumbnails', {}).get('medium', {}).get('url', f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg'),
                        'date':  snip.get('publishedAt', '')[:10],
                        'url':   f'https://www.youtube.com/watch?v={vid_id}',
                    })
            time.sleep(1)
        seen, unique = set(), []
        for v in all_videos:
            if v['vid'] not in seen:
                seen.add(v['vid'])
                unique.append(v)
        result[sport] = unique[:MAX_VIDEOS]
        print(f'    OK {len(result[sport])} videos')
    return result

# ══════════════════════════════════════════════════════════════
# 3. PARTIDOS
# ══════════════════════════════════════════════════════════════
def build_partidos():
    print('\nGenerando partidos.json...')
    result = {}

    print('  [BK] NBA...')
    data = fetch_json(ESPN_APIS['bk'])
    matches = []
    if data and 'events' in data:
        for ev in (data.get('events') or [])[:MAX_MATCHES]:
            try:
                comp  = ev['competitions'][0]
                home  = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away  = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                st    = ev['status']['type']
                is_live = st['state'] == 'in'
                is_post = st['state'] == 'post'
                score = f"{away.get('score','')}-{home.get('score','')}" if st['state'] != 'pre' else ''
                matches.append({
                    'fecha':  datetime.fromisoformat(ev['date'].replace('Z','+00:00')).strftime('%a %d %b'),
                    'local':  home['team']['abbreviation'],
                    'visita': away['team']['abbreviation'],
                    'score':  score,
                    'liga':   'NBA',
                    'estado': 'live' if is_live else ('post' if is_post else 'pre'),
                    'url':    'https://www.espn.com/nba/scoreboard',
                })
            except Exception as e:
                print(f'    aviso partido: {e}')
    result['bk'] = matches
    print(f'    OK {len(matches)} partidos NBA')

    time.sleep(1)
    print('  [FX] Liga MX...')
    data = fetch_json(ESPN_APIS['fx'])
    matches = []
    if data and 'events' in data:
        for ev in (data.get('events') or [])[:MAX_MATCHES]:
            try:
                comp  = ev['competitions'][0]
                home  = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away  = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                st    = ev['status']['type']
                is_live = st['state'] == 'in'
                is_post = st['state'] == 'post'
                score = f"{away.get('score','')}-{home.get('score','')}" if st['state'] != 'pre' else ''
                matches.append({
                    'fecha':  datetime.fromisoformat(ev['date'].replace('Z','+00:00')).strftime('%a %d %b'),
                    'local':  home['team'].get('shortDisplayName', home['team']['abbreviation']),
                    'visita': away['team'].get('shortDisplayName', away['team']['abbreviation']),
                    'score':  score,
                    'liga':   'Liga MX',
                    'estado': 'live' if is_live else ('post' if is_post else 'pre'),
                    'url':    'https://www.espn.com/soccer/scoreboard/_/league/mex.1',
                })
            except Exception as e:
                print(f'    aviso partido: {e}')
    result['fx'] = matches
    print(f'    OK {len(matches)} partidos Liga MX')

    result['pd'] = PADEL_CALENDAR
    print(f'    OK {len(PADEL_CALENDAR)} torneos Premier Padel')

    return result

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    ts = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    print(f'\n{"="*50}')
    print(f'  CourtKing Bot v4 — {ts}')
    print(f'{"="*50}')

    noticias = build_noticias()
    videos   = build_videos()
    partidos = build_partidos()

    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': noticias}, f, ensure_ascii=False, indent=2)
    with open('videos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': videos}, f, ensure_ascii=False, indent=2)
    with open('partidos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': partidos}, f, ensure_ascii=False, indent=2)

    print(f'\n{"="*50}')
    print(f'  OK noticias.json  -> {sum(len(v) for v in noticias.values())} noticias')
    print(f'  OK videos.json    -> {sum(len(v) for v in videos.values())} videos')
    print(f'  OK partidos.json  -> {sum(len(v) for v in partidos.values())} partidos')
    print(f'{"="*50}\n')

if __name__ == '__main__':
    main()
