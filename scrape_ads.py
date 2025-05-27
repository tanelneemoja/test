from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time
import subprocess
 
# Keywords to search (Estonian + English)
KEYWORDS = [
    "elekter", "elektrileping", "elektripaketid", "elektribörs",
    "börsielekter", "elektri börsihind", "elektri paketid", "elektrimüüjad",
    "electricity", "electric contract", "electric packages", "electricity market",
    "electric price", "electric plans", "electric sellers"
]

# Ad indicators (Estonian + English)
AD_INDICATORS = ['Reklaam', 'Sponsoreeritud', 'Sponsitud', 'Ad', 'Sponsored']

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    driver = webdriver.Firefox(options=options)
    return driver

def is_ad_text(text):
    if not text:
        return False
    text_lower = text.lower()
    for indicator in AD_INDICATORS:
        if indicator.lower() in text_lower:
            return True
    return False

def scrape_ads_google(driver, keyword):
    url = f"https://www.google.com/search?q={keyword}"
    driver.get(url)
    time.sleep(3)  # wait for page to load

    ads = []
    # Google ads usually have 'Ad' label in some span or div — scrape titles near those
    ad_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-text-ad='1'], div[data-ads-ad]")

    # If above doesn't work, try to find blocks that contain "Ad" or Estonian equivalents
    if not ad_elements:
        ad_elements = driver.find_elements(By.XPATH, "//span[contains(text(),'Ad') or contains(text(),'Reklaam') or contains(text(),'Sponsoreeritud') or contains(text(),'Sponsitud')]")

    for ad_el in ad_elements:
        try:
            ad_text = ad_el.text
            if is_ad_text(ad_text):
                # Try to get parent container's headline or description
                parent = ad_el.find_element(By.XPATH, '..')
                ads.append(parent.text.strip())
        except Exception:
            pass

    # If still empty, fallback to generic ad blocks
    if not ads:
        # This tries to get sponsored results container
        containers = driver.find_elements(By.CSS_SELECTOR, "div[data-text-ad]")
        for cont in containers:
            ads.append(cont.text.strip())

    return ads

def scrape_ads_bing(driver, keyword):
    url = f"https://www.bing.com/search?q={keyword}"
    driver.get(url)
    time.sleep(3)

    ads = []
    # Bing ads often have 'Ad' label or "Sponsoreeritud" (Estonian)
    ad_labels = driver.find_elements(By.XPATH, "//span[contains(text(),'Ad') or contains(text(),'Reklaam') or contains(text(),'Sponsoreeritud') or contains(text(),'Sponsitud')]")
    for label in ad_labels:
        try:
            # Usually the ad container is near the label span
            parent = label.find_element(By.XPATH, '../../..')  # adjust if needed
            ads.append(parent.text.strip())
        except Exception:
            pass

    return ads

def main():
    print("Firefox version:")
    print(subprocess.run(["firefox", "--version"], capture_output=True, text=True).stdout)
    print("Geckodriver version:")
    print(subprocess.run(["geckodriver", "--version"], capture_output=True, text=True).stdout)

    driver = setup_driver()

    all_ads = {}

    for kw in KEYWORDS:
        print(f"Scraping Google ads for keyword: {kw}")
        google_ads = scrape_ads_google(driver, kw)
        print(f"Found {len(google_ads)} ads on Google")
        print(f"Scraping Bing ads for keyword: {kw}")
        bing_ads = scrape_ads_bing(driver, kw)
        print(f"Found {len(bing_ads)} ads on Bing")
        all_ads[kw] = {
            "google": google_ads,
            "bing": bing_ads
        }

    driver.quit()

    # Save results to file
    with open("ads_results.txt", "w", encoding="utf-8") as f:
        for kw, ads_data in all_ads.items():
            f.write(f"Keyword: {kw}\n")
            f.write("Google Ads:\n")
            for ad in ads_data["google"]:
                f.write(ad + "\n---\n")
            f.write("Bing Ads:\n")
            for ad in ads_data["bing"]:
                f.write(ad + "\n---\n")
            f.write("\n\n")

    print("Scraping complete. Results saved in ads_results.txt")

if __name__ == "__main__":
    main()
