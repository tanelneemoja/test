import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time

def count_sitemap_urls(sitemap_urls):
    total = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in sitemap_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            # Handle Sitemap Index vs Simple Sitemap
            if '<sitemapindex' in response.text:
                # If it's an index, we'd need to fetch sub-sitemaps (simplified here)
                print(f"  [!] {url} is a Sitemap Index. Only counting top-level entries.")
            
            root = ET.fromstring(response.content)
            # Namespace handling for sitemaps
            urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            total += len(urls)
        except Exception as e:
            print(f"  [Error] Could not process {url}: {e}")
    return total

def run_audit():
    competitors = {
        "Rademar.ee": [
            "https://api.rademar.ee/google/product_sitemap.xml",
            "https://api.rademar.ee/google/category_sitemap.xml"
        ],
        "Ballzy.eu": [
            "https://ballzy.eu/pub/media/sitemap/sitemap.xml"
        ]
    }

    results = []

    print("--- STARTING MULTI-DOMAIN AUDIT ---")
    for name, sitemaps in competitors.items():
        print(f"\nAuditing {name}...")
        count = count_sitemap_urls(sitemaps)
        results.append({"name": name, "count": count})
        time.sleep(1) # Polite delay

    # Print Comparison Table
    print("\n" + "="*40)
    print(f"{'COMPETITOR':<20} | {'SITEMAP URLS':<15}")
    print("-" * 40)
    for res in results:
        print(f"{res['name']:<20} | {res['count']:<15,}")
    print("="*40)

    # Strategic Insight
    if len(results) >= 2:
        diff = abs(results[0]['count'] - results[1]['count'])
        winner = max(results, key=lambda x:x['count'])['name']
        print(f"\nINSIGHT: {winner} has {diff:,} more URLs in their sitemap.")
        print(f"This indicates a more aggressive 'Long Tail' SEO strategy.")

if __name__ == "__main__":
    run_audit()
