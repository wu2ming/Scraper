
import asyncio
import os
from dotenv import load_dotenv
from scrapybara import Scrapybara
from playwright.async_api import async_playwright

import json

load_dotenv()
api_key = os.getenv("SCRAPYBARA_API_KEY")

async def get_scrapybara_browser():
    client = Scrapybara(api_key=api_key)
    instance = client.start_browser()
    return instance


async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    :args:
    instance: the scrapybara instance to use
    url: the initial url to navigate to

    :desc:
    this function navigates to {url}. then, it will collect the detailed
    data for each menu item in the store and return it.

    (hint: click a menu item, open dev tools -> network tab -> filter for
            "https://www.doordash.com/graphql/itemPage?operation=itemPage")

    one way to do this is to scroll through the page and click on each menu
    item.

    determine the most efficient way to collect this data.

    :returns:
    a list of menu items on the page, represented as dictionaries
    """
    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()

        await page.goto(start_url)

        # browser automation ...
        menu_items = []

        overlay = await page.query_selector("div[data-testid='turnstile/overlay']")
        if overlay:
            await page.evaluate("document.querySelector('div[data-testid=\"turnstile/overlay\"]').remove()")

    
        containers = await page.query_selector_all("div[data-testid='VirtualGridContainer']")
        print (len(containers))
            
        # Scroll to conatiner to load items
        for container in containers:
            print("Entering Container")
            await container.scroll_into_view_if_needed()
            await asyncio.sleep(1) 

            menu_buttons = await container.query_selector_all("div[data-testid='MenuItem']")
            print("Scraping menu items")
            for button in menu_buttons:
                print("Clicking menu item")
                # click on menu item and wait for API response
                async with page.expect_response(lambda response: "graphql/itemPage" in response.url) as response_info:
                    await button.click() 

                response = await response_info.value
                json_data = await response.json()
                # Extract menu item details from API response
                item_data = json_data.get("data", {}).get("itemPage", {}).get("itemHeader", {})
                menu_items.append({
                    "name": item_data.get("name"),
                    "description": item_data.get("description"),
                    "image_url": item_data.get("imageUrl"),
                })
                print(f"Scraped {item_data.get('name')}")

                # Close modal before clicking next item
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
    
        await browser.close()

    #debugging
    with open("menu_items.json", "w") as f:
        json.dump(menu_items, f, indent=2)
    return menu_items


async def main():
    instance = await get_scrapybara_browser()
    try:
        await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
    finally:
        # Be sure to close the browser instance after you're done!
        instance.stop()


if __name__ == "__main__":
    asyncio.run(main())
