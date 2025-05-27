import asyncio
import json
import os
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_sync

# Configuration loaded from environment variables (GitHub Actions Secrets)
CONFIG = {
    "keywords": json.loads(os.environ.get("KEYWORDS_JSON", '[]')),
    "output_file": os.environ.get("OUTPUT_FILE", "competitor_ads.json"),
    "headless": os.environ.get("HEADLESS", "true").lower() == "true",
    "max_ads_per_page": int(os.environ.get("MAX_ADS_PER_PAGE", 5)),
    "delay_between_searches_seconds": int(os.environ.get("DELAY_BETWEEN_SEARCHES_SECONDS", 10)),
    "proxy_server": os.environ.get("PROXY_SERVER"),
    "proxy_username": os.environ.get("PROXY_username"),
    "proxy_password": os.environ.get("PROXY_PASSWORD")
}

async def scrape_google_ads(page, keyword, max_ads):
    search_url = f"https://www.google.com/search?q={keyword}&gl=EE&hl=en"
    print(f"Navigating to Google: {search_url}")
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Error navigating to Google search page for '{keyword}': {e}")
        return []

    stealth_sync(page)

    ads = []
    try:
        # Define all possible ad labels (English and Estonian)
        ad_labels = ["Ad", "Sponsored", "Reklaam", "Sponsoreeritud", "Sponsitud"]
        # Create a CSS selector that looks for ANY span containing these texts
        # We also specifically add the class you found: U3A9Ac qV8iec
        label_selectors = ", ".join([f'span:has-text("{label}")' for label in ad_labels])
        label_selectors += ', span.U3A9Ac.qV8iec' # Add the specific class you found

        # Find all elements that have these ad labels
        labeled_elements = await page.query_selector_all(label_selectors)

        # Now, for each labeled element, try to find its ultimate ad container parent
        # This is the crucial part that adapts to Google's wrapping of ad labels
        # Common Google Ad container classes/attributes:
        # div[data-text-ad] (older/general)
        # .uEac3e (common wrapper)
        # div[jsaction^="h.HqcS9a"] (another type of wrapper for ads)
        # div[jscontroller="e4F63e"] (often contains the ad group)
        # div[data-hveid] (general Google content block, but useful to check for ads inside)
        # .dGdCNb (another common ad container class)
        # .vdBfKf (yet another ad container class)

        potential_ad_containers = set()
        for labeled_el in labeled_elements:
            # Try to find a common parent that encapsulates the whole ad block
            # This is a list of potential parent selectors that are likely to be the ad's main div
            parent_selectors = [
                'div[data-text-ad]', # Older/common ad block
                '.uEac3e',           # Often wraps the ad content
                'div[jsaction^="h.HqcS9a"]', # Another common ad wrapper
                'div[jscontroller="e4F63e"]', # Often a container for ad groups
                'div[data-hveid]',   # General Google content block, check for ad-like children
                '.dGdCNb',            # Common ad container class
                '.vdBfKf',           # Another common ad container class
                '.ads-ad'            # Generic ad class
            ]

            for selector in parent_selectors:
                container = await labeled_el.evaluate_handle(f'el => el.closest("{selector}")')
                if container:
                    # Using object ID or outerHTML to get a unique representation of the element
                    potential_ad_containers.add(await container.evaluate("node => node.outerHTML"))
                    break # Found a parent, move to the next labeled element

        final_ad_elements_handles = []
        # Re-query the page for these specific outerHTMLs to get fresh element handles
        for outer_html in potential_ad_containers:
            # This is a bit tricky, but ensures we get the actual element handle back
            # It's better to get the elements directly from the page if possible.
            # A simpler way if the classes are unique enough:
            # ad_containers_by_class = await page.query_selector_all('div[data-text-ad], .uEac3e, div[jsaction^="h.HqcS9a"], div[jscontroller="e4F63e"], .dGdCNb, .vdBfKf, .ads-ad')
            # For this exact scenario, let's just use a broad approach and filter later.
            pass # We'll rely on the combined selector below

        # Let's try a combined approach directly in the query_selector_all
        # Look for containers that EITHER have known ad attributes/classes OR contain the ad label spans
        # This is complex in a single CSS selector. Let's revert to finding containers, then checking if they contain labels.

        # Re-think: Best approach is to find general containers that MIGHT be ads,
        # then check *their* inner text for the ad labels.
        # This is more robust than trying to find the label first and then going up.

        # Broad selection of elements that could be ad containers
        # These are commonly seen structural elements for ads on Google.
        potential_containers = await page.query_selector_all(
            'div[data-text-ad], .uEac3e, div[jsaction^="h.HqcS9a"], '
            'div[jscontroller="e4F63e"], div.dGdCNb, div.vdBfKf, .ads-ad'
        )

        print(f"Found {len(potential_containers)} potential Google ad containers.")

        for i, ad_element in enumerate(potential_containers):
            if len(ads) >= max_ads:
                break

            try:
                # Check if this potential ad_element contains any of the ad labels
                is_ad_label_present = await ad_element.evaluate(
                    f"""
                    (element) => {{
                        const adLabels = {json.dumps(ad_labels)}; // Pass labels as JSON
                        const specificLabelClass = 'U3A9Ac qV8iec'; // The specific class to check

                        // Check for text labels
                        for (const label of adLabels) {{
                            if (element.innerText.includes(label)) {{
                                return true;
                            }
                        }}
                        // Check for the specific span class within the element
                        if (element.querySelector('span.' + specificLabelClass.replace(' ', '.'))) {{
                            return true;
                        }}
                        return false;
                    }}
                    """
                )

                if is_ad_label_present:
                    title_element = await ad_element.query_selector('h3')
                    title_text = await title_element.inner_text() if title_element else 'N/A'

                    description_element = await ad_element.query_selector('div[data-sncf], div[role="text"], .VaQj8d, .VwiC3b') # Added .VwiC3b
                    description_text = await description_element.inner_text() if description_element else 'N/A'

                    link_element = await ad_element.query_selector('a[href]')
                    link_href = await link_element.get_attribute('href') if link_element else 'N/A'

                    ads.append({
                        'source': 'Google',
                        'keyword': keyword,
                        'title': title_text.strip(),
                        'description': description_text.strip(),
                        'link': link_href
                    })
                else:
                    # print(f"Element {i} skipped as no valid ad label or strong ad attribute found within its content.")
                    pass # Don't print for every skipped element, it's noisy

            except Exception as e:
                print(f"Error parsing Google ad element (index {i}): {e}")
                continue

    except Exception as e:
        print(f"Could not process Google ads for '{keyword}': {e}")
    return ads

async def scrape_bing_ads(page, keyword, max_ads):
    # loc=EE for Estonia
    search_url = f"https://www.bing.com/search?q={keyword}&loc=EE"
    print(f"Navigating to Bing: {search_url}")
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Error navigating to Bing search page for '{keyword}': {e}")
        return []

    stealth_sync(page)

    ads = []
    try:
        # Primary ad identification: Look for specific HTML structures used for ads.
        potential_containers = await page.query_selector_all(
            '.b_ad, li.b_algo.b_ads' # Common structural identifiers for Bing Ads
        )

        print(f"Found {len(potential_containers)} potential Bing ad containers.")

        for i, ad_element in enumerate(potential_containers):
            if len(ads) >= max_ads:
                break
            try:
                # Define all possible ad labels (English and Estonian)
                ad_labels = ["Ad", "Sponsored", "Reklaam", "Sponsoreeritud", "Sponsitud"]
                # Final verification using text content within the container
                is_ad_label_present = await ad_element.evaluate(
                    f"""
                    (element) => {{
                        const adLabels = {json.dumps(ad_labels)};
                        for (const label of adLabels) {{
                            if (element.innerText.includes(label)) {{
                                return true;
                            }}
                        }}
                        return false;
                    }}
                    """
                )

                if is_ad_label_present:
                    title_element = await ad_element.query_selector('h2 > a')
                    title_text = await title_element.inner_text() if title_element else 'N/A'

                    description_element = await ad_element.query_selector('.b_algoDescription, .b_text')
                    description_text = await description_element.inner_text() if description_element else 'N/A'

                    link_element = await ad_element.query_selector('a[href]')
                    link_href = await link_element.get_attribute('href') if link_element else 'N/A'

                    ads.append({
                        'source': 'Bing',
                        'keyword': keyword,
                        'title': title_text.strip(),
                        'description': description_text.strip(),
                        'link': link_href
                    })
                else:
                    # print(f"Element {i} skipped as no valid ad label found within its content.")
                    pass

            except Exception as e:
                print(f"Error parsing Bing ad element (index {i}): {e}")
                continue

    except Exception as e:
        print(f"Could not process Bing ads for '{keyword}': {e}")
    return ads


async def main():
    all_scraped_ads = []

    # Configure Playwright launch arguments for proxy and location
    launch_args = {
        "headless": CONFIG["headless"],
        "args": [
            "--lang=en-US", # Set browser language
            "--disable-features=InterestFeedContentSuggestions" # Reduce noise
        ]
    }
    if CONFIG["proxy_server"]:
        launch_args["proxy"] = {
            "server": CONFIG["proxy_server"],
            "username": CONFIG["proxy_username"],
            "password": CONFIG["proxy_password"]
        }
        print(f"Using proxy: {CONFIG['proxy_server']}")

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(**launch_args)

            # Set geolocation for Estonia (not always effective for search engines, proxy is better)
            context = await browser.new_context(
                locale="en-US", # Keep browser locale to English, as we explicitly search for labels
                timezone_id="Europe/Tallinn",
                geolocation={"latitude": 59.436962, "longitude": 24.753574}, # Tallinn coordinates
                permissions=["geolocation"]
            )
            page = await context.new_page()

            for keyword in CONFIG["keywords"]:
                print(f"\n--- Scraping ads for keyword: '{keyword}' ---")

                # Google
                print("Attempting Google search...")
                google_ads = await scrape_google_ads(page, keyword, CONFIG["max_ads_per_page"])
                if google_ads:
                    all_scraped_ads.extend(google_ads)
                    print(f"Found {len(google_ads)} Google ads for '{keyword}'")
                else:
                    print(f"No Google ads found for '{keyword}'")

                await asyncio.sleep(random.uniform(CONFIG["delay_between_searches_seconds"], CONFIG["delay_between_searches_seconds"] * 1.5))

                # Bing
                print("Attempting Bing search...")
                bing_ads = await scrape_bing_ads(page, keyword, CONFIG["max_ads_per_page"])
                if bing_ads:
                    all_scraped_ads.extend(bing_ads)
                    print(f"Found {len(bing_ads)} Bing ads for '{keyword}'")
                else:
                    print(f"No Bing ads found for '{keyword}'")

                await asyncio.sleep(random.uniform(CONFIG["delay_between_searches_seconds"], CONFIG["delay_between_searches_seconds"] * 1.5))

        except Exception as e:
            print(f"An unexpected error occurred during browser operation: {e}")
        finally:
            if browser:
                await browser.close()

    # Save results to a JSON file
    try:
        with open(CONFIG["output_file"], 'w', encoding='utf-8') as f:
            json.dump(all_scraped_ads, f, ensure_ascii=False, indent=4)
        print(f"\nScraping complete. Data saved to {CONFIG['output_file']}")
    except Exception as e:
        print(f"Error saving data to file: {e}")

if __name__ == "__main__":
    asyncio.run(main())
