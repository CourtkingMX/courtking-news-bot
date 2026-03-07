"""
CourtKing News Bot v2
Genera noticias.json que el portal lee directamente desde GitHub CDN.
No requiere token de Shopify.
"""

import re, json, time, hashlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = {
    'bk': [
        'https://news.google.com/rss/search?q=NBA+basketball+2025&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=basketball+Mexico+Liga&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'pd': [
        'https://news.google.com/rss/search?q=padel+Mexico+torneo+2025&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=World+Padel+Tour+2025&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
    'fx': [
        'https://news.google.com/rss/search?q=Liga+MX+futbol+mexicano&hl=es-419&gl=MX&ceid=MX:es-419',
        'https://news.google.com/rss/search?q=seleccion+mexicana+futbol&hl=es-419&gl=MX&ceid=MX:es-419',
    ],
}

MAX_PER_SPORT = 4

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
        for item in root.findall('.//item')[:6]:
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
    print(f"CourtKing News Bot — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
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

        # Deduplicar
        seen, unique = set(), []
        for item in items:
            key = hashlib.md5(item['title'].encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                item['date'] = format_date(item['pub'])
                unique.append(item)

        result['sports'][sport] = unique[:MAX_PER_SPORT]
        print(f"  {len(result['sports'][sport])} noticias OK")

    # Guardar noticias.json
    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nnoticias.json generado!")
    print(f"Total noticias: {sum(len(v) for v in result['sports'].values())}")

if __name__ == '__main__':
    main()
