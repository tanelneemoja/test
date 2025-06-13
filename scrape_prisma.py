import asyncio
from playwright.async_api import async_playwright
import csv
import re
from datetime import datetime

async def scrape_prisma_market():
    url = "https://www.prismamarket.ee/leht/nadala-hind"
    output_filename = "prisma_products.csv"
    products_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle")

        # --- Extract Offer Period Date ---
        offer_period = "N/A"
        try:
            date_element = await page.query_selector("h2.cuehUj:has-text('Nädala eripakkumised')")
            if date_element:
                full_text = await date_element.inner_text()
                match = re.search(r'Nädala eripakkumised\s*(.+)', full_text)
                if match:
                    offer_period = match.group(1).strip()
            print(f"Extracted Offer Period: {offer_period}")
        except Exception as e:
            print(f"Could not extract offer period: {e}")

        # --- Extract Product Data ---
        print("Waiting for product cards to load...")
        try:
            await page.wait_for_selector('article[data-test-id="product-card"]', timeout=30000)
            print("Product cards visible. Starting extraction.")
        except Exception as e:
            print(f"Timeout waiting for product cards: {e}")
            await browser.close()
            return

        product_articles = await page.query_selector_all('article[data-test-id="product-card"]')
        print(f"Found {len(product_articles)} potential product articles. Processing...")

        for article in product_articles:
            product_id = await article.get_attribute('data-product-id')
            
            product_name = 'N/A'
            image_url = 'N/A'
            exit_url = 'N/A'
            price = 'N/A'

            # Product Name
            name_span = await article.query_selector('div[data-test-id="product-card__productName"] span[title]')
            if name_span:
                product_name = await name_span.get_attribute('title')

            # Image URL with missing image check
            img_element = await article.query_selector('img[data-test-id="product-card__productImage"]')
            if img_element:
                image_url = await img_element.get_attribute('src')
                # --- NEW CHECK FOR MISSING IMAGE ---
                if image_url == "/icons/missing-product-image.svg":
                    print(f"  Skipping product '{product_name}' (ID: {product_id}) due to missing image placeholder.")
                    continue # Skip to the next product in the loop
            # If img_element is not found, image_url remains 'N/A' as initialized.

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
                price = price_text.replace(',', '.').replace('€', '').strip()

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
