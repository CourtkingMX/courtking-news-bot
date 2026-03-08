"""
CourtKing News Bot v3
Genera noticias.json que el portal lee directamente desde GitHub CDN.
- Basketball: NBA + México
- Padel: Premier Padel + México
- Fútbol: Internacional (Champions, Premier, LaLiga, Copa del Mundo, Selecciones)
"""

import re, json, time, hashlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = {
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

MAX_PER_SPORT = 6

def fetch_rss(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return None

def parse_items(xml_bytes):
    if not xml_bytes:
        return []
    try:
        root = ET.fromstring(xml_bytes)
        items = []
        for item in root.findall('.//item')[:8]:
            title = item.findtext('title', '').strip()
            link  = item.findtext('link', '').strip()
            pub   = item.findtext('pubDate', '').strip()
            title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
            if title and link:
                items.append({'title': title, 'url': link, 'pub': pub})
        return items
    except:
        return []

def format_date(pub_str):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str)
        meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        return f"{dt.day} {meses[dt.month-1]} {dt.year}"
    except:
        return datetime.now().strftime('%d/%m/%Y')

def main():
    print(f"\n{'='*50}")
    print(f"CourtKing News Bot v3 — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}\n")

    result = {
        'updated': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC'),
        'sports': {}
    }

    for sport, urls in FEEDS.items():
        print(f"Buscando {sport}...")
        items = []
        for url in urls:
            raw = fetch_rss(url)
            items.extend(parse_items(raw))
            time.sleep(1)

        seen, unique = set(), []
        for item in items:
            key = hashlib.md5(item['title'].lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                item['date'] = format_date(item['pub'])
                del item['pub']
                unique.append(item)

        result['sports'][sport] = unique[:MAX_PER_SPORT]
        print(f"  ✓ {len(result['sports'][sport])} noticias OK")

    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ noticias.json generado!")
    print(f"Total: {sum(len(v) for v in result['sports'].values())} noticias")

if __name__ == '__main__':
    main()
