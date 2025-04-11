from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options  # Importing options for headless mode
import time

# Set up Chrome options to run headless (without a GUI)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Ensure the browser is headless
chrome_options.add_argument("--no-sandbox")  # Disables the sandbox for CI environments
chrome_options.add_argument("--disable-dev-shm-usage")  # To avoid issues on CI servers

# Initialize the Chrome WebDriver with headless options
driver = webdriver.Chrome(options=chrome_options)  # No need for the path if chromedriver is in PATH

# Open the Ads Transparency Center page for seb.ee in Estonia
url = "https://adstransparency.google.com/?region=EE&domain=seb.ee"
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

            # Print the results
            print(f"Advertiser: {advertiser_name}, Image URL: {image_url}, Creative Link: {creative_link}")
        
        except Exception as e:
            print(f"Error extracting ad data: {e}")

# Scrape initial data
scrape_ads()

# Now we need to click the "See all ads" button and scrape additional data
while True:
    try:
        # Wait for the "See all ads" button to be clickable
        see_all_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[text()="See all ads"]'))  # Adjust the XPath if necessary
        )
        
        # Click the "See all ads" button
        see_all_button.click()
        
        # Wait for the new ads to load
        time.sleep(5)
        
        # Scrape the newly loaded ads
        scrape_ads()
    
    except Exception as e:
        # If no "See all ads" button is found or an error occurs, stop the loop
        print("No more ads to load or error: ", e)
        break

# Close the WebDriver after scraping
driver.quit()
