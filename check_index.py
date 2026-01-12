import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re

def get_sitemap_url_count(urls):
    total_count = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            root = ET.fromstring(response.content)
            # Find all <loc> tags in the sitemap XML
            urls_in_sitemap = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            print(f"Sitemap: {url.split('/')[-1]} -> {len(urls_in_sitemap)} URLs")
            total_count += len(urls_in_sitemap)
        except Exception as e:
            print(f"Error parsing sitemap {url}: {e}")
    return total_count

def get_google_indexed_count(domain):
    query = f"site:{domain}"
    url = f"https://www.google.com/search?q={query}&hl=en"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 429:
            return "Blocked by Google (Rate Limited)"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        result_stats = soup.find('div', id='result-stats')
        
        if result_stats:
            # Extract number from string like "About 15,200 results"
            count_str = re.sub(r'[^0-9]', '', result_stats.text)
            return int(count_str) if count_str else 0
        return "Not found (Google may have changed layout or blocked the request)"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    sitemaps = [
        "https://api.rademar.ee/google/product_sitemap.xml",
        "https://api.rademar.ee/google/category_sitemap.xml"
    ]
    
    print("--- Rademar Indexing Audit ---")
    s_count = get_sitemap_url_count(sitemaps)
    g_count = get_google_indexed_count("rademar.ee")
    
    print(f"\nTotal URLs in Sitemaps: {s_count}")
    print(f"Google Indexed Count (site:): {g_count}")
    
    if isinstance(g_count, int):
        gap = s_count - g_count
        print(f"Indexing Gap: {gap} pages are missing from search results.")
