from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time

KEYWORDS = [
    "elekter", "elektrileping", "elektripaketid", "elektribörs",
    "börsielekter", "elektri börsihind", "elektri paketid", "elektrimüüjad"
]

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    return driver

def scrape_google(driver, keyword):
    driver.get(f"https://www.google.ee/search?q={keyword}")
    time.sleep(3)
    all_results = driver.find_elements(By.CSS_SELECTOR, 'div[data-text-ad]')
    
    # fallback if data-text-ad fails
    if not all_results:
        all_results = driver.find_elements(By.XPATH, "//span[contains(text(),'Reklaam') or contains(text(),'Sponsored') or contains(text(),'Sponsitud') or contains(text(),'Sponsoreeritud')]/ancestor::div[@data-content-feature]")

    return [ad.text for ad in all_results]

def scrape_bing(driver, keyword):
    driver.get(f"https://www.bing.com/search?q={keyword}")
    time.sleep(3)
    all_results = driver.find_elements(By.CSS_SELECTOR, 'li.b_ad')

    # filter by text labels
    ads = []
    for ad in all_results:
        text = ad.text.lower()
        if any(label in text for label in ['reklaam', 'sponsitud', 'sponsoreeritud', 'sponsored', 'ad']):
            ads.append(ad.text)
    return ads

def main():
    driver = setup_driver()
    all_results = []

    for keyword in KEYWORDS:
        google_ads = scrape_google(driver, keyword)
        bing_ads = scrape_bing(driver, keyword)
        all_results.append({
            "keyword": keyword,
            "google": google_ads,
            "bing": bing_ads
        })

    driver.quit()

    for result in all_results:
        print(f"Keyword: {result['keyword']}")
        print("Google Ads:")
        for ad in result["google"]:
            print("  -", ad.strip().replace("\n", " "))
        print("Bing Ads:")
        for ad in result["bing"]:
            print("  -", ad.strip().replace("\n", " "))
        print("-" * 40)

if __name__ == "__main__":
    main()
