"""
CourtKing News Bot v6
- Noticias: Google News RSS (12 por deporte, más fuentes)
- Videos: YouTube RSS (sin API key)
- Partidos: ESPN API pública
- NUEVO: Tabla posiciones NBA + Liga MX
- NUEVO: Ranking Pádel top 10
- NUEVO: Líderes estadísticas (puntos NBA, goles Liga MX)
Corre cada 8h via GitHub Actions.
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
# FEEDS RSS — más fuentes, mejor cobertura
# ══════════════════════════════════════════════════════════════
NEWS_FEEDS = {
    'bk': [
        'https://news.google.com/rss/search?q=NBA+2026+resultados&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+highlights+mejores+jugadas&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=NBA+playoffs+standings+2026&hl=es&gl=US&ceid=US:es',
        'https://news.google.com/rss/search?q=basketball+NBA+draft+2026&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'pd': [
        'https://news.google.com/rss/search?q=Premier+Padel+2026+torneo&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+ranking+jugadores+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=padel+Mexico+Cancun+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Lebron+Williams+padel+FIP+2026&hl=es&gl=ES&ceid=ES:es',
    ],
    'fx': [
        'https://news.google.com/rss/search?q=Liga+MX+Clausura+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Champions+League+2026+octavos&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=LaLiga+Premier+League+futbol+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=futbol+mexicano+seleccion+2026&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=Copa+MX+futbol+mexicano+goles&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
}

ESPN_NBA    = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
ESPN_NBA_STANDINGS = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
ESPN_NBA_LEADERS   = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/leaders'
ESPN_FX_STANDINGS  = 'https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings'
ESPN_FX_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard?limit=10'
ESPN_FX_LEADERS    = 'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard'

FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY', '')
FOOTBALL_DATA_MX  = 'https://api.football-data.org/v4/competitions/MX1/matches?status=LIVE,IN_PLAY,PAUSED,FINISHED,SCHEDULED&limit=12'

# Ranking Pádel top 10 — API pública FIP
PADEL_RANKING_URL = 'https://api.padelfip.com/v1/ranking/world?gender=M&limit=10'

PADEL_CALENDAR = [
    {'fecha': '1-8 Mar 2026',   'torneo': 'Gijón P2',     'liga': 'Premier Padel — España',   'url': 'https://www.padelfip.com/es/evento/gijon-p2-2026/',                      'live': True},
    {'fecha': '16-22 Mar 2026', 'torneo': 'Cancún P2',    'liga': 'Premier Padel — México',   'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': '23-29 Mar 2026', 'torneo': 'Miami P1',     'liga': 'Premier Padel — EUA',      'url': 'https://www.miamipremierpadel.com/',                                     'live': False},
    {'fecha': '6-11 Abr 2026',  'torneo': 'Qatar Major',  'liga': 'Premier Padel — Doha',     'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'May 2026',       'torneo': 'Madrid Major', 'liga': 'Premier Padel — España',   'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'Jun 2026',       'torneo': 'París P1',     'liga': 'Premier Padel — Francia',  'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
    {'fecha': 'Nov 2026',       'torneo': 'Mexico Major', 'liga': 'Premier Padel — Acapulco', 'url': 'https://www.padelfip.com/es/calendario-premier-padel/?events-year=2026', 'live': False},
]

MAX_NEWS    = 12
MAX_VIDEOS  = 8
MAX_MATCHES = 10

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fetch(url, timeout=15, headers=None):
    try:
        h = {'User-Agent': 'Mozilla/5.0 (compatible; CourtkingBot/6.0)'}
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
                for item in root.findall('.//item')[:10]:
                    title = item.findtext('title', '').strip()
                    link  = item.findtext('link',  '').strip()
                    pub   = item.findtext('pubDate', '').strip()
                    desc  = item.findtext('description', '')
                    img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', desc)
                    image = img_match.group(1) if img_match else ''
                    title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
                    if title and link:
                        raw_items.append({'title': title, 'url': link, 'date': format_date(pub), 'image': image})
            except Exception as e:
                print(f'    aviso parse: {e}')
            time.sleep(0.6)
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
                standings[key].append({
                    'pos':    entry.get('rank', ''),
                    'team':   team.get('abbreviation', team.get('displayName','')),
                    'name':   team.get('shortDisplayName', team.get('displayName','')),
                    'w':      stats.get('wins', stats.get('wins','')),
                    'l':      stats.get('losses', ''),
                    'pct':    stats.get('winPercent', stats.get('playoffSeed','')),
                    'gb':     stats.get('gamesBehind', ''),
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
    data = fetch_json(ESPN_NBA_LEADERS)
    leaders = {'pts': [], 'reb': [], 'ast': []}
    if not data:
        return leaders
    try:
        for cat in data.get('categories', []):
            cat_name = cat.get('name', '').lower()
            key = None
            if 'point' in cat_name:  key = 'pts'
            elif 'rebound' in cat_name: key = 'reb'
            elif 'assist' in cat_name:  key = 'ast'
            if not key:
                continue
            for i, leader in enumerate(cat.get('leaders', [])[:5]):
                athlete = leader.get('athlete', {})
                leaders[key].append({
                    'pos':   i + 1,
                    'name':  athlete.get('shortName', athlete.get('displayName', '')),
                    'team':  leader.get('team', {}).get('abbreviation', ''),
                    'value': leader.get('displayValue', ''),
                })
        print(f'    OK pts:{len(leaders["pts"])} reb:{len(leaders["reb"])} ast:{len(leaders["ast"])}')
    except Exception as e:
        print(f'    aviso leaders NBA: {e}')
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
        # Puede estar en children[0] o directo en standings.entries
        for src in [data] + data.get('children', []):
            e = src.get('standings', {}).get('entries', [])
            if e:
                entries = e
                break
        for entry in entries[:12]:
            team  = entry.get('team', {})
            stats = {s['name']: s.get('displayValue', s.get('value','')) for s in entry.get('stats', [])}
            standings.append({
                'pos':  entry.get('rank', len(standings)+1),
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
# 6. GOLEADORES LIGA MX — ESPN scoreboard stats
# ══════════════════════════════════════════════════════════════
def build_leaders_fx():
    print('  [FX] Goleadores Liga MX...')
    # ESPN no tiene endpoint directo de goleadores para Liga MX sin auth
    # Usamos football-data.org si hay key, sino hardcoded top conocidos
    leaders = []
    if FOOTBALL_DATA_KEY:
        try:
            url = 'https://api.football-data.org/v4/competitions/MX1/scorers?limit=10'
            data = fetch_json(url, headers={'X-Auth-Token': FOOTBALL_DATA_KEY})
            if data:
                for s in (data.get('scorers') or [])[:8]:
                    p = s.get('player', {})
                    t = s.get('team', {})
                    leaders.append({
                        'pos':   len(leaders) + 1,
                        'name':  p.get('name', ''),
                        'team':  t.get('shortName', t.get('name','')),
                        'goles': s.get('goals', 0),
                    })
                print(f'    OK {len(leaders)} goleadores')
                return leaders
        except Exception as e:
            print(f'    aviso goleadores fd: {e}')
    # Fallback: ESPN leaders endpoint para soccer
    try:
        url = 'https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/leaders'
        data = fetch_json(url)
        if data:
            for cat in (data.get('categories') or [])[:1]:
                for i, ldr in enumerate((cat.get('leaders') or [])[:8]):
                    ath = ldr.get('athlete', {})
                    leaders.append({
                        'pos':   i + 1,
                        'name':  ath.get('shortName', ath.get('displayName','')),
                        'team':  ldr.get('team', {}).get('abbreviation',''),
                        'goles': ldr.get('displayValue',''),
                    })
            print(f'    OK {len(leaders)} goleadores (ESPN)')
    except Exception as e:
        print(f'    aviso goleadores ESPN: {e}')
    return leaders

# ══════════════════════════════════════════════════════════════
# 7. RANKING PÁDEL TOP 10 — FIP API o hardcoded actualizado
# ══════════════════════════════════════════════════════════════
def build_ranking_padel():
    print('  [PD] Ranking Mundial Pádel...')
    # Intentar API FIP
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

    # Fallback hardcoded ranking 2026 conocido
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
        print('    OK men: hardcoded top 10')
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
        print('    OK women: hardcoded top 10')
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
    print(f'    OK {len(matches)} partidos')

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
    except Exception as e:
        print(f'    ESPN fallback error: {e}')
    return matches

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    ts = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    print(f'\n{"="*55}')
    print(f'  CourtKing Bot v6 — {ts}')
    print(f'{"="*55}')

    noticias   = build_noticias()
    videos     = build_videos()
    partidos   = build_partidos()

    # Tablas y rankings
    print('\nGenerando tablas y rankings...')
    standings_nba  = build_standings_nba()
    leaders_nba    = build_leaders_nba()
    standings_fx   = build_standings_fx()
    leaders_fx     = build_leaders_fx()
    ranking_padel  = build_ranking_padel()

    # Guardar JSONs
    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': noticias}, f, ensure_ascii=False, indent=2)

    with open('videos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': videos}, f, ensure_ascii=False, indent=2)

    with open('partidos.json', 'w', encoding='utf-8') as f:
        json.dump({'updated': ts, 'sports': partidos}, f, ensure_ascii=False, indent=2)

    # NUEVO: tablas.json con standings + leaders + ranking pádel
    with open('tablas.json', 'w', encoding='utf-8') as f:
        json.dump({
            'updated': ts,
            'nba': {
                'standings': standings_nba,
                'leaders':   leaders_nba,
            },
            'fx': {
                'standings': standings_fx,
                'leaders':   leaders_fx,
            },
            'pd': {
                'ranking': ranking_padel,
            }
        }, f, ensure_ascii=False, indent=2)

    total_n = sum(len(v) for v in noticias.values())
    total_v = sum(len(v) for v in videos.values())
    total_p = sum(len(v) for v in partidos.values())
    print(f'\n{"="*55}')
    print(f'  OK noticias.json  -> {total_n} noticias')
    print(f'  OK videos.json    -> {total_v} videos')
    print(f'  OK partidos.json  -> {total_p} partidos')
    print(f'  OK tablas.json    -> NBA+LigaMX+Padel')
    print(f'{"="*55}\n')

if __name__ == '__main__':
    main()
