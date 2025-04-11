from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from datetime import datetime, timedelta
import time
import re
import pandas as pd

# Competitor domains
competitor_domains = ['seb.ee', 'rimi.ee']  # Add more as needed

# Get date range
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

# Selenium setup
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

# Excel output
all_data = {}

def scrape_ads_for_domain(domain):
    url = f"https://adstransparency.google.com/?region=EE&domain={domain}&start-date={start_date}&end-date={end_date}"
    print(f"Loading: {url}")
    driver.get(url)
    time.sleep(5)

    results = []

    def extract_ads():
        ad_elements = driver.find_elements(By.TAG_NAME, 'creative-preview')
        for ad in ad_elements:
            try:
                advertiser_name = ad.find_element(By.CLASS_NAME, 'advertiser-name').text
                image_url = ad.find_element(By.TAG_NAME, 'img').get_attribute('src')
                creative_link = ad.find_element(By.TAG_NAME, 'a').get_attribute('href')

                match = re.search(r'/advertiser/([^/]+)/creative/([^?]+)', creative_link)
                advertiser_id = match.group(1) if match else None
                creative_id = match.group(2) if match else None

                results.append({
                    "Advertiser Name": advertiser_name,
                    "Image URL": image_url,
                    "Creative Link": creative_link,
                    "Advertiser ID": advertiser_id,
                    "Creative ID": creative_id
                })
            except Exception as e:
                print("Error:", e)

    # Initial scrape before click
    extract_ads()

    # Click "See all ads" using JS
    try:
        see_all_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[text()="See all ads"]'))
        )
        driver.execute_script("arguments[0].click();", see_all_button)
        print("Clicked 'See all ads'")
        time.sleep(4)
    except Exception as e:
        print("No 'See all ads' or error:", e)

    # Scroll and scrape
    seen = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, 5000);")
        time.sleep(2)
        ad_elements = driver.find_elements(By.TAG_NAME, 'creative-preview')
        for ad in ad_elements:
            try:
                href = ad.find_element(By.TAG_NAME, 'a').get_attribute('href')
                if href not in seen:
                    seen.add(href)
                    advertiser_name = ad.find_element(By.CLASS_NAME, 'advertiser-name').text
                    image_url = ad.find_element(By.TAG_NAME, 'img').get_attribute('src')
                    match = re.search(r'/advertiser/([^/]+)/creative/([^?]+)', href)
                    advertiser_id = match.group(1) if match else None
                    creative_id = match.group(2) if match else None
                    results.append({
                        "Advertiser Name": advertiser_name,
                        "Image URL": image_url,
                        "Creative Link": href,
                        "Advertiser ID": advertiser_id,
                        "Creative ID": creative_id
                    })
            except:
                continue
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print(f"{domain}: Found {len(results)} ads")
    return results

# Run for each competitor
for domain in competitor_domains:
    data = scrape_ads_for_domain(domain)
    all_data[domain] = pd.DataFrame(data)

# Export to Excel
with pd.ExcelWriter("ad_results.xlsx", engine="openpyxl") as writer:
    for domain, df in all_data.items():
        sheet_name = domain.replace('.', '_')[:31]  # Excel sheet name max 31 chars
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print("✅ All data saved to ad_results.xlsx")

driver.quit()
