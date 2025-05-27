from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import time

KEYWORDS = [
    "elekter", "elektrileping", "elektripaketid", "elektribörs",
    "börsielekter", "elektri börsihind", "elektri paketid", "elektrimüüjad",
    # English versions
    "electricity", "electric contract", "electric packages", "electricity exchange",
    "electric market price", "electric packages", "electricity sellers"
]

ESTONIAN_AD_KEYWORDS = ["reklaam", "sponsoreeritud", "sponsitud"]
ENGLISH_AD_KEYWORDS = ["ad", "sponsored", "sponsorship"]

def setup_driver():
    options = Options()
    options.headless = True
    options.set_preference("intl.accept_languages", "et,en")
    driver = webdriver.Firefox(options=options)
    return driver

def get_ads_from_google(driver, keyword):
    ads_texts = []
    url = f"https://www.google.com/search?q={keyword}"
    driver.get(url)
    time.sleep(3)  # Wait for ads and page to load

    # Ads container divs have aria-label like "Ads" or "Reklaam"
    ad_elements = driver.find_elements(By.XPATH, "//div[contains(@aria-label,'Ads') or contains(@aria-label,'Reklaam')]//div[contains(@class,'uEierd')]")
    if not ad_elements:
        # fallback: look for known ad labels and texts
        ad_elements = driver.find_elements(By.XPATH, "//div[contains(text(),'Ad') or contains(text(),'Reklaam') or contains(text(),'Sponsored') or contains(text(),'Sponsoreeritud')]//following-sibling::div")

    for ad in ad_elements:
        text = ad.text.strip()
        if text:
            ads_texts.append(text)
    return ads_texts

def get_ads_from_bing(driver, keyword):
    ads_texts = []
    url = f"https://www.bing.com/search?q={keyword}"
    driver.get(url)
    time.sleep(3)

    # Bing ads usually have "Ad" or "Sponsoreeritud" label near them
    ad_elements = driver.find_elements(By.XPATH, "//li[contains(@class,'b_ad')]//div[contains(@class,'b_caption')]")
    for ad in ad_elements:
        text = ad.text.strip()
        if text:
            ads_texts.append(text)
    return ads_texts

def main():
    driver = setup_driver()

    all_results = {}
    try:
        for kw in KEYWORDS:
            print(f"Searching ads for keyword: {kw}")
            google_ads = get_ads_from_google(driver, kw)
            bing_ads = get_ads_from_bing(driver, kw)

            all_results[kw] = {
                "google_ads": google_ads,
                "bing_ads": bing_ads
            }

            print(f"Google ads found: {len(google_ads)}")
            print(f"Bing ads found: {len(bing_ads)}")
    finally:
        driver.quit()

    # Save or print results (example print)
    for kw, ads in all_results.items():
        print(f"\nKeyword: {kw}")
        print("Google Ads:")
        for ad in ads["google_ads"]:
            print(f"- {ad}")
        print("Bing Ads:")
        for ad in ads["bing_ads"]:
            print(f"- {ad}")

if __name__ == "__main__":
    main()
