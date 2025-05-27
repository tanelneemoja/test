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
    "max_ads_per_page": int(os.environ.get("MAX_ADS_PER_page", 5)),
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

        # Broad selection of elements that could be ad containers
        potential_containers = await page.query_selector_all(
            'div[data-text-ad], .uEac3e, div[jsaction^="h.HqcS9a"], '
            'div[jscontroller="e4F63e"], div.dGdCNb, div.vdBfKf, .ads-ad, .GxGvSe' # Added .GxGvSe - another common Google ad container
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
                            }}
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

                    description_element = await ad_element.query_selector('div[data-sncf], div[role="text"], .VaQj8d, .VwiC3b')
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
                    pass

            except Exception as e:
                print(f"Error parsing Google ad element (index {i}): {e}")
                continue

    except Exception as e:
        print(f"Could not process Google ads for '{keyword}': {e}")
    return ads

async def scrape_bing_ads(page, keyword, max_ads):
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
        potential_containers = await page.query_selector_all(
            '.b_ad, li.b_algo.b_ads'
        )

        print(f"Found {len(potential_containers)} potential Bing ad containers.")

        for i, ad_element in enumerate(potential_containers):
            if len(ads) >= max_ads:
                break
            try:
                ad_labels = ["Ad", "Sponsored", "Reklaam", "Sponsoreeritud", "Sponsitud"]
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
                    pass

            except Exception as e:
                print(f"Error parsing Bing ad element (index {i}): {e}")
                continue

    except Exception as e:
        print(f"Could not process Bing ads for '{keyword}': {e}")
    return ads


async def main():
    all_scraped_ads = []

    launch_args = {
        "headless": CONFIG["headless"],
        "args": [
            "--lang=en-US",
            "--disable-features=InterestFeedContentSuggestions"
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

            context = await browser.new_context(
                locale="en-US",
                timezone_id="Europe/Tallinn",
                geolocation={"latitude": 59.436962, "longitude": 24.753574},
                permissions=["geolocation"]
            )
            page = await context.new_page()

            for keyword in CONFIG["keywords"]:
                print(f"\n--- Scraping ads for keyword: '{keyword}' ---")

                print("Attempting Google search...")
                google_ads = await scrape_google_ads(page, keyword, CONFIG["max_ads_per_page"])
                if google_ads:
                    all_scraped_ads.extend(google_ads)
                    print(f"Found {len(google_ads)} Google ads for '{keyword}'")
                else:
                    print(f"No Google ads found for '{keyword}'")

                await asyncio.sleep(random.uniform(CONFIG["delay_between_searches_seconds"], CONFIG["delay_between_searches_seconds"] * 1.5))

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

    try:
        with open(CONFIG["output_file"], 'w', encoding='utf-8') as f:
            json.dump(all_scraped_ads, f, ensure_ascii=False, indent=4)
        print(f"\nScraping complete. Data saved to {CONFIG['output_file']}")
    except Exception as e:
        print(f"Error saving data to file: {e}")

if __name__ == "__main__":
    asyncio.run(main())
