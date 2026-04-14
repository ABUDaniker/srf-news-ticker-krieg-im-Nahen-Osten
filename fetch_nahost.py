import urllib.request
import json
import re
import os

def fetch_and_save():
    url = 'https://www.srf.ch/news/international/nahost-konflikt'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
    except Exception as e:
        print("Fehler beim Abrufen der SRF-Seite:", e)
        return

    articles = []

    # --- Strategy 1: Extract teaser articles (main article cards) ---
    # SRF uses <a> tags with class "teaser" that contain image, title, and lead text
    teaser_pattern = re.compile(
        r'<a\s+[^>]*class="[^"]*teaser[^"]*"[^>]*href="([^"]*)"[^>]*>'
        r'(.*?)</a>',
        re.DOTALL | re.IGNORECASE
    )

    for match in teaser_pattern.finditer(html):
        href = match.group(1)
        content = match.group(2)

        # Only include nahost-konflikt or krieg-im-nahen-osten articles
        if 'nahost' not in href.lower() and 'nahen-osten' not in href.lower() and 'iran' not in href.lower():
            continue

        # Extract title
        title_match = re.search(r'<span[^>]*class="[^"]*teaser__title[^"]*"[^>]*>(.*?)</span>', content, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<h[23][^>]*>(.*?)</h[23]>', content, re.DOTALL)
        if not title_match:
            continue

        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        if not title:
            continue

        # Extract lead/teaser text
        lead = ""
        lead_match = re.search(r'<p[^>]*class="[^"]*teaser__lead[^"]*"[^>]*>(.*?)</p>', content, re.DOTALL)
        if lead_match:
            lead = re.sub(r'<[^>]+>', '', lead_match.group(1)).strip()

        # Extract image
        img_url = ""
        img_match = re.search(r'<img[^>]+src="([^"]+)"', content)
        if img_match:
            img_url = img_match.group(1)

        # Build full URL
        full_url = href if href.startswith('http') else 'https://www.srf.ch' + href

        # Extract date if present
        date = ""
        date_match = re.search(r'<time[^>]*datetime="([^"]*)"', content)
        if date_match:
            date = date_match.group(1)
        else:
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', content)
            if date_match:
                date = date_match.group(1)

        # Avoid duplicates
        if any(a['url'] == full_url for a in articles):
            continue

        articles.append({
            "title": title,
            "lead": lead,
            "url": full_url,
            "imageUrl": img_url,
            "date": date
        })

    # --- Strategy 2: Extract ticker entries (short newsticker items) ---
    ticker_pattern = re.compile(
        r'<li[^>]*>\s*<time[^>]*>([^<]*)</time>\s*<p[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE
    )

    for match in ticker_pattern.finditer(html):
        time_str = match.group(1).strip()
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if text and not any(a['title'] == text for a in articles):
            articles.append({
                "title": text,
                "lead": "",
                "url": url,
                "imageUrl": "",
                "date": time_str
            })

    # Keep only first 3 articles
    articles = articles[:3]

    if not articles:
        print("Keine Artikel gefunden!")
        return

    # If we got < 3 articles from teasers, try to get article text for the ones we have
    for article in articles:
        if article['url'] != url and not article['lead']:
            try:
                art_req = urllib.request.Request(article['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                art_html = urllib.request.urlopen(art_req, timeout=15).read().decode('utf-8')

                # Try og:description
                og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', art_html)
                if og_desc:
                    article['lead'] = og_desc.group(1).strip()

                # Get image if missing
                if not article['imageUrl']:
                    og_img = re.search(r'<meta\s+property="og:image"\s+content="([^"]*)"', art_html)
                    if og_img:
                        article['imageUrl'] = og_img.group(1)

            except Exception as e:
                print(f"Fehler beim Abrufen von {article['url']}: {e}")

    data = {
        "source": "SRF News - Krieg im Nahen Osten",
        "sourceUrl": url,
        "articles": articles
    }

    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news_data.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Erfolgreich {len(articles)} Artikel gespeichert:")
    for a in articles:
        print(f"  - {a['title']}")

if __name__ == '__main__':
    fetch_and_save()
