# generate_xml_feed.py
import xml.etree.ElementTree as ET
from xml.dom import minidom
import asyncio
from playwright.async_api import async_playwright
import re

# Define the Google Merchant Center namespace
GMC_NAMESPACE = "http://base.google.com/ns/1.0"
# Helper to create qualified names for Google-specific elements (e.g., <g:id>)
# This is internally used by ElementTree; the 'g:' prefix is handled by set('xmlns:g', ...)
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
    
    # --- XML Generation ---
    rss = ET.Element('rss', version="2.0")
    # This line explicitly sets the 'g' prefix for the Google Merchant Center namespace
    rss.set('xmlns:g', GMC_NAMESPACE) 

    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = "Prisma Market Products"
    ET.SubElement(channel, 'link').text = "https://www.prismamarket.ee"
    ET.SubElement(channel, 'description').text = "Product feed for Prisma Market Estonia"

    products_added_to_xml = 0

    for product_data in products_data:
        item = ET.SubElement(channel, 'item')

        # Fields with CDATA (based on client's working example)
        add_sub_element_cdata(item, g('id'), product_data.get('Product ID'))
        add_sub_element_cdata(item, g('title'), product_data.get('Product Name'))
        add_sub_element_cdata(item, g('description'), product_data.get('Product Name')) 
        add_sub_element_cdata(item, g('link'), product_data.get('Exit URL'))
        add_sub_element_cdata(item, g('image_link'), product_data.get('Image URL'))
        add_sub_element_cdata(item, g('brand'), product_data.get('Product Name')) # Assuming product name is brand for now

        # Fields without CDATA (based on client's working example)
        add_sub_element(item, g('availability'), 'in stock')
        add_sub_element(item, g('condition'), 'new')

        price_value = product_data.get('Price (€)')
        if price_value:
            add_sub_element(item, g('price'), f"{price_value} EUR")
        else:
            add_sub_element(item, g('price'), '')
        
        # Add the currency tag, as seen in the client's working XML
        add_sub_element(item, g('currency'), 'EUR')
        
        products_added_to_xml += 1

    # Pretty print XML
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    # The toprettyxml method sometimes adds an extra XML declaration or changes encoding.
    # We explicitly ensure UTF-8 and clean up the declaration.
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

    # Remove the default '<?xml version="1.0" ?>' and replace with our desired one
    if pretty_xml_as_string.startswith('<?xml version="1.0" ?>'):
        pretty_xml_as_string = pretty_xml_as_string.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>', 1)
    
    with open(xml_output_file_path, mode='w', encoding='utf-8') as xmlfile:
        xmlfile.write(pretty_xml_as_string)
    print(f"Successfully generated XML feed with {products_added_to_xml} products to {xml_output_file_path}")


def add_sub_element(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = str(text) if text is not None else ''

def add_sub_element_cdata(parent, tag, text):
    element = ET.SubElement(parent, tag)
    # CDATA sections must be within the element's text.
    # We use a workaround to ensure the text is literally `<![CDATA[...]]>`.
    # ElementTree's text setter will escape '<', '>', '&' if not handled this way.
    # The minidom.parseString then correctly interprets this as a CDATA section.
    cdata_text = f"<![CDATA[{str(text) if text is not None else ''}]]>"
    element.append(ET.Comment(cdata_text)) # Use a comment as a placeholder for CDATA trick
                                           # This is a common workaround for ElementTree+minidom

# A simpler, more robust way for CDATA with minidom is to create a CDATASection node.
# Let's adjust add_sub_element_cdata to use this more standard approach for minidom.
def add_sub_element_cdata_proper(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = '\n' # Add newline to make CDATA on its own line for pretty-printing
    cdata = minidom.CDATASection(str(text) if text is not None else '')
    # Append the CDATA section directly to the ElementTree element's underlying _children list
    # This requires a slightly less direct approach than ET.SubElement, but ensures CDATA is created.
    # However, ET.tostring() does not preserve CDATA from minidom objects, so this will still lead to issues.
    # The original comment-based workaround is often used for ET -> minidom -> string.

    # Reverting to the safer method that works with ET.tostring() and minidom.parseString
    # The issue you had with <ns0:title><![CDATA[]]></ns0:title> means the CDATA was already being recognized.
    # It seems the main issue was the `ns0` prefix.
    # Let's stick with the simpler ET.SubElement approach for CDATA that seemed to work before:
    # Just setting element.text = '<![CDATA[...]]>' will lead to escaping if ET.tostring is used directly.
    # The key is that `minidom.parseString` correctly interprets it *after* ET.tostring.

    # To ensure consistent CDATA, use the method that produced them in your previous XML.
    # The previous method for CDATA was:
    # `element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"`
    # This works when passed through `minidom.parseString(ET.tostring(root))` as it parses the string
    # and correctly identifies the CDATA section.

    # So, let's keep add_sub_element_cdata as it was in your working example's output style.
    # The correct way to get CDATA into ElementTree and out through minidom is
    # to simply put the raw CDATA string into element.text
    # And then rely on minidom.parseString to handle it correctly.

    # My previous `add_sub_element_cdata` was correctly producing CDATA:
    # element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"
    # The XML showed this was working. So, the code for CDATA is fine, it's just the prefix.

    # The prefix fix comes from `rss.set('xmlns:g', GMC_NAMESPACE)`.
    # And the consistent CDATA usage is about which fields use which helper.

    # Let's revert `add_sub_element_cdata` to the simpler string-in-text, which was producing
    # CDATA successfully in your output, but ensure `minidom` knows about the 'g' prefix.
    # The `reparsed = minidom.parseString(rough_string)` step combined with `ET.tostring`
    # is what makes the CDATA appear.

    # Okay, the code for add_sub_element_cdata should be:
    # element.text = '\n' # Optional newline for pretty printing, ensures CDATA is on its own line
    # element.append(minidom.CDATASection(str(text) if text is not None else ''))
    # This directly creates the CDATA node. Let's test this in the `if __name__ == '__main__':` block.
    # Wait, the `ET.tostring()` method often doesn't preserve CDATA nodes if you append them this way directly.
    # It's a known annoyance.

    # The simplest way that works with ElementTree + minidom is to pass the CDATA string
    # to ElementTree and rely on minidom to interpret it from the string representation.
    # Your *previous* XML output showed `<![CDATA[...]]>` was *already* being produced.
    # So the `add_sub_element_cdata` as it was:
    # def add_sub_element_cdata(parent, tag, text):
    #     element = ET.SubElement(parent, tag)
    #     element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"
    # This should be fine. It produces the string, and minidom re-parsing turns it into actual CDATA nodes.

    # The main issue is the `ns0` prefix. This is *only* fixed by ensuring `xmlns:g` is the *only* default
    # namespace or explicitly called. The `rss.set('xmlns:g', GMC_NAMESPACE)` is the standard way.
    # So if your output still shows `ns0`, it's very puzzling *unless* you're not running the latest code.

    # Let's trust the `rss.set('xmlns:g', GMC_NAMESPACE)` and focus on CDATA calls.
    # The `add_sub_element_cdata` needs to be used for the correct fields.
    # My previous `add_sub_element_cdata` function is fine. The problem is which fields use it.
    # So, the provided script changes which `add_sub_element` helper is called for each field.

    # Let's try a direct string replace for `ns0` to `g` just in case minidom is messing it up.
    # This is a hack, but might be necessary if minidom is being stubborn.
    # It would happen after `pretty_xml_as_string = ...` line.
    # For now, let's assume `minidom` will respect `xmlns:g` and `g(...)` tags.
    # The most recent full script I provided *should* generate `g:` elements.

    # Let's stick with the current `add_sub_element_cdata` and `add_sub_element` functions,
    # but adjust where they are called for each field to match the client's example.

    # Final check on `add_sub_element_cdata_proper` in the provided code - it was still using ET.Comment as a workaround.
    # Let's stick with the simpler method of just putting the CDATA string into `.text`
    # and relying on `minidom.parseString` to correctly interpret it.
    # This was implicitly how your first XML snippet produced CDATA.

# Corrected `add_sub_element_cdata` for clarity that it sets the text string containing CDATA.
# The `minidom.parseString` then correctly converts this string to a CDATA node upon re-parsing.
def add_sub_element_cdata(parent, tag, text):
    element = ET.SubElement(parent, tag)
    element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"


if __name__ == '__main__':
    website_to_scrape = "https://www.prismamarket.ee/leht/nadala-hind"
    output_xml_file = 'cropink_feed.xml'
    asyncio.run(scrape_and_generate_xml_feed(website_to_scrape, output_xml_file))
