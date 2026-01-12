import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import time

def get_sitemap_url_count(urls):
    total_count = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in urls:
        print(f"Fetching sitemap: {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            # Handle potential encoding issues
            root = ET.fromstring(response.content)
            # Find all <loc> tags in the sitemap XML (handling namespaces)
            urls_in_sitemap = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            count = len(urls_in_sitemap)
            print(f"Found {count} URLs.")
            total_count += count
        except Exception as e:
            print(f"Error parsing sitemap {url}: {e}")
    return total_count

def get_google_indexed_count(domain):
    query = f"site:{domain}"
    url = f"https://www.google.com/search?q={query}&hl=en"
    # Using a very specific User-Agent to try and bypass simple bot detection
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 429:
            return "Blocked (Google detected a bot). Try again later or use an API."
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the result stats (e.g., "About 15,200 results")
        result_stats = soup.find('div', id='result-stats')
        
        if result_stats:
            # Strip non-numeric characters to get the raw number
            count_match = re.search(r'([\d,\.]+)', result_stats.text)
            if count_match:
                count_str = count_match.group(1).replace(',', '').replace('.', '')
                return int(count_str)
        return "Not found (Google may be hiding stats or layout changed)"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    sitemaps = [
        "https://api.rademar.ee/google/product_sitemap.xml",
        "https://api.rademar.ee/google/category_sitemap.xml"
    ]
    
    print("--- STARTING RADEMAR.EE INDEX AUDIT ---")
    s_count = get_sitemap_url_count(sitemaps)
    
    # Small delay to avoid instant bot flags
    time.sleep(2) 
    
    g_count = get_google_indexed_count("rademar.ee")
    
    print("\n--- RESULTS ---")
    print(f"Total Unique URLs in Sitemaps: {s_count}")
    print(f"Google Indexed Count (site:): {g_count}")
    
    if isinstance(g_count, int):
        index_rate = (g_count / s_count) * 100 if s_count > 0 else 0
        print(f"Indexation Rate: {index_rate:.2f}%")
        if index_rate < 50:
            print("CRITICAL: More than half your pages are missing from Google!")
    print("--- END OF AUDIT ---")
