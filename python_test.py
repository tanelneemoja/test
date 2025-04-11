from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options  # Importing options for headless mode
import time
import re
from datetime import datetime, timedelta

# Calculate the dynamic start and end dates
end_date = datetime.today().strftime('%Y-%m-%d')  # Today's date as the end date
start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')  # One year ago as the start date

# Construct the URL with dynamic dates
url = f"https://adstransparency.google.com/?region=EE&domain=seb.ee&start-date={start_date}&end-date={end_date}"

# Set up Firefox options to run headless (without a GUI)
firefox_options = Options()
firefox_options.add_argument("--headless")  # Ensure the browser is headless
firefox_options.add_argument("--no-sandbox")  # Disables the sandbox for CI environments
firefox_options.add_argument("--disable-dev-shm-usage")  # To avoid issues on CI servers

# Initialize the Firefox WebDriver with headless options
driver = webdriver.Firefox(options=firefox_options)  # No need for the path if geckodriver is in PATH

# Open the Ads Transparency Center page for seb.ee in Estonia with dynamic dates
driver.get(url)

# Wait for the page to load
time.sleep(5)

# Function to scrape ad data
def scrape_ads():
    ad_elements = driver.find_elements(By.TAG_NAME, 'creative-preview')
    for ad in ad_elements:
        try:
            # Extract the advertiser name
            advertiser_name = ad.find_element(By.CLASS_NAME, 'advertiser-name').text
            
            # Extract the image URL (creative image)
            image_url = ad.find_element(By.TAG_NAME, 'img').get_attribute('src')
            
            # Extract the link to the creative (ad details)
            creative_link = ad.find_element(By.TAG_NAME, 'a').get_attribute('href')

            # Use regular expressions to extract the Advertiser ID and Creative ID from the URL
            match = re.search(r'/advertiser/([^/]+)/creative/([^?]+)', creative_link)
            if match:
                advertiser_id = match.group(1)
                creative_id = match.group(2)
            else:
                advertiser_id, creative_id = None, None

            # Print the results, including the advertiser and creative IDs
            print(f"Advertiser: {advertiser_name}, Image URL: {image_url}, Creative Link: {creative_link}, Advertiser ID: {advertiser_id}, Creative ID: {creative_id}")
        
        except Exception as e:
            print(f"Error extracting ad data: {e}")

# Scrape initial data
scrape_ads()

# Now we need to click the "See all ads" button and scrape additional data
while True:
    try:
        # Wait for the "See all ads" button to be clickable
        see_all_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//div[text()="See all ads"]'))  # Adjust the XPath if necessary
        )

        # Scroll the button into view
        driver.execute_script("arguments[0].scrollIntoView();", see_all_button)

        # Use JavaScript to click the button if the ripple effect is blocking
        driver.execute_script("arguments[0].click();", see_all_button)

        # Wait for the new ads to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, 'creative-preview'))  # Wait for ad elements to appear
        )

        # Scrape the newly loaded ads
        scrape_ads()

        # Scroll down further to load more ads (5000 pixels)
        driver.execute_script("window.scrollBy(0, 5000);")  # Scroll down by 5000 pixels
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, 'creative-preview'))  # Wait for ads to load after scrolling
        )

    except Exception as e:
        # If no "See all ads" button is found or an error occurs, stop the loop
        print("No more ads to load or error: ", e)
        break

# Close the WebDriver after scraping
driver.quit()
