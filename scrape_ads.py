import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
 
KEYWORDS = [
    "elekter", "elektrileping", "elektripaketid", "elektribörs",
    "börsielekter", "elektri börsihind", "elektri paketid", "elektrimüüjad"
]
OUTPUT_FILE = "results.csv"
 
def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=et")
    return webdriver.Chrome(options=options)

def scrape_google_ads(driver, keyword):
    print(f"[Google] Searching for: {keyword}")
    driver.get(f"https://www.google.com/search?q={keyword}&hl=et")
    time.sleep(2)

    # Match Estonian ad labels + English 'Sponsored', case-insensitive
    ad_blocks = driver.find_elements(
        By.XPATH,
        "//span[translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')="
        "'reklaam' or translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')="
        "'sponsoreeritud' or translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')="
        "'sponsitud' or .='Sponsored']/ancestor::div[@data-text-ad]"
    )

    ads = []
    for ad in ad_blocks:
        try:
            headline = " | ".join([e.text for e in ad.find_elements(By.TAG_NAME, "h3") if e.text])
            description = " ".join([e.text for e in ad.find_elements(By.TAG_NAME, "div") if e.text])
            ads.append(("Google", keyword, headline.strip(), description.strip()))
        except Exception as e:
            print(f"Error parsing Google ad: {e}")
    return ads

def scrape_bing_ads(driver, keyword):
    print(f"[Bing] Searching for: {keyword}")
    driver.get(f"https://www.bing.com/search?q={keyword}&setlang=et")
    time.sleep(2)

    ads = []
    ad_blocks = driver.find_elements(By.CSS_SELECTOR, "li.b_ad")
    for ad in ad_blocks:
        try:
            headline = ad.find_element(By.TAG_NAME, "h2").text.strip()
            description = ad.find_element(By.CLASS_NAME, "b_caption").text.strip()
            ads.append(("Bing", keyword, headline, description))
        except Exception as e:
            print(f"Error parsing Bing ad: {e}")
    return ads

def main():
    driver = setup_driver()
    all_ads = []

    for keyword in KEYWORDS:
        all_ads.extend(scrape_google_ads(driver, keyword))
        all_ads.extend(scrape_bing_ads(driver, keyword))

    driver.quit()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Search Engine", "Keyword", "Headline", "Description"])
        writer.writerows(all_ads)

    print(f"Done. Ads saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
