from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import time
import re
from datetime import datetime, timedelta

# Dates
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

# URL
url = f"https://adstransparency.google.com/?region=EE&domain=seb.ee&start-date={start_date}&end-date={end_date}"

# Headless Firefox
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

driver.get(url)
time.sleep(5)

# --- SCRAPING FUNCTION ---
def scrape_ads():
    ad_elements = driver.find_elements(By.TAG_NAME, 'creative-preview')
    print(f"Found {len(ad_elements)} ads")
    for ad in ad_elements:
        try:
            advertiser_name = ad.find_element(By.CLASS_NAME, 'advertiser-name').text
            image_url = ad.find_element(By.TAG_NAME, 'img').get_attribute('src')
            creative_link = ad.find_element(By.TAG_NAME, 'a').get_attribute('href')

            match = re.search(r'/advertiser/([^/]+)/creative/([^?]+)', creative_link)
            advertiser_id = match.group(1) if match else None
            creative_id = match.group(2) if match else None

            print(f"Advertiser: {advertiser_name}\nImage: {image_url}\nLink: {creative_link}\nAdvertiser ID: {advertiser_id}, Creative ID: {creative_id}\n")
        except Exception as e:
            print("Error:", e)

# --- SCROLLING FUNCTION ---
def scroll_until_end():
    seen_ads = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, 5000);")
        time.sleep(2)

        current_ads = driver.find_elements(By.TAG_NAME, 'creative-preview')
        print(f"Scraping {len(current_ads)} visible ads...")

        for ad in current_ads:
            href = ad.find_element(By.TAG_NAME, 'a').get_attribute('href')
            if href not in seen_ads:
                seen_ads.add(href)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print(f"Total unique ads found: {len(seen_ads)}")
    scrape_ads()

# --- SCRAPE FIRST ADS BEFORE CLICK ---
print("Scraping first visible ads...")
scrape_ads()

# --- CLICK THE "SEE ALL ADS" BUTTON ---
try:
    see_all_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//div[text()="See all ads"]'))
    )

    driver.execute_script("arguments[0].click();", see_all_button)
    print("Clicked 'See all ads' button")
    time.sleep(4)

    scroll_until_end()

except Exception as e:
    print("Error clicking 'See all ads':", e)

driver.quit()
