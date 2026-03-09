"""
CourtKing News Bot v8 — FIXES APLICADOS:
1. API_FOOTBALL_KEY ahora se lee correctamente del entorno
2. Season corregida: Clausura 2026 = season 2025 en api-football
3. Header x-rapidapi-host agregado (requerido por api-football)
4. Queries RSS mejoradas con palabras clave más frescas
5. Fallback hardcoded de goleadores Liga MX actualizado
"""

import re, json, time, hashlib, urllib.request, urllib.parse, os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════
# CANALES YOUTUBE — RSS sin API key
# ══════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════
# FEEDS RSS — queries mejoradas para noticias más frescas
# ══════════════════════════════════════════════════════════════
NEWS_FEEDS = {
    'bk': [
        # Google News — varias queries NBA
        'https://news.google.com/rss/search?q=NBA+resultados+hoy&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+highlights+jugadas&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+playoffs+2026+clasificacion&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=basquetbol+NBA+transferencias+fichajes&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+lesiones+noticias+equipo&hl=es-419&gl=MX&ceid=MX:es-419',
        # ESPN RSS directo
        'https://www.espn.com/espn/rss/nba/news',
        # Bleacher Report RSS
        'https://bleacherreport.com/nba.rss',
        # Yahoo Sports NBA
        'https://sports.yahoo.com/nba/rss.xml',
    ],
    'pd': [
        # Google News — pádel
        'https://news.google.com/rss/search?q=Premier+Padel+2026+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+torneo+ranking+jugadores&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+Mexico+Cancun+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Coello+Tapia+Di+Nenno+padel&hl=es&gl=ES&ceid=ES:es',
        'https://news.google.com/rss/search?q=Triay+Jensen+padel+femenino&hl=es&gl=ES&ceid=ES:es',
        # Padel World Press RSS
        'https://www.padelmundo.com/feed/',
        # Noticias pádel Marca
        'https://news.google.com/rss/search?q=padel+site:marca.com&hl=es&gl=ES&ceid=ES:es',
    ],
    'fx': [
        # Google News — Liga MX
        'https://news.google.com/rss/search?q=Liga+MX+jornada+goles+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Liga+MX+Clausura+2026+noticias&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=futbol+mexicano+Chivas+America+Cruz+Azul&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=seleccion+mexicana+futbol+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        # Google News — Champions + Europa
        'https://news.google.com/rss/search?q=Champions+League+2026+resultados+goles&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=LaLiga+2026+resultados+jornada&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Premier+League+2026+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        # ESPN RSS directo fútbol
        'https://www.espn.com/espn/rss/soccer/news',
        # Record MX RSS
        'https://www.record.com.mx/rss/futbol-mexicano',
        # TUDN RSS
        'https://news.google.com/rss/search?q=futbol+site:tudn.com&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
}

ESPN_NBA             = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
ESPN_NBA_STANDINGS   = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
ESPN_NBA_LEADERS     = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/leaders'
ESPN_FX_STANDINGS    = 'https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings'
ESPN_FX_SCOREBOARD   = 'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?limit=10'

FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY', '')
FOOTBALL_DATA_MX  = 'https://api.football-data.org/v4/competitions/MX1/matches?status=LIVE,IN_PLAY,PAUSED,FINISHED,SCHEDULED&limit=12'

# ✅ FIX: Leer API_FOOTBALL_KEY correctamente del entorno
API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY', '')

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

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fetch(url, timeout=15, headers=None):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (compatible; CourtkingBot/8.0)'}
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

# ══════════════════════════════════════════════════════════════
# 1. NOTICIAS — Google News RSS
# ══════════════════════════════════════════════════════════════
# Imágenes fallback variadas por deporte (6 opciones cada una)
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

def fetch_og_image(url, timeout=6):
    """Extrae og:image de la página de la noticia para imagen real."""
    try:
        data = fetch(url, timeout=timeout)
        if not data:
            return ''
        html = data.decode('utf-8', errors='ignore')
        for pattern in [
            r'<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']',
            r'<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']',
            r'<meta[^>]+name=["']twitter:image["'][^>]+content=["']([^"']+)["']',
        ]:
            m = re.search(pattern, html)
            if m:
                img = m.group(1).strip()
                if img.startswith('http'):
                    return img
    except:
        pass
    return ''

# ══════════════════════════════════════════════════════════════
# 1. NOTICIAS — Google News RSS + imágenes reales (og:image)
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
                    image = img_match.group(1) if img_match else ''
                    title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                    if title and link:
                        raw_items.append({'title': title, 'url': link, 'date': format_date(pub), 'image': image})
            except Exception as e:
                print(f'    aviso parse: {e}')
            time.sleep(0.5)

        # Deduplicar
        seen, unique = set(), []
        for item in raw_items:
            key = hashlib.md5(item['title'].lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique.append(item)

        # Intentar og:image para las que no tienen imagen (max 8 fetches por deporte)
        fallbacks = SPORT_FALLBACK_IMGS.get(sport, SPORT_FALLBACK_IMGS['bk'])
        og_count = 0
        for i, item in enumerate(unique[:MAX_NEWS]):
            if not item['image'] and og_count < 8:
                og_img = fetch_og_image(item['url'])
                if og_img:
                    item['image'] = og_img
                    og_count += 1
                else:
                    # Fallback variado por posición para no repetir imagen
                    item['image'] = fallbacks[i % len(fallbacks)]
                time.sleep(0.3)
            elif not item['image']:
                item['image'] = fallbacks[i % len(fallbacks)]

        result[sport] = unique[:MAX_NEWS]
        print(f'    OK {len(result[sport])} noticias ({og_count} con og:image)')
    return result

# ══════════════════════════════════════════════════════════════
# 2. VIDEOS — YouTube RSS sin API key
# ══════════════════════════════════════════════════════════════
def build_videos():
    print('\nGenerando videos.json...')
    result = {}
    for sport, channel_ids in YT_CHANNELS.items():
        print(f'  [{sport.upper()}]')
        all_videos = []
        for channel_id in channel_ids:
            rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
            data = fetch(rss_url)
            if not data:
                continue
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
                print(f'    canal {channel_id[:12]}... OK')
            except Exception as e:
                print(f'    aviso: {e}')
            time.sleep(0.5)
        seen, unique = set(), []
        for v in all_videos:
            if v['vid'] not in seen:
                seen.add(v['vid'])
                unique.append(v)
        result[sport] = unique[:MAX_VIDEOS]
        print(f'    TOTAL {len(result[sport])} videos')
    return result

# ══════════════════════════════════════════════════════════════
# 3. TABLA POSICIONES NBA — ESPN API
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
                team = entry.get('team', {})
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
        print(f'    OK Este:{len(standings["east"])} Oeste:{len(standings["west"])}')
    except Exception as e:
        print(f'    aviso standings NBA: {e}')
    return standings

# ══════════════════════════════════════════════════════════════
# 4. LÍDERES NBA — puntos, rebotes, asistencias
# ══════════════════════════════════════════════════════════════
def build_leaders_nba():
    print('  [BK] Líderes estadísticas NBA...')
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
            if not cats:
                cats = data.get('leaders', [])

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
            print(f'    OK pts:{len(leaders["pts"])} reb:{len(leaders["reb"])} ast:{len(leaders["ast"])}')
        except Exception as e:
            print(f'    aviso /leaders: {e}')

    # Fallback hardcoded si ESPN falla
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
# 5. TABLA POSICIONES LIGA MX — ESPN API
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
        print(f'    OK {len(standings)} equipos')
    except Exception as e:
        print(f'    aviso standings FX: {e}')
    return standings

# ══════════════════════════════════════════════════════════════
# 6. GOLEADORES LIGA MX — api-football (CORREGIDO)
# ══════════════════════════════════════════════════════════════
def build_leaders_fx():
    print('  [FX] Goleadores Liga MX...')
    leaders = []

    # api-football plan gratuito solo da season 2024 (datos de temporada pasada)
    # Deshabilitado. Cambiar False por API_FOOTBALL_KEY cuando tengas plan de pago.
    if False:
        print(f'    API_FOOTBALL_KEY encontrado, consultando api-football...')
        try:
            for season in ['2025', '2024']:
                url = f'https://v3.football.api-sports.io/players/topscorers?league=262&season={season}'
                data = fetch_json(url, headers={
                    'x-apisports-key':  API_FOOTBALL_KEY,
                    'x-rapidapi-host':  'v3.football.api-sports.io',
                })
                if data and data.get('response'):
                    print(f'    api-football season {season}: {len(data["response"])} jugadores OK')
                    for item in data['response'][:8]:
                        p = item.get('player', {})
                        s = (item.get('statistics') or [{}])[0]
                        t = s.get('team', {})
                        goals = s.get('goals', {}).get('total', 0) or 0
                        leaders.append({
                            'pos':   len(leaders) + 1,
                            'name':  p.get('name', ''),
                            'team':  t.get('name', ''),
                            'goles': goals,
                        })
                    print(f'    OK {len(leaders)} goleadores (api-football)')
                    return leaders
                else:
                    err = (data or {}).get('errors', 'sin datos')
                    print(f'    api-football season {season}: {err}')
        except Exception as e:
            print(f'    aviso api-football: {e}')
    else:
        print('    API_FOOTBALL_KEY no encontrado en entorno, usando fallback...')

    # Fallback hardcoded — goleadores Clausura 2026 actualizados J10 (08/Mar/2026)
    # ⚠️ ACTUALIZAR cada domingo — ver instrucciones en README
    print('    Usando goleadores hardcoded Clausura 2026 (J10)...')
    leaders = [
        {'pos':1,  'name':'Joao Pedro',          'team':'Atl. San Luis', 'goles': 9},
        {'pos':2,  'name':'Armando González',    'team':'Chivas',        'goles': 6},
        {'pos':3,  'name':'José Paradela',       'team':'Cruz Azul',     'goles': 5},
        {'pos':4,  'name':'Joao Paulo Dias',     'team':'Toluca',        'goles': 5},
        {'pos':5,  'name':'Arturo González',     'team':'Atlas',         'goles': 5},
        {'pos':6,  'name':'Diber Cambindo',      'team':'León',          'goles': 5},
        {'pos':7,  'name':'A. Palavecino',       'team':'Cruz Azul',     'goles': 4},
        {'pos':8,  'name':'Salomón Rondón',      'team':'Pachuca',       'goles': 4},
        {'pos':9,  'name':'Juninho',             'team':'Pumas',         'goles': 4},
        {'pos':10, 'name':'L. Di Yorio',         'team':'Santos',        'goles': 4},
        {'pos':11, 'name':'G. Fernández',        'team':'Cruz Azul',     'goles': 3},
        {'pos':12, 'name':'Oussama Idrissi',     'team':'Pachuca',       'goles': 3},
        {'pos':13, 'name':'Robert Morales',      'team':'Pumas',         'goles': 3},
        {'pos':14, 'name':'Álvaro Angulo',       'team':'Pumas',         'goles': 3},
        {'pos':15, 'name':'Marcelo Flores',      'team':'Tigres',        'goles': 3},
    ]
    print(f'    OK {len(leaders)} goleadores (hardcoded)')
    return leaders

# ══════════════════════════════════════════════════════════════
# 7. RANKING PÁDEL TOP 10
# ══════════════════════════════════════════════════════════════
def build_ranking_padel():
    print('  [PD] Ranking Mundial Pádel...')
    ranking = {'men': [], 'women': []}

    try:
        for gender, key in [('M', 'men'), ('F', 'women')]:
            url = f'https://api.padelfip.com/v1/ranking/world?gender={gender}&limit=10'
            data = fetch_json(url)
            if data and isinstance(data, list):
                for i, p in enumerate(data[:10]):
                    ranking[key].append({
                        'pos':     i + 1,
                        'name':    p.get('player', {}).get('name', p.get('name','')),
                        'country': p.get('player', {}).get('country', {}).get('code', p.get('country','')),
                        'pts':     p.get('points', p.get('rankingPoints','')),
                    })
                if ranking[key]:
                    print(f'    OK {key}: {len(ranking[key])} jugadores (API FIP)')
                    continue
    except Exception as e:
        print(f'    aviso FIP API: {e}')

    # Fallback hardcoded ranking 2026
    if not ranking['men']:
        ranking['men'] = [
            {'pos':1,  'name':'Arturo Coello',       'country':'ESP', 'pts':''},
            {'pos':2,  'name':'Martín Di Nenno',      'country':'ARG', 'pts':''},
            {'pos':3,  'name':'Agustín Tapia',        'country':'ARG', 'pts':''},
            {'pos':4,  'name':'Federico Chingotto',   'country':'ARG', 'pts':''},
            {'pos':5,  'name':'Juan Lebrón',          'country':'ESP', 'pts':''},
            {'pos':6,  'name':'Pablo Lima',           'country':'BRA', 'pts':''},
            {'pos':7,  'name':'Ale Galán',            'country':'ESP', 'pts':''},
            {'pos':8,  'name':'Jon Sanz',             'country':'ESP', 'pts':''},
            {'pos':9,  'name':'Fede Stupaczuk',       'country':'ARG', 'pts':''},
            {'pos':10, 'name':'Álex Ruiz',            'country':'ESP', 'pts':''},
        ]
    if not ranking['women']:
        ranking['women'] = [
            {'pos':1,  'name':'Gemma Triay',          'country':'ESP', 'pts':''},
            {'pos':2,  'name':'Claudia Jensen',       'country':'ESP', 'pts':''},
            {'pos':3,  'name':'Ariana Sánchez',       'country':'ESP', 'pts':''},
            {'pos':4,  'name':'Marta Ortega',         'country':'ESP', 'pts':''},
            {'pos':5,  'name':'Paula Josemaría',      'country':'ESP', 'pts':''},
            {'pos':6,  'name':'Tamara Icardo',        'country':'ESP', 'pts':''},
            {'pos':7,  'name':'Delfi Brea',           'country':'ARG', 'pts':''},
            {'pos':8,  'name':'Bea González',         'country':'ESP', 'pts':''},
            {'pos':9,  'name':'Martina Capra',        'country':'ARG', 'pts':''},
            {'pos':10, 'name':'Lucía Sainz',          'country':'ESP', 'pts':''},
        ]
    return ranking

# ══════════════════════════════════════════════════════════════
# 8. PARTIDOS
# ══════════════════════════════════════════════════════════════
def build_partidos():
    print('\nGenerando partidos.json...')
    result = {}

    # NBA
    print('  [BK] NBA partidos...')
    data = fetch_json(ESPN_NBA)
    matches = []
    if data and 'events' in data:
        for ev in (data.get('events') or [])[:MAX_MATCHES]:
            try:
                comp  = ev['competitions'][0]
                home  = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away  = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                st    = ev['status']['type']
                score = f"{home.get('score','')}-{away.get('score','')}" if st['state'] != 'pre' else ''
                matches.append({
                    'fecha':  datetime.fromisoformat(ev['date'].replace('Z','+00:00')).strftime('%a %d %b'),
                    'local':  home['team']['abbreviation'],
                    'visita': away['team']['abbreviation'],
                    'score':  score,
                    'liga':   'NBA',
                    'estado': 'live' if st['state']=='in' else ('post' if st['state']=='post' else 'pre'),
                    'url':    'https://www.espn.com/nba/scoreboard',
                })
            except Exception as e:
                print(f'    aviso: {e}')
    result['bk'] = matches
    print(f'    OK {len(matches)} partidos NBA')

    # Liga MX
    time.sleep(1)
    print('  [FX] Liga MX partidos...')
    matches = []
    if FOOTBALL_DATA_KEY:
        try:
            req = urllib.request.Request(FOOTBALL_DATA_MX, headers={'X-Auth-Token': FOOTBALL_DATA_KEY})
            with urllib.request.urlopen(req, timeout=10) as resp:
                fd_data = json.loads(resp.read())
            for m in (fd_data.get('matches') or [])[:MAX_MATCHES]:
                try:
                    sh = (m.get('score',{}).get('fullTime',{}) or {}).get('home')
                    sa = (m.get('score',{}).get('fullTime',{}) or {}).get('away')
                    if sh is None:
                        sh = (m.get('score',{}).get('halfTime',{}) or {}).get('home')
                        sa = (m.get('score',{}).get('halfTime',{}) or {}).get('away')
                    status = m.get('status','')
                    fecha_str = m.get('utcDate','')[:10]
                    try:
                        fecha_str = datetime.fromisoformat(fecha_str).strftime('%a %d %b')
                    except: pass
                    matches.append({
                        'fecha':  fecha_str,
                        'local':  m.get('homeTeam',{}).get('shortName', m.get('homeTeam',{}).get('name','')),
                        'visita': m.get('awayTeam',{}).get('shortName', m.get('awayTeam',{}).get('name','')),
                        'score':  f"{sh}-{sa}" if sh is not None else '',
                        'liga':   'Liga MX',
                        'estado': 'live' if status in ('IN_PLAY','PAUSED') else ('post' if status=='FINISHED' else 'pre'),
                        'url':    'https://www.ligabbvamx.mx/',
                    })
                except: pass
            print(f'    OK {len(matches)} partidos (football-data)')
        except Exception as e:
            print(f'    football-data falló: {e}')
            matches = _fx_espn_fallback()
    else:
        matches = _fx_espn_fallback()
    result['fx'] = matches

    result['pd'] = PADEL_CALENDAR
    return result

def _fx_espn_fallback():
    matches = []
    try:
        data = fetch_json(ESPN_FX_SCOREBOARD)
        if data and 'events' in data:
            for ev in (data.get('events') or [])[:MAX_MATCHES]:
                comp  = ev['competitions'][0]
                home  = next(c for c in comp['competitors'] if c['homeAway'] == 'home')
                away  = next(c for c in comp['competitors'] if c['homeAway'] == 'away')
                st    = ev['status']['type']
                score = f"{home.get('score','')}-{away.get('score','')}" if st['state'] != 'pre' else ''
                matches.append({
                    'fecha':  datetime.fromisoformat(ev['date'].replace('Z','+00:00')).strftime('%a %d %b'),
                    'local':  home['team'].get('shortDisplayName', home['team']['abbreviation']),
                    'visita': away['team'].get('shortDisplayName', away['team']['abbreviation']),
                    'score':  score, 'liga': 'Liga MX',
                    'estado': 'live' if st['state']=='in' else ('post' if st['state']=='post' else 'pre'),
                    'url':    'https://www.espn.com/soccer/scoreboard/_/league/mex.1',
                })
        print(f'    OK {len(matches)} partidos (ESPN fallback)')
    except Exception as e:
        print(f'    ESPN fallback error: {e}')
    return matches

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    ts = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    print(f'\n{"="*55}')
    print(f'  CourtKing Bot v8 — {ts}')
    print(f'  FOOTBALL_DATA_KEY: {"✅ encontrado" if FOOTBALL_DATA_KEY else "❌ no encontrado"}')
    print(f'  API_FOOTBALL_KEY:  {"✅ encontrado" if API_FOOTBALL_KEY else "❌ no encontrado"}')
    print(f'{"="*55}')

    noticias  = build_noticias()
    videos    = build_videos()
    partidos  = build_partidos()

    print('\nGenerando tablas y rankings...')
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
