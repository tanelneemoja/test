# generate_xml_feed.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import asyncio
from playwright.async_api import async_playwright
import re # Used for advanced string replacements

# Define the Google Merchant Center namespace
GMC_NAMESPACE = "http://base.google.com/ns/1.0"
# Helper to create qualified names for Google-specific elements
g = lambda tag: f"{{{GMC_NAMESPACE}}}{tag}"

async def scrape_and_generate_xml_feed(website_url, xml_output_file_path):
    """
    Scrapes product data from the website, processes it, and generates an XML feed
    in Google Merchant Center (RSS 2.0) format.
    """
    products_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigating to {website_url}")
        try:
            await page.goto(website_url, wait_until="networkidle", timeout=60000)
            print("Page loaded successfully.")
        except Exception as e:
            print(f"ERROR: Failed to navigate to {website_url}: {e}")
            await browser.close()
            return

        print("Waiting for product cards to load...")
        try:
            await page.wait_for_selector('article[data-test-id="product-card"]', timeout=30000)
            print("Product cards visible. Starting extraction.")
        except Exception as e:
            print(f"Timeout waiting for product cards: {e}")
            await browser.close()
            return

        product_articles = await page.query_selector_all('article[data-test-id="product-card"]')
        print(f"Found {len(product_articles)} potential product articles. Processing for XML feed...")

        for article in product_articles:
            product_id = await article.get_attribute('data-product-id')
            if product_id:
                product_id = product_id.zfill(13)
            else:
                product_id = 'N/A'

            product_name = 'N/A'
            image_url = 'N/A'
            exit_url = 'N/A'
            price = 'N/A'

            name_span = await article.query_selector('div[data-test-id="product-card__productName"] span[title]')
            if name_span:
                product_name = await name_span.get_attribute('title')

            img_element = await article.query_selector('img[data-test-id="product-card__productImage"]')
            if img_element:
                image_url = await img_element.get_attribute('src')
                if image_url == "/icons/missing-product-image.svg":
                    print(f"  Skipping product '{product_name}' (ID: {product_id}) due to missing image placeholder.")
                    continue
            
            exit_link = await article.query_selector('div[data-test-id="product-card__productName"] a')
            if exit_link:
                relative_path = await exit_link.get_attribute('href')
                if relative_path:
                    exit_url = f"https://www.prismamarket.ee{relative_path}"
                else:
                    exit_url = f"https://www.prismamarket.ee/toode/{product_id}"

            price_span = await article.query_selector('span[data-test-id="display-price"]')
            if price_span:
                price_text = await price_span.inner_text()
                price = price_text.replace(',', '.').replace('€', '').strip()

            products_data.append({
                'Product ID': product_id,
                'Product Name': product_name,
                'Image URL': image_url,
                'Exit URL': exit_url,
                'Price (€)': price
            })

        await browser.close()
    
    print(f"Finished scraping. Collected {len(products_data)} products for XML generation.")
    
    # --- XML Generation (ElementTree part) ---
    rss = ET.Element('rss', version="2.0")
    # This line is crucial for ElementTree to know about the 'g' prefix.
    rss.set('xmlns:g', GMC_NAMESPACE) 

    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = "Prisma Market Products"
    ET.SubElement(channel, 'link').text = "https://www.prismamarket.ee"
    ET.SubElement(channel, 'description').text = "Product feed for Prisma Market Estonia"

    products_added_to_xml = 0

    for product_data in products_data:
        item = ET.SubElement(channel, 'item')

        # Use add_sub_element_plain for fields WITHOUT CDATA (based on client's working XML)
        add_sub_element_plain(item, g('id'), product_data.get('Product ID'))
        add_sub_element_plain(item, g('price'), f"{product_data.get('Price (€)')} EUR")
        add_sub_element_plain(item, g('condition'), 'new')
        add_sub_element_plain(item, g('currency'), 'EUR') # Added as per client's XML

        # Use add_sub_element_cdata for fields WITH CDATA (based on client's working XML)
        add_sub_element_cdata(item, g('title'), product_data.get('Product Name'))
        add_sub_element_cdata(item, g('description'), product_data.get('Product Name')) 
        add_sub_element_cdata(item, g('link'), product_data.get('Exit URL'))
        add_sub_element_cdata(item, g('image_link'), product_data.get('Image URL'))
        add_sub_element_cdata(item, g('availability'), 'in stock') # Client's XML has CDATA for availability
        add_sub_element_cdata(item, g('brand'), product_data.get('Product Name')) # Assuming product name is brand for now
        
        products_added_to_xml += 1

    # Pretty print XML using minidom
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

    # --- POST-PROCESSING FOR EXACT XML FORMAT (Prefix & Namespace Cleanup) ---

    # 1. Ensure XML declaration is correct (utf-8)
    if pretty_xml_as_string.startswith('<?xml version="1.0" ?>'):
        pretty_xml_as_string = pretty_xml_as_string.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>', 1)

    # 2. Force change ns0: to g: for all tags. This is the most reliable way.
    # We use a regex that matches `<ns0:tagname>` and `</ns0:tagname>`
    pretty_xml_as_string = re.sub(r'<ns0:([^>]+)>', r'<g:\1>', pretty_xml_as_string)
    pretty_xml_as_string = re.sub(r'</ns0:([^>]+)>', r'</g:\1>', pretty_xml_as_string)
    
    # 3. Clean up the duplicate xmlns:ns0 declaration in the <rss> tag if it appears
    pretty_xml_as_string = pretty_xml_as_string.replace('xmlns:ns0="http://base.google.com/ns/1.0"', '', 1)
    
    with open(xml_output_file_path, mode='w', encoding='utf-8') as xmlfile:
        xmlfile.write(pretty_xml_as_string)
    print(f"Successfully generated XML feed with {products_added_to_xml} products to {xml_output_file_path}")


# Helper function to add a simple sub-element with plain text (NO CDATA)
def add_sub_element_plain(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = str(text) if text is not None else ''

# Helper function to add a sub-element with CDATA (text wrapped with <![CDATA[...]]>)
def add_sub_element_cdata(parent, tag, text):
    element = ET.SubElement(parent, tag)
    # This method relies on minidom.parseString re-interpreting this string as a CDATA node
    element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"


if __name__ == '__main__':
    website_to_scrape = "https://www.prismamarket.ee/leht/nadala-hind"
    output_xml_file = 'cropink_feed.xml'
    asyncio.run(scrape_and_generate_xml_feed(website_to_scrape, output_xml_file))
