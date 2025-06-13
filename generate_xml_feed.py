# generate_xml_feed.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import asyncio
from playwright.async_api import async_playwright
import re # Needed for potential date extraction, though not used in current logic for XML feed
            # It's good to keep if you were to adapt it for date-related info again.

# Define the Google Merchant Center namespace
GMC_NAMESPACE = "http://base.google.com/ns/1.0"
# Helper to create qualified names for Google-specific elements (e.g., <g:id>)
g = lambda tag: f"{{{GMC_NAMESPACE}}}{tag}"

async def scrape_and_generate_xml_feed(website_url, xml_output_file_path):
    """
    Scrapes product data from the website, processes it, and generates an XML feed
    in Google Merchant Center (RSS 2.0) format.
    """
    products_data = [] # This list will hold the scraped and cleaned product dictionaries

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Run headless on GitHub Actions
        page = await browser.new_page()

        print(f"Navigating to {website_url}")
        try:
            # Wait until the network is idle, indicating most dynamic content should be loaded
            await page.goto(website_url, wait_until="networkidle", timeout=60000) # Increased timeout
            print("Page loaded successfully.")
        except Exception as e:
            print(f"ERROR: Failed to navigate to {website_url}: {e}")
            await browser.close()
            return # Exit if navigation fails

        print("Waiting for product cards to load...")
        try:
            # Wait for at least one product card to be present. This is critical.
            await page.wait_for_selector('article[data-test-id="product-card"]', timeout=30000) # Wait up to 30 seconds
            print("Product cards visible. Starting extraction.")
        except Exception as e:
            print(f"Timeout waiting for product cards: {e}")
            await browser.close()
            return # Exit if products don't load


        # Find all product article elements on the page
        product_articles = await page.query_selector_all('article[data-test-id="product-card"]')
        print(f"Found {len(product_articles)} potential product articles. Processing for XML feed...")

        for article in product_articles:
            product_id = await article.get_attribute('data-product-id')
            
            # Pad product_id with leading zeros to ensure 13 digits for EAN-13 format
            if product_id:
                product_id = product_id.zfill(13)
            else:
                product_id = 'N/A' # Default if ID is somehow missing

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
                # Check for missing image placeholder URL - if found, skip this product
                if image_url == "/icons/missing-product-image.svg":
                    print(f"  Skipping product '{product_name}' (ID: {product_id}) due to missing image placeholder.")
                    continue # Skip to the next product in the loop
            # If img_element is not found, image_url remains 'N/A' as initialized.

            # Exit URL
            exit_link = await article.query_selector('div[data-test-id="product-card__productName"] a')
            if exit_link:
                relative_path = await exit_link.get_attribute('href')
                if relative_path:
                    # Ensure it's an absolute URL
                    exit_url = f"https://www.prismamarket.ee{relative_path}"
                else:
                    exit_url = f"https://www.prismamarket.ee/toode/{product_id}" # Fallback if specific link is missing

            # Price
            price_span = await article.query_selector('span[data-test-id="display-price"]')
            if price_span:
                price_text = await price_span.inner_text()
                # Clean up price text: replace comma with dot, remove euro symbol, trim whitespace
                price = price_text.replace(',', '.').replace('€', '').strip()

            products_data.append({
                'Product ID': product_id,
                'Product Name': product_name,
                'Image URL': image_url,
                'Exit URL': exit_url,
                'Price (€)': price
            })
            # print(f"  Scraped: {product_name} (ID: {product_id})") # Uncomment for detailed local logging

        await browser.close()
    
    print(f"Finished scraping. Collected {len(products_data)} products for XML generation.")
    
    # --- XML Generation (integrated directly after scraping) ---
    rss = ET.Element('rss', version="2.0")
    rss.set('xmlns:g', GMC_NAMESPACE)

    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = "Prisma Market Products" # Customize
    ET.SubElement(channel, 'link').text = "https://www.prismamarket.ee" # Customize
    ET.SubElement(channel, 'description').text = "Product feed for Prisma Market Estonia" # Customize

    products_added_to_xml = 0

    for product_data in products_data:
        item = ET.SubElement(channel, 'item')

        add_sub_element(item, g('id'), product_data.get('Product ID'))
        add_sub_element_cdata(item, g('title'), product_data.get('Product Name'))
        add_sub_element_cdata(item, g('description'), product_data.get('Product Name')) 
        add_sub_element(item, g('availability'), 'in stock')
        add_sub_element(item, g('condition'), 'new')

        price_value = product_data.get('Price (€)')
        if price_value:
            add_sub_element(item, g('price'), f"{price_value} EUR")
        else:
            add_sub_element(item, g('price'), '')

        add_sub_element(item, g('link'), product_data.get('Exit URL'))
        add_sub_element(item, g('image_link'), product_data.get('Image URL'))
        add_sub_element_cdata(item, g('brand'), product_data.get('Product Name'))
        
        products_added_to_xml += 1

    # Pretty print XML
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

    if pretty_xml_as_string.startswith('<?xml version="1.0" ?>'):
        pretty_xml_as_string = pretty_xml_as_string.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>', 1)
    
    with open(xml_output_file_path, mode='w', encoding='utf-8') as xmlfile:
        xmlfile.write(pretty_xml_as_string)
    print(f"Successfully generated XML feed with {products_added_to_xml} products to {xml_output_file_path}")


def add_sub_element(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = str(text) if text is not None else ''

def add_sub_element_cdata(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"

if __name__ == '__main__':
    website_to_scrape = "https://www.prismamarket.ee/leht/nadala-hind" # Ensure this is the correct URL for special offers
    output_xml_file = 'cropink_feed.xml'
    asyncio.run(scrape_and_generate_xml_feed(website_to_scrape, output_xml_file))
