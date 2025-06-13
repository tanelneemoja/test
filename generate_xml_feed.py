import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Define the Google Merchant Center namespace
GMC_NAMESPACE = "http://base.google.com/ns/1.0"
# Helper to create qualified names for Google-specific elements (e.g., <g:id>)
g = lambda tag: f"{{{GMC_NAMESPACE}}}{tag}"

def generate_xml_feed(csv_file_path, xml_file_path):
    """
    Reads product data from a CSV, generates an XML feed in Google Merchant Center (RSS 2.0) format,
    and saves it.
    Assumes CSV headers: 'Product ID', 'Product Name', 'Image URL', 'Exit URL', 'Price (€)'
    """
    # Create the root <rss> element with version and Google namespace
    rss = ET.Element('rss', version="2.0")
    rss.set('xmlns:g', GMC_NAMESPACE) # Set the Google namespace attribute

    # Create the <channel> element, which contains feed metadata and products
    channel = ET.SubElement(rss, 'channel')
    
    # Add mandatory channel metadata (customize these for your shop)
    ET.SubElement(channel, 'title').text = "Prisma Market Products" # Your shop's feed title
    ET.SubElement(channel, 'link').text = "https://www.prismamarket.ee" # Your shop's main URL
    ET.SubElement(channel, 'description').text = "Product feed for Prisma Market Estonia" # Your shop's description

    products_added = 0 # Counter for logging

    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # Read the first row as headers, removing ' (€)' from 'Price (€)' if present
        headers = [h.strip().replace(' (€)', '') for h in next(reader)] 
        
        # Define the mapping from your CSV headers to the required XML element names
        header_map = {
            'Product ID': 'id',
            'Product Name': 'title',       # Also used for description and brand
            'Image URL': 'image_link',
            'Exit URL': 'link',
            'Price': 'price'
            # Add other CSV header mappings here if Cropink requires more specific fields
        }

        for row in reader:
            # Skip any completely empty rows in the CSV
            if not any(row): 
                continue

            product_data = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    product_data[headers[i]] = value.strip() # Store data with its original CSV header

            # Create an <item> element for each product, as required by Google RSS format
            item = ET.SubElement(channel, 'item')

            # Populate the XML elements according to Google Merchant Center specifications:
            # All product attributes must be prefixed with 'g:'
            # Use add_sub_element and add_sub_element_cdata helpers.

            # <g:id> - from 'Product ID'
            add_sub_element(item, g('id'), product_data.get(header_map['Product ID']))

            # <g:title> - always 'Product Name' with CDATA for free text
            add_sub_element_cdata(item, g('title'), product_data.get(header_map['Product Name']))

            # <g:description> - always 'Product Name' with CDATA for free text
            add_sub_element_cdata(item, g('description'), product_data.get(header_map['Product Name'])) 

            # <g:availability> - always 'in stock'
            add_sub_element(item, g('availability'), 'in stock')

            # <g:condition> - always 'new'
            add_sub_element(item, g('condition'), 'new')

            # <g:price> - from 'Price' + ' EUR'
            price_value = product_data.get(header_map['Price'])
            if price_value:
                add_sub_element(item, g('price'), f"{price_value} EUR")
            else:
                add_sub_element(item, g('price'), '') # Ensure price element exists even if empty

            # <g:link> - from 'Exit URL'
            add_sub_element(item, g('link'), product_data.get(header_map['Exit URL']))

            # <g:image_link> - from 'Image URL'
            add_sub_element(item, g('image_link'), product_data.get(header_map['Image URL']))

            # <g:brand> - always 'Product Name' with CDATA for free text
            add_sub_element_cdata(item, g('brand'), product_data.get(header_map['Product Name']))
            
            # --- IMPORTANT: Consider other mandatory Google Merchant Center fields ---
            # Depending on your product type and target country, you might need:
            # <g:gtin> (Global Trade Item Number like EAN, UPC, ISBN)
            # <g:mpn> (Manufacturer Part Number)
            # <g:google_product_category> (Google's product taxonomy)
            # <g:age_group>, <g:gender>, <g:color>, <g:size> (for apparel)
            # You would add these similarly, pulling data from your CSV if available.
            # Example: add_sub_element(item, g('gtin'), product_data.get('GTIN'))

            products_added += 1

    # --- Pretty Print and Save XML ---
    # This section formats the XML to be human-readable and saves it to a file.
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

    # Ensure the XML declaration specifies UTF-8 encoding correctly (minidom might add a default one)
    if pretty_xml_as_string.startswith('<?xml version="1.0" ?>'):
        pretty_xml_as_string = pretty_xml_as_string.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>', 1)
    
    with open(xml_file_path, mode='w', encoding='utf-8') as xmlfile:
        xmlfile.write(pretty_xml_as_string)
    print(f"Successfully generated XML feed with {products_added} products to {xml_file_path}")

def add_sub_element(parent, tag, text):
    """Helper to add a sub-element with plain text content."""
    element = ET.SubElement(parent, tag)
    element.text = str(text) if text is not None else '' # Ensure text is a string

def add_sub_element_cdata(parent, tag, text):
    """Helper to add a sub-element with CDATA section for free text content."""
    element = ET.SubElement(parent, tag)
    # CDATA prevents issues with special XML characters in text
    element.text = f"<![CDATA[{str(text) if text is not None else ''}]]>"

if __name__ == '__main__':
    # These are the default input/output file names for the script
    csv_input_file = 'prisma_products.csv' # Your source CSV file in GitHub
    xml_output_file = 'cropink_feed.xml'   # The generated XML file in GitHub
    generate_xml_feed(csv_input_file, xml_output_file)
