import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://cooking.nytimes.com/68861692-nyt-cooking/32998034-our-newest-recipes?page=2"
        print(f"Loading {url}...")
        await page.goto(url, wait_until="networkidle")
        links = await page.query_selector_all('a[href^="/recipes/"]')
        print(f"Found {len(links)} recipe links.")
        for link in links[:5]:
            href = await link.get_attribute('href')
            print(f"  {href}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
