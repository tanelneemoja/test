import asyncio
from playwright.async_api import async_playwright
import csv
import re
from datetime import datetime

async def scrape_prisma_market():
    url = "https://www.prismamarket.ee/leht/nadala-hind"
    output_filename = "prisma_products.csv" # Name of the CSV file to create
    products_data = []

    async with async_playwright() as p:
        # Launch a headless Chromium browser (headless=True means no browser window appears)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigating to {url}")
        # Wait until the network is idle, indicating most dynamic content should be loaded
        await page.goto(url, wait_until="networkidle")

        # --- Extract Offer Period Date ---
        offer_period = "N/A"
        try:
            # Select the H2 element that contains the offer period text
            date_element = await page.query_selector("h2.cuehUj:has-text('Nädala eripakkumised')")
            if date_element:
                full_text = await date_element.inner_text()
                # Use regex to extract the date part (e.g., "11.-17.06") after "Nädala eripakkumised"
                match = re.search(r'Nädala eripakkumised\s*(.+)', full_text)
                if match:
                    offer_period = match.group(1).strip()
            print(f"Extracted Offer Period: {offer_period}")
        except Exception as e:
            print(f"Could not extract offer period: {e}")

        # --- Extract Product Data ---
        print("Waiting for product cards to load...")
        try:
            # Crucial step for dynamic content: wait until at least one product card is present
            await page.wait_for_selector('article[data-test-id="product-card"]', timeout=30000) # Wait up to 30 seconds
            print("Product cards visible. Starting extraction.")
        except Exception as e:
            print(f"Timeout waiting for product cards: {e}")
            await browser.close()
            return # Exit the function if products don't load

        # Find all product article elements on the page
        product_articles = await page.query_selector_all('article[data-test-id="product-card"]')
        print(f"Found {len(product_articles)} potential product articles. Processing...")

        for article in product_articles:
            # Get the product ID from the data-product-id attribute
            product_id = await article.get_attribute('data-product-id')
            
            # --- NEW: Pad product_id with leading zeros to ensure 13 digits for EAN-13 format ---
            if product_id:
                product_id = product_id.zfill(13)
            # --- END NEW ---
            
            # Initialize variables with default 'N/A' in case data is missing
            product_name = 'N/A'
            image_url = 'N/A'
            exit_url = 'N/A'
            price = 'N/A'

            # Extract Product Name from the 'title' attribute of the span
            name_span = await article.query_selector('div[data-test-id="product-card__productName"] span[title]')
            if name_span:
                product_name = await name_span.get_attribute('title')

            # Extract Image URL
            img_element = await article.query_selector('img[data-test-id="product-card__productImage"]')
            if img_element:
                image_url = await img_element.get_attribute('src')
                # --- NEW: Check for missing image placeholder URL ---
                if image_url == "/icons/missing-product-image.svg":
                    print(f"  Skipping product '{product_name}' (ID: {product_id}) due to missing image placeholder.")
                    continue # Skip this product and move to the next one in the loop
            # If img_element is not found, image_url remains 'N/A' as initialized.

            # Extract Exit URL
            exit_link = await article.query_selector('div[data-test-id="product-card__productName"] a')
            if exit_link:
                relative_path = await exit_link.get_attribute('href')
                if relative_path:
                    exit_url = "https://www.prismamarket.ee" + relative_path # Construct full URL

            # Extract Price
            price_span = await article.query_selector('span[data-test-id="display-price"]')
            if price_span:
                price_text = await price_span.inner_text()
                # Clean up price text: replace comma with dot, remove euro symbol, trim whitespace
                price = price_text.replace(',', '.').replace('€', '').strip()

            # Add the scraped data to our list
            products_data.append({
                'Product ID': product_id,
                'Product Name': product_name,
                'Image URL': image_url,
                'Exit URL': exit_url,
                'Price (€)': price,
                'Offer Period': offer_period
            })
            # Uncomment the line below for more detailed logging during local testing
            # print(f"  Scraped: {product_name} (ID: {product_id})")

        await browser.close()

    # --- Write Scraped Data to CSV File ---
    if products_data:
        # Open the CSV file in write mode, ensuring proper newline handling and UTF-8 encoding
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            # Define the header row names for the CSV file
            fieldnames = ['Product ID', 'Product Name', 'Image URL', 'Exit URL', 'Price (€)', 'Offer Period']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader() # Write the header row
            writer.writerows(products_data) # Write all product data rows
        print(f"Data saved to {output_filename}")
    else:
        print("No products were scraped and no CSV file was created.")

if __name__ == "__main__":
    # Run the asynchronous scraping function
    asyncio.run(scrape_prisma_market())
