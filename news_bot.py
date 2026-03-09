"""
CourtKing News Bot v12 — Múltiples ligas de fútbol
CAMBIOS vs v11:
- build_partidos_fx(): ahora carga Liga MX + LaLiga + Champions + Premier League
- ESPN_FX_LEAGUES: dict con todas las ligas y sus endpoints ESPN
- Marcador guardado como "local-visita" (consistente con HTML)
"""

import re, json, time, hashlib, urllib.request, urllib.parse, os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════
# CANALES YOUTUBE — YouTube Data API v3
# ══════════════════════════════════════════════════════════════
YT_API_KEY = os.environ.get('YT_API_KEY', 'AIzaSyABQSy5j3HOeFVFxijwZUw5SNFNyLbdAIw')

YT_CHANNELS = {
    'bk': [
        'UCWJ2lWNubArHWmf3FIHbfcQ',  # NBA official
        'UCzNQbFGNDFBIBPMI68bFZkQ',  # House of Highlights
        'UCEjOSbbaOfgnfRODEEMYlCw',  # Bleacher Report
    ],
    'pd': [
        'UCaJRfYmUhhBjt0VbVuJoNxw',  # Premier Padel FIP
        'UCK59dYVs3Wgwoe73nDTH6jw',  # World Padel Tour
        'UCXv4OKDlA2PEzpFGwT8_hSA',  # Padel Addict
    ],
    'fx': [
        'UCTv-XvfzLX3i4IGWAm4sbmA',  # LaLiga oficial
        'UCyGa1YEx9ST66rYrJTGIKOw',  # UEFA Champions League
        'UCq8BPLXtFeiSFOvmJrknWGg',  # Liga BBVA MX
        'UCTIyEyDNHPrwVFPhpi5dm0A',  # TUDN
    ],
}

NEWS_FEEDS = {
    'bk': [
        'https://news.google.com/rss/search?q=NBA+basquetbol+hoy+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+jugadas+destacadas+semana&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=basquetbol+NBA+noticias+hoy&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+2026+clasificacion+equipos&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=basquetbol+NBA+lesion+traspaso&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://www.espn.com/espn/rss/nba/news',
        'https://news.google.com/rss/search?q=NBA+site:espndeportes.espn.com&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+site:record.com.mx&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'pd': [
        'https://news.google.com/rss/search?q=Premier+Padel+2026+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+torneo+ranking+jugadores&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+Mexico+Cancun+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Coello+Tapia+Di+Nenno+padel&hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/search?q=Triay+Jensen+padel+femenino&hl=es&gl=ES&ceid=ES:es',
        'https://www.padelmundo.com/feed/',
        'https://news.google.com/rss/search?q=padel+site:marca.com&hl=es&gl=ES&ceid=ES:es',
    ],
    'fx': [
        'https://news.google.com/rss/search?q=Liga+MX+jornada+goles+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Liga+MX+Clausura+2026+noticias&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=futbol+mexicano+Chivas+America+Cruz+Azul&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=seleccion+mexicana+futbol+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Champions+League+2026+resultados+goles&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=LaLiga+2026+resultados+jornada&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Premier+League+2026+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://www.espn.com/espn/rss/soccer/news',
        'https://www.record.com.mx/rss/futbol-mexicano',
        'https://news.google.com/rss/search?q=futbol+site:tudn.com&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
}

ESPN_NBA             = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
ESPN_NBA_STANDINGS   = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
ESPN_NBA_LEADERS     = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/leaders'
ESPN_FX_STANDINGS    = 'https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings'

# ── Ligas de fútbol — endpoint ESPN + nombre para mostrar ──
ESPN_FX_LEAGUES = {
    'Liga MX':        'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?limit=10',
    'LaLiga':         'https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard?limit=8',
    'Champions':      'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard?limit=8',
    'Premier League': 'https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?limit=8',
    'Ligue 1':        'https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard?limit=6',
    'Serie A':        'https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard?limit=6',
}

FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY', '')
FOOTBALL_DATA_MX  = 'https://api.football-data.org/v4/competitions/MX1/matches?status=LIVE,IN_PLAY,PAUSED,FINISHED,SCHEDULED&limit=12'
API_FOOTBALL_KEY  = os.environ.get('API_FOOTBALL_KEY', '')

UNSPLASH_KEY = os.environ.get('UNSPLASH_KEY', '')

PADEL_CALENDAR = [
    {'fecha': '1-8 Mar 2026',   'torneo': 'Gijón P2',     'liga': 'Premier Padel — España',   'url': 'https://www.padelfip.com/es/evento/gijon-p2-2026/',                      'live': True},
    {'fecha': '16-22 Mar 2026', 'torneo': 'Cancún P2',    'liga': 'Premier Padel — México',   'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': '23-29 Mar 2026', 'torneo': 'Miami P1',     'liga': 'Premier Padel — EUA',      'url': 'https://www.miamipremierpadel.com/',                                     'live': False},
    {'fecha': '6-11 Abr 2026',  'torneo': 'Qatar Major',  'liga': 'Premier Padel — Doha',     'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'May 2026',       'torneo': 'Madrid Major', 'liga': 'Premier Padel — España',   'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'Jun 2026',       'torneo': 'París P1',     'liga': 'Premier Padel — Francia',  'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'Nov 2026',       'torneo': 'Mexico Major', 'liga': 'Premier Padel — Acapulco', 'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
]

MAX_NEWS    = 20
MAX_VIDEOS  = 8
MAX_MATCHES = 10

SPORT_FALLBACK_IMGS = {
    'bk': [
        'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=480&q=70',
        'https://images.unsplash.com/photo-1504450758481-7338eba7524a?w=480&q=70',
        'https://images.unsplash.com/photo-1577471488278-16eec37ffcc2?w=480&q=70',
        'https://images.unsplash.com/photo-1574623452334-1e0ac2b3ccb4?w=480&q=70',
        'https://images.unsplash.com/photo-1519861531473-9200262188bf?w=480&q=70',
        'https://images.unsplash.com/photo-1608245449230-4ac19066d2d0?w=480&q=70',
    ],
    'pd': [
        'https://images.unsplash.com/photo-1554068865-24cecd4e34b8?w=480&q=70',
        'https://images.unsplash.com/photo-1612872087720-bb876e2e67d1?w=480&q=70',
        'https://images.unsplash.com/photo-1587280501635-68a0e82cd5ff?w=480&q=70',
        'https://images.unsplash.com/photo-1560012057-4372e14c5085?w=480&q=70',
        'https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=480&q=70',
        'https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=480&q=70',
    ],
    'fx': [
        'https://images.unsplash.com/photo-1575361204480-aadea25e6e68?w=480&q=70',
        'https://images.unsplash.com/photo-1553778263-73a83bab9b0c?w=480&q=70',
        'https://images.unsplash.com/photo-1606925797300-0b35e9d1794e?w=480&q=70',
        'https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=480&q=70',
        'https://images.unsplash.com/photo-1560272564-c83b66b1ad12?w=480&q=70',
        'https://images.unsplash.com/photo-1517927033932-b3d18e61fb3a?w=480&q=70',
    ],
}

SPORT_BASE_QUERY = {
    'bk': 'basketball NBA',
    'pd': 'padel tennis sport',
    'fx': 'soccer football Mexico',
}

_unsplash_cache = {}

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fetch(url, timeout=15, headers=None):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (compatible; CourtkingBot/12.0)'}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f'    aviso fetch: {e}')
        return None

def fetch_json(url, headers=None):
    data = fetch(url, headers=headers)
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

def parse_pub_date(pub_str):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except:
        return None

def build_unsplash_query(title, sport):
    stopwords = {
        'de','la','el','los','las','en','con','por','para','del','al',
        'una','un','que','se','su','sus','como','más','pero','esto','este',
        'esta','son','fue','era','han','hay','muy','ya','si','no','le','les',
        'lo','y','a','e','o','u','vs','vs.','gana','ganan','pierde',
    }
    clean = re.sub(r'[^a-zA-ZáéíóúñüÁÉÍÓÚÑÜ\s]', ' ', title.lower())
    words = [w for w in clean.split() if len(w) > 3 and w not in stopwords]
    keywords = words[:3]
    base = SPORT_BASE_QUERY.get(sport, 'sport')
    query = ' '.join(keywords) + ' ' + base if keywords else base
    return query.strip()

def fetch_unsplash_image(title, sport, orientation='landscape'):
    if not UNSPLASH_KEY:
        return ''
    query = build_unsplash_query(title, sport)
    cache_key = query.lower()
    if cache_key in _unsplash_cache:
        return _unsplash_cache[cache_key]
    try:
        params = urllib.parse.urlencode({
            'query':       query,
            'per_page':    5,
            'orientation': orientation,
            'content_filter': 'high',
        })
        url = f'https://api.unsplash.com/search/photos?{params}'
        data = fetch_json(url, headers={
            'Authorization': f'Client-ID {UNSPLASH_KEY}',
            'Accept-Version': 'v1',
        })
        if data and data.get('results'):
            idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % min(5, len(data['results']))
            photo = data['results'][idx]
            img_url = photo['urls'].get('regular', photo['urls'].get('small', ''))
            if img_url and '?' in img_url:
                img_url = re.sub(r'w=\d+', 'w=600', img_url)
            elif img_url:
                img_url += '&w=600'
            _unsplash_cache[cache_key] = img_url
            return img_url
    except Exception as e:
        print(f'    aviso Unsplash: {e}')
    _unsplash_cache[cache_key] = ''
    return ''

IMG_BLOCKED = [
    'googleusercontent.com/news', 'google.com/news', 'gstatic.com',
    'placeholder', 'default', 'logo', 'icon', 'favicon',
    'lh3.googleusercontent', 'encrypted-tbn',
]

def is_valid_img(url):
    if not url or not url.startswith('http'):
        return False
    return not any(b in url.lower() for b in IMG_BLOCKED)

def resolve_google_news_url(url, timeout=5):
    if 'news.google.com' not in url:
        return url
    try:
        import http.client
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout)
        conn.request('HEAD', parsed.path + ('?' + parsed.query if parsed.query else ''))
        resp = conn.getresponse()
        if resp.status in (301, 302, 303, 307, 308):
            location = resp.getheader('Location', '')
            if location and location.startswith('http'):
                return location
        conn.close()
    except:
        pass
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.url
    except:
        pass
    return url

def fetch_og_image(url, timeout=6):
    try:
        real_url = resolve_google_news_url(url, timeout=4)
        data = fetch(real_url, timeout=timeout)
        if not data:
            return ''
        html = data.decode('utf-8', errors='ignore')
        m = re.search(r'property="og:image"[^>]+content="([^"]+)"', html)
        if not m:
            m = re.search(r'content="([^"]+)"[^>]+property="og:image"', html)
        if not m:
            m = re.search(r"name='og:image'[^>]+content='([^']+)'", html)
        if not m:
            m = re.search(r'name="twitter:image"[^>]+content="([^"]+)"', html)
        if m:
            img = m.group(1).strip()
            if is_valid_img(img):
                return img
    except:
        pass
    return ''

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
                    img_match = re.search(r'<img[^>]+src=[\"\'](https?://[^\"\']+)[\"\']', desc)
                    raw_img = img_match.group(1) if img_match else ''
                    image = raw_img if is_valid_img(raw_img) else ''
                    title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                    if title and link:
                        raw_items.append({
                            'title': title, 'url': link,
                            'date': format_date(pub), 'image': image,
                            '_pub_raw': pub,
                        })
            except Exception as e:
                print(f'    aviso parse: {e}')
            time.sleep(0.4)

        seen, unique = set(), []
        for item in raw_items:
            key = hashlib.md5(item['title'].lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(item)

        now_utc = datetime.utcnow()
        filtered = []
        for item in unique:
            pub_dt = parse_pub_date(item.get('_pub_raw', ''))
            if pub_dt is None or (now_utc - pub_dt).total_seconds() <= 48 * 3600:
                filtered.append(item)
        if len(filtered) < 4:
            filtered = []
            for item in unique:
                pub_dt = parse_pub_date(item.get('_pub_raw', ''))
                if pub_dt is None or (now_utc - pub_dt).total_seconds() <= 7 * 24 * 3600:
                    filtered.append(item)
        unique = filtered

        fallbacks   = SPORT_FALLBACK_IMGS.get(sport, SPORT_FALLBACK_IMGS['bk'])
        og_count    = 0
        uns_count   = 0
        fallb_count = 0

        for i, item in enumerate(unique[:MAX_NEWS]):
            if item.get('image'):
                continue
            if og_count < 6:
                og_img = fetch_og_image(item['url'])
                time.sleep(0.25)
                if og_img:
                    item['image'] = og_img
                    og_count += 1
                    continue
            if UNSPLASH_KEY and uns_count < 15:
                uns_img = fetch_unsplash_image(item['title'], sport)
                time.sleep(0.2)
                if uns_img:
                    item['image'] = uns_img
                    uns_count += 1
                    continue
            item['image'] = fallbacks[i % len(fallbacks)]
            fallb_count += 1

        result[sport] = unique[:MAX_NEWS]
        print(f'    OK {len(result[sport])} noticias (og:{og_count} / unsplash:{uns_count} / fallback:{fallb_count})')
    return result

# ══════════════════════════════════════════════════════════════
# 2. VIDEOS
# ══════════════════════════════════════════════════════════════
def build_videos():
    print('\nGenerando videos.json...')
    result = {}
    for sport, channel_ids in YT_CHANNELS.items():
        print(f'  [{sport.upper()}]')
        all_videos = []
        for channel_id in channel_ids:
            api_ok = False
            if YT_API_KEY:
                try:
                    api_url = (
                        'https://www.googleapis.com/youtube/v3/search'
                        f'?part=snippet&channelId={channel_id}'
                        '&type=video&order=date&maxResults=5'
                        f'&key={YT_API_KEY}'
                    )
                    data = fetch_json(api_url)
                    if data and data.get('items'):
                        for item in data['items']:
                            vid_id = item.get('id', {}).get('videoId', '')
                            snip   = item.get('snippet', {})
                            title  = snip.get('title', '')
                            pub    = snip.get('publishedAt', '')[:10]
                            thumb  = (snip.get('thumbnails', {})
                                      .get('medium', {})
                                      .get('url', f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg'))
                            if vid_id and title:
                                all_videos.append({
                                    'vid': vid_id, 'title': title,
                                    'thumb': thumb, 'date': pub,
                                    'url': f'https://www.youtube.com/watch?v={vid_id}',
                                })
                        api_ok = True
                except Exception as e:
                    print(f'    API aviso {channel_id[:12]}: {e}')

            if not api_ok:
                rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
                data = fetch(rss_url)
                if data:
                    try:
                        ns = {
                            'atom':  'http://www.w3.org/2005/Atom',
                            'yt':    'http://www.youtube.com/xml/schemas/2015',
                            'media': 'http://search.yahoo.com/mrss/',
                        }
                        root = ET.fromstring(data)
                        for entry in root.findall('atom:entry', ns)[:5]:
                            vid_id = entry.findtext('yt:videoId', '', ns)
                            title  = entry.findtext('atom:title', '', ns)
                            pub    = entry.findtext('atom:published', '', ns)
                            thumb  = f'https://img.youtube.com/vi/{vid_id}/mqdefault.jpg'
                            mg = entry.find('media:group', ns)
                            if mg is not None:
                                mt = mg.find('media:thumbnail', ns)
                                if mt is not None:
                                    thumb = mt.get('url', thumb)
                            if vid_id and title:
                                all_videos.append({
                                    'vid': vid_id, 'title': title,
                                    'thumb': thumb, 'date': pub[:10] if pub else '',
                                    'url': f'https://www.youtube.com/watch?v={vid_id}',
                                })
                    except Exception as e:
                        print(f'    RSS aviso: {e}')
            time.sleep(0.3)

        seen, unique = set(), []
        for v in all_videos:
            if v['vid'] not in seen:
                seen.add(v['vid'])
                unique.append(v)
        result[sport] = unique[:MAX_VIDEOS]
    return result

# ══════════════════════════════════════════════════════════════
# 3. TABLA POSICIONES NBA
# ══════════════════════════════════════════════════════════════
def build_standings_nba():
    print('\n  [BK] Tabla posiciones NBA...')
    data = fetch_json(ESPN_NBA_STANDINGS)
    standings = {'east': [], 'west': []}
    if not data:
        return standings
    try:
        for conf in data.get('children', []):
            conf_name = conf.get('name', '').lower()
            key = 'east' if 'east' in conf_name else 'west'
            for entry in conf.get('standings', {}).get('entries', [])[:8]:
                team  = entry.get('team', {})
                stats = {s['name']: s.get('displayValue','') for s in entry.get('stats', [])}
                pos_idx = len(standings[key]) + 1
                standings[key].append({
                    'pos':  entry.get('rank', pos_idx) or pos_idx,
                    'team': team.get('abbreviation', team.get('displayName','')),
                    'name': team.get('shortDisplayName', team.get('displayName','')),
                    'w':    stats.get('wins', ''),
                    'l':    stats.get('losses', ''),
                    'pct':  stats.get('winPercent', ''),
                    'gb':   stats.get('gamesBehind', ''),
                })
    except Exception as e:
        print(f'    aviso: {e}')
    return standings

# ══════════════════════════════════════════════════════════════
# 4. LÍDERES NBA
# ══════════════════════════════════════════════════════════════
def build_leaders_nba():
    print('  [BK] Líderes NBA...')
    leaders = {'pts': [], 'reb': [], 'ast': []}
    data = fetch_json(ESPN_NBA_LEADERS)
    if data:
        try:
            cats = data.get('categories', [])
            if not cats:
                for sport in data.get('sports', []):
                    for league in sport.get('leagues', []):
                        cats = league.get('leaders', [])
                        if cats: break
            for cat in cats:
                cat_name = (cat.get('name', '') or cat.get('displayName', '')).lower()
                key = None
                if any(x in cat_name for x in ['point','pts','scoring']): key = 'pts'
                elif any(x in cat_name for x in ['rebound','reb']): key = 'reb'
                elif any(x in cat_name for x in ['assist','ast']): key = 'ast'
                if not key:
                    continue
                items = cat.get('leaders', cat.get('athletes', cat.get('items', [])))
                for i, leader in enumerate(items[:5]):
                    athlete = leader.get('athlete', leader.get('player', {}))
                    team    = leader.get('team', {})
                    leaders[key].append({
                        'pos':   i + 1,
                        'name':  athlete.get('shortName', athlete.get('displayName', '')),
                        'team':  team.get('abbreviation', team.get('shortName', '')),
                        'value': str(leader.get('displayValue', leader.get('value', ''))),
                    })
        except Exception as e:
            print(f'    aviso: {e}')
    # Fallbacks hardcoded si falla ESPN
    if not leaders['pts']:
        leaders['pts'] = [
            {'pos':1,'name':'S. Gilgeous-Alexander','team':'OKC','value':'32.3'},
            {'pos':2,'name':'G. Antetokounmpo','team':'MIL','value':'30.4'},
            {'pos':3,'name':'N. Jokic','team':'DEN','value':'29.6'},
            {'pos':4,'name':'L. Doncic','team':'DAL','value':'28.1'},
            {'pos':5,'name':'D. Mitchell','team':'CLE','value':'26.8'},
        ]
    if not leaders['reb']:
        leaders['reb'] = [
            {'pos':1,'name':'N. Jokic','team':'DEN','value':'13.1'},
            {'pos':2,'name':'G. Antetokounmpo','team':'MIL','value':'12.2'},
            {'pos':3,'name':'A. Davis','team':'LAL','value':'12.0'},
            {'pos':4,'name':'D. Ayton','team':'POR','value':'11.4'},
            {'pos':5,'name':'J. Embiid','team':'PHI','value':'10.9'},
        ]
    if not leaders['ast']:
        leaders['ast'] = [
            {'pos':1,'name':'T. Haliburton','team':'IND','value':'9.4'},
            {'pos':2,'name':'L. Doncic','team':'DAL','value':'8.9'},
            {'pos':3,'name':'J. Brunson','team':'NYK','value':'7.7'},
            {'pos':4,'name':'S. Gilgeous-Alexander','team':'OKC','value':'6.4'},
            {'pos':5,'name':'D. Fox','team':'SAC','value':'6.1'},
        ]
    return leaders

# ══════════════════════════════════════════════════════════════
# 5. TABLA POSICIONES LIGA MX
# ══════════════════════════════════════════════════════════════
def build_standings_fx():
    print('  [FX] Tabla posiciones Liga MX...')
    data = fetch_json(ESPN_FX_STANDINGS)
    standings = []
    if not data:
        return standings
    try:
        entries = []
        for src in [data] + data.get('children', []):
            e = src.get('standings', {}).get('entries', [])
            if e:
                entries = e
                break
        for entry in entries[:18]:
            team  = entry.get('team', {})
            stats = {s['name']: s.get('displayValue', s.get('value','')) for s in entry.get('stats', [])}
            pos_fx = entry.get('rank', len(standings)+1) or len(standings)+1
            standings.append({
                'pos':  pos_fx,
                'team': team.get('abbreviation', team.get('displayName','')),
                'name': team.get('shortDisplayName', team.get('displayName','')),
                'pj':   stats.get('gamesPlayed', ''),
                'g':    stats.get('wins', ''),
                'e':    stats.get('ties', ''),
                'p':    stats.get('losses', ''),
                'gf':   stats.get('pointsFor', stats.get('goalsFor','')),
                'gc':   stats.get('pointsAgainst', stats.get('goalsAgainst','')),
                'pts':  stats.get('points', ''),
            })
    except Exception as e:
        print(f'    aviso: {e}')
    # Fallback hardcoded J10 Clausura 2026 si ESPN falla
    if not standings:
        standings = [
            {'pos':1,  'team':'CRU', 'name':'Cruz Azul',    'pj':10,'g':8,'e':1,'p':1,'gf':20,'gc':9, 'pts':25},
            {'pos':2,  'team':'TOL', 'name':'Toluca',        'pj':10,'g':7,'e':3,'p':0,'gf':17,'gc':5, 'pts':24},
            {'pos':3,  'team':'GDL', 'name':'Guadalajara',   'pj':9, 'g':7,'e':0,'p':2,'gf':14,'gc':9, 'pts':21},
            {'pos':4,  'team':'PAC', 'name':'Pachuca',       'pj':10,'g':6,'e':2,'p':2,'gf':13,'gc':8, 'pts':20},
            {'pos':5,  'team':'PUM', 'name':'Pumas',         'pj':10,'g':5,'e':4,'p':1,'gf':18,'gc':10,'pts':19},
            {'pos':6,  'team':'TIG', 'name':'Tigres',        'pj':10,'g':5,'e':1,'p':4,'gf':17,'gc':12,'pts':16},
            {'pos':7,  'team':'ATL', 'name':'Atlas',         'pj':10,'g':4,'e':4,'p':2,'gf':12,'gc':10,'pts':16},
            {'pos':8,  'team':'AME', 'name':'América',       'pj':10,'g':4,'e':2,'p':4,'gf':13,'gc':14,'pts':14},
            {'pos':9,  'team':'MTY', 'name':'Monterrey',     'pj':10,'g':4,'e':1,'p':5,'gf':12,'gc':13,'pts':13},
            {'pos':10, 'team':'PUE', 'name':'Puebla',        'pj':10,'g':3,'e':3,'p':4,'gf':10,'gc':13,'pts':12},
            {'pos':11, 'team':'SLU', 'name':'Atl. San Luis', 'pj':10,'g':3,'e':2,'p':5,'gf':12,'gc':18,'pts':11},
            {'pos':12, 'team':'JUA', 'name':'FC Juárez',     'pj':10,'g':3,'e':2,'p':5,'gf':9, 'gc':14,'pts':11},
            {'pos':13, 'team':'LEO', 'name':'León',          'pj':10,'g':3,'e':1,'p':6,'gf':11,'gc':18,'pts':10},
            {'pos':14, 'team':'MAZ', 'name':'Mazatlán',      'pj':10,'g':3,'e':1,'p':6,'gf':14,'gc':19,'pts':10},
            {'pos':15, 'team':'NEC', 'name':'Necaxa',        'pj':10,'g':2,'e':3,'p':5,'gf':8, 'gc':13,'pts':9},
            {'pos':16, 'team':'TIJ', 'name':'Tijuana',       'pj':10,'g':2,'e':2,'p':6,'gf':8, 'gc':17,'pts':8},
            {'pos':17, 'team':'QRO', 'name':'Querétaro',     'pj':10,'g':1,'e':3,'p':6,'gf':7, 'gc':18,'pts':6},
            {'pos':18, 'team':'SAN', 'name':'Santos',        'pj':10,'g':1,'e':2,'p':7,'gf':6, 'gc':18,'pts':5},
        ]
        print('    Usando fallback hardcoded J10')
    return standings

# ══════════════════════════════════════════════════════════════
# 6. GOLEADORES LIGA MX  ⚠️ ACTUALIZAR cada domingo
# ══════════════════════════════════════════════════════════════
def build_leaders_fx():
    print('  [FX] Goleadores Liga MX...')
    # ⚠️ ACTUALIZADO J10 Clausura 2026 — 9 mar 2026
    leaders = [
        {'pos':1,  'name':'Joao Pedro',          'team':'Atl. San Luis', 'goles': 9},
        {'pos':2,  'name':'Armando González',    'team':'Chivas',        'goles': 6},
        {'pos':3,  'name':'Paulinho',            'team':'Toluca',        'goles': 6},
        {'pos':4,  'name':'José Paradela',       'team':'Cruz Azul',     'goles': 5},
        {'pos':5,  'name':'Arturo González',     'team':'Atlas',         'goles': 5},
        {'pos':6,  'name':'Diber Cambindo',      'team':'León',          'goles': 5},
        {'pos':7,  'name':'A. Palavecino',       'team':'Cruz Azul',     'goles': 4},
        {'pos':8,  'name':'G. Fernández',        'team':'Cruz Azul',     'goles': 4},
        {'pos':9,  'name':'Salomón Rondón',      'team':'Pachuca',       'goles': 4},
        {'pos':10, 'name':'Juninho',             'team':'Pumas',         'goles': 4},
        {'pos':11, 'name':'L. Di Yorio',         'team':'Santos',        'goles': 4},
        {'pos':12, 'name':'Oussama Idrissi',     'team':'Pachuca',       'goles': 3},
        {'pos':13, 'name':'Robert Morales',      'team':'Pumas',         'goles': 3},
        {'pos':14, 'name':'Álvaro Angulo',       'team':'Pumas',         'goles': 3},
        {'pos':15, 'name':'Marcelo Flores',      'team':'Tigres',        'goles': 3},
    ]
    return leaders

# ══════════════════════════════════════════════════════════════
# 7. RANKING PÁDEL
# ══════════════════════════════════════════════════════════════
def build_ranking_padel():
    print('  [PD] Ranking Mundial Pádel...')
    ranking = {'men': [], 'women': []}
    if not ranking['men']:
        ranking['men'] = [
            {'pos':1,'name':'Arturo Coello','country':'ESP','pts':''},
            {'pos':2,'name':'Martín Di Nenno','country':'ARG','pts':''},
            {'pos':3,'name':'Agustín Tapia','country':'ARG','pts':''},
            {'pos':4,'name':'Federico Chingotto','country':'ARG','pts':''},
            {'pos':5,'name':'Juan Lebrón','country':'ESP','pts':''},
            {'pos':6,'name':'Pablo Lima','country':'BRA','pts':''},
            {'pos':7,'name':'Ale Galán','country':'ESP','pts':''},
            {'pos':8,'name':'Jon Sanz','country':'ESP','pts':''},
            {'pos':9,'name':'Fede Stupaczuk','country':'ARG','pts':''},
            {'pos':10,'name':'Álex Ruiz','country':'ESP','pts':''},
        ]
    if not ranking['women']:
        ranking['women'] = [
            {'pos':1,'name':'Gemma Triay','country':'ESP','pts':''},
            {'pos':2,'name':'Claudia Jensen','country':'ESP','pts':''},
            {'pos':3,'name':'Ariana Sánchez','country':'ESP','pts':''},
            {'pos':4,'name':'Marta Ortega','country':'ESP','pts':''},
            {'pos':5,'name':'Paula Josemaría','country':'ESP','pts':''},
            {'pos':6,'name':'Tamara Icardo','country':'ESP','pts':''},
            {'pos':7,'name':'Delfi Brea','country':'ARG','pts':''},
            {'pos':8,'name':'Bea González','country':'ESP','pts':''},
            {'pos':9,'name':'Martina Capra','country':'ARG','pts':''},
            {'pos':10,'name':'Lucía Sainz','country':'ESP','pts':''},
        ]
    return ranking

# ══════════════════════════════════════════════════════════════
# 8. PARTIDOS — NBA + MÚLTIPLES LIGAS FÚTBOL
# ══════════════════════════════════════════════════════════════
def _espn_events_to_matches(events, liga, url_liga):
    """Convierte eventos ESPN a formato estándar. Score = local-visita."""
    matches = []
    for ev in (events or [])[:MAX_MATCHES]:
        try:
            comp  = ev['competitions'][0]
            home  = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
            away  = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
            st    = ev['status']['type']
            # Score: primero local, luego visita
            score = f"{home.get('score','')}-{away.get('score','')}" if st['state'] != 'pre' else ''
            matches.append({
                'fecha':  datetime.fromisoformat(ev['date'].replace('Z','+00:00')).strftime('%a %d %b'),
                'local':  home['team'].get('shortDisplayName', home['team']['abbreviation']),
                'visita': away['team'].get('shortDisplayName', away['team']['abbreviation']),
                'score':  score,
                'liga':   liga,
                'estado': 'live' if st['state']=='in' else ('post' if st['state']=='post' else 'pre'),
                'url':    url_liga,
            })
        except Exception as e:
            print(f'    aviso evento: {e}')
    return matches

def build_partidos():
    print('\nGenerando partidos.json...')
    result = {}

    # ── NBA ──
    print('  [BK] NBA...')
    data = fetch_json(ESPN_NBA)
    bk_matches = []
    if data and 'events' in data:
        bk_matches = _espn_events_to_matches(
            data.get('events', []),
            'NBA',
            'https://www.espn.com/nba/scoreboard'
        )
    result['bk'] = bk_matches
    print(f'    OK {len(bk_matches)} partidos NBA')

    time.sleep(1)

    # ── FÚTBOL — múltiples ligas ──
    print('  [FX] Múltiples ligas fútbol...')
    fx_matches = []

    for liga_name, liga_url in ESPN_FX_LEAGUES.items():
        try:
            data = fetch_json(liga_url)
            if data and 'events' in data:
                liga_matches = _espn_events_to_matches(
                    data.get('events', []),
                    liga_name,
                    liga_url.replace('/scoreboard', '').replace('?limit=10', '').replace('?limit=8', '').replace('?limit=6', '')
                )
                fx_matches.extend(liga_matches)
                print(f'    {liga_name}: {len(liga_matches)} partidos')
            time.sleep(0.5)
        except Exception as e:
            print(f'    aviso {liga_name}: {e}')

    # Si el bot de football-data.org está configurado, usar para Liga MX (más confiable)
    if FOOTBALL_DATA_KEY:
        try:
            req = urllib.request.Request(FOOTBALL_DATA_MX, headers={'X-Auth-Token': FOOTBALL_DATA_KEY})
            with urllib.request.urlopen(req, timeout=10) as resp:
                fd_data = json.loads(resp.read())
            mx_fd = []
            for m in (fd_data.get('matches') or [])[:MAX_MATCHES]:
                sh = (m.get('score',{}).get('fullTime',{}) or {}).get('home')
                sa = (m.get('score',{}).get('fullTime',{}) or {}).get('away')
                if sh is None:
                    sh = (m.get('score',{}).get('halfTime',{}) or {}).get('home')
                    sa = (m.get('score',{}).get('halfTime',{}) or {}).get('away')
                status    = m.get('status','')
                fecha_str = m.get('utcDate','')[:10]
                try:
                    fecha_str = datetime.fromisoformat(fecha_str).strftime('%a %d %b')
                except: pass
                mx_fd.append({
                    'fecha':  fecha_str,
                    'local':  m.get('homeTeam',{}).get('shortName', m.get('homeTeam',{}).get('name','')),
                    'visita': m.get('awayTeam',{}).get('shortName', m.get('awayTeam',{}).get('name','')),
                    'score':  f"{sh}-{sa}" if sh is not None else '',
                    'liga':   'Liga MX',
                    'estado': 'live' if status in ('IN_PLAY','PAUSED') else ('post' if status=='FINISHED' else 'pre'),
                    'url':    'https://www.ligabbvamx.mx/',
                })
            # Reemplazar Liga MX del ESPN con los datos de football-data (más precisos)
            fx_matches = [m for m in fx_matches if m.get('liga') != 'Liga MX']
            fx_matches = mx_fd + fx_matches
            print(f'    Liga MX (football-data): {len(mx_fd)} partidos ✅')
        except Exception as e:
            print(f'    football-data falló: {e} — usando ESPN')

    result['fx'] = fx_matches
    result['pd'] = PADEL_CALENDAR

    total_fx = len(fx_matches)
    print(f'    TOTAL fútbol: {total_fx} partidos ({len(ESPN_FX_LEAGUES)} ligas)')
    return result

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    ts   = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    mode = os.environ.get('MODE', 'full')

    print(f'\n{"="*55}')
    print(f'  CourtKing Bot v12 — {ts}  [MODE={mode}]')
    print(f'  FOOTBALL_DATA_KEY: {"✅" if FOOTBALL_DATA_KEY else "❌"}')
    print(f'  UNSPLASH_KEY:      {"✅" if UNSPLASH_KEY else "❌"}')
    print(f'{"="*55}')

    if mode == 'partidos':
        partidos = build_partidos()
        with open('partidos.json', 'w', encoding='utf-8') as f:
            json.dump({'updated': ts, 'sports': partidos}, f, ensure_ascii=False, indent=2)
        total_p = sum(len(v) for v in partidos.values())
        print(f'\n✅ partidos.json → {total_p} partidos\n')
        return

    noticias  = build_noticias()
    videos    = build_videos()
    partidos  = build_partidos()

    print('\nGenerando tablas...')
    standings_nba = build_standings_nba()
    leaders_nba   = build_leaders_nba()
    standings_fx  = build_standings_fx()
    leaders_fx    = build_leaders_fx()
    ranking_padel = build_ranking_padel()

    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': noticias}, f, ensure_ascii=False, indent=2)
    with open('videos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': videos}, f, ensure_ascii=False, indent=2)
    with open('partidos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': partidos}, f, ensure_ascii=False, indent=2)
    with open('tablas.json', 'w', encoding='utf-8') as f:
        json.dump({
            'updated': ts,
            'nba': {'standings': standings_nba, 'leaders': leaders_nba},
            'fx':  {'standings': standings_fx,  'leaders': leaders_fx},
            'pd':  {'ranking':   ranking_padel},
        }, f, ensure_ascii=False, indent=2)

    total_n = sum(len(v) for v in noticias.values())
    total_v = sum(len(v) for v in videos.values())
    total_p = sum(len(v) for v in partidos.values())
    print(f'\n{"="*55}')
    print(f'  ✅ noticias.json  → {total_n} noticias')
    print(f'  ✅ videos.json    → {total_v} videos')
    print(f'  ✅ partidos.json  → {total_p} partidos')
    print(f'  ✅ tablas.json    → NBA + Liga MX + Padel')
    print(f'{"="*55}\n')

if __name__ == '__main__':
    main()
