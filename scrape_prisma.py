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
        # Launch a headless Chromium browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigating to {url}")
        # Wait until the network is idle, indicating most dynamic content should be loaded
        await page.goto(url, wait_until="networkidle")

        # --- Extract Offer Period Date ---
        offer_period = "N/A"
        try:
            # Find the h2 element containing the date, relying on the class name and partial text
            # This class (cuehUj) might change, but it was previously stable for the date
            date_element = await page.query_selector("h2.cuehUj:has-text('Nädala eripakkumised')")
            if date_element:
                full_text = await date_element.inner_text()
                # Use regex to extract the date part (e.g., "11.-17.06")
                match = re.search(r'Nädala eripakkumised\s*(.+)', full_text)
                if match:
                    offer_period = match.group(1).strip()
            print(f"Extracted Offer Period: {offer_period}")
        except Exception as e:
            print(f"Could not extract offer period: {e}")

        # --- Extract Product Data ---
        print("Waiting for product cards to load...")
        try:
            # Wait for at least one product card to be present.
            # This is critical as products are loaded dynamically.
            await page.wait_for_selector('article[data-test-id="product-card"]', timeout=30000) # Wait up to 30 seconds
            print("Product cards visible. Starting extraction.")
        except Exception as e:
            print(f"Timeout waiting for product cards: {e}")
            await browser.close()
            return # Exit if products don't load

        # Find all product article elements
        product_articles = await page.query_selector_all('article[data-test-id="product-card"]')
        print(f"Found {len(product_articles)} product articles.")

        for article in product_articles:
            product_id = await article.get_attribute('data-product-id')
            
            product_name = 'N/A'
            image_url = 'N/A'
            exit_url = 'N/A'
            price = 'N/A'

            # Product Name (from title attribute of the span)
            name_span = await article.query_selector('div[data-test-id="product-card__productName"] span[title]')
            if name_span:
                product_name = await name_span.get_attribute('title')

            # Image URL
            img_element = await article.query_selector('img[data-test-id="product-card__productImage"]')
            if img_element:
                image_url = await img_element.get_attribute('src')

            # Exit URL
            exit_link = await article.query_selector('div[data-test-id="product-card__productName"] a')
            if exit_link:
                relative_path = await exit_link.get_attribute('href')
                if relative_path:
                    exit_url = "https://www.prismamarket.ee" + relative_path

            # Price
            price_span = await article.query_selector('span[data-test-id="display-price"]')
            if price_span:
                price_text = await price_span.inner_text()
                price = price_text.replace(',', '.').replace('€', '').strip() # Replace comma with dot for consistent numbers

            products_data.append({
                'Product ID': product_id,
                'Product Name': product_name,
                'Image URL': image_url,
                'Exit URL': exit_url,
                'Price (€)': price,
                'Offer Period': offer_period
            })
            # print(f"  Scraped: {product_name} (ID: {product_id})") # Uncomment for detailed local logging

        await browser.close()

    if products_data:
        # Write data to CSV file
        with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Product ID', 'Product Name', 'Image URL', 'Exit URL', 'Price (€)', 'Offer Period']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(products_data)
        print(f"Data saved to {output_filename}")
    else:
        print("No products scraped and no CSV file created.")

if __name__ == "__main__":
    asyncio.run(scrape_prisma_market())
