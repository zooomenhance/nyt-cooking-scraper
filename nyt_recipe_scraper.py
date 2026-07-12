import asyncio
import os
import re
import csv
import json
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Configuration
MEAL_CATEGORIES = {
    "Dinner": "https://cooking.nytimes.com/topics/dinner-recipes",
    "Breakfast": "https://cooking.nytimes.com/topics/breakfast",
    "Lunch": "https://cooking.nytimes.com/68861692-nyt-cooking/20404912-lunch-ideas",
    "Desserts": "https://cooking.nytimes.com/topics/desserts",
    "Appetizers": "https://cooking.nytimes.com/topics/appetizers",
    "Side Dishes": "https://cooking.nytimes.com/topics/side-dishes",
    "Drinks": "https://cooking.nytimes.com/topics/drink-recipes",
    "Newest": "https://cooking.nytimes.com/68861692-nyt-cooking/32998034-our-newest-recipes"
}

OUTPUT_DIR = "nyt_recipes_pdfs"
CSV_FILENAME = "nyt_recipes_index.csv"
CONCURRENT_TASKS = 3 

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")

def safe_save_csv(data_rows):
    """Attempt to save CSV with retries if file is locked."""
    if not data_rows: return
    for attempt in range(10):
        try:
            file_exists = os.path.isfile(CSV_FILENAME)
            with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data_rows[0].keys())
                if not file_exists: writer.writeheader()
                writer.writerows(data_rows)
            return
        except PermissionError:
            print(f"!!! Warning: CSV locked. Close Excel/Sheets! Retrying in 2s... (Attempt {attempt+1}/10)")
            time.sleep(2)
    print("!!! Error: Could not save CSV after 10 attempts. Progress may be lost.")

def extract_recipe_data(html_content, url, pdf_filename, category):
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script', type='application/ld+json')
    
    recipe_data = {
        "Category": category,
        "Title": "N/A",
        "Rating": "N/A",
        "Reviews": "0",
        "Ingredients": "N/A",
        "Method": "N/A",
        "Tags": "N/A",
        "Total Time": "N/A",
        "Yield": "N/A",
        "Image URL": "",
        "URL": url,
        "PDF Filename": pdf_filename
    }

    # Extract image from meta tags as fallback
    og_image = soup.find("meta", property="og:image")
    if og_image: recipe_data["Image URL"] = og_image.get("content", "")

    for script in scripts:
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get('@type') == 'Recipe':
                    recipe_data["Title"] = item.get("name", "N/A")
                    recipe_data["Ingredients"] = "; ".join(item.get("recipeIngredient", []))
                    instructions = item.get("recipeInstructions", [])
                    if isinstance(instructions, list):
                        steps = [s["text"] if isinstance(s, dict) and "text" in s else str(s) for s in instructions]
                        recipe_data["Method"] = " ".join(steps)
                    categories = item.get("recipeCategory", [])
                    if isinstance(categories, str): categories = [categories]
                    keywords = item.get("keywords", "")
                    if isinstance(keywords, str): keywords = keywords.split(",")
                    recipe_data["Tags"] = ", ".join(set(categories + keywords))
                    recipe_data["Total Time"] = item.get("totalTime", "N/A").replace("PT", "").lower()
                    recipe_data["Yield"] = item.get("recipeYield", "N/A")
                    # Prefer high-res image from JSON-LD
                    img = item.get("image")
                    if img:
                        if isinstance(img, list): recipe_data["Image URL"] = img[0]
                        elif isinstance(img, dict): recipe_data["Image URL"] = img.get("url", "")
                        else: recipe_data["Image URL"] = str(img)
                    return recipe_data
        except: continue
    
    if recipe_data["Title"] == "N/A":
        h1 = soup.find('h1')
        if h1: recipe_data["Title"] = h1.get_text().strip()
    return recipe_data

async def process_recipe(browser, url, category):
    context = await browser.new_context(java_script_enabled=False)
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="load", timeout=60000)
        html_content = await page.content()
        title_element = await page.query_selector('h1')
        title = await title_element.inner_text() if title_element else "Untitled"
        filename = f"{sanitize_filename(title)}.pdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            await page.pdf(path=filepath, format="A4", print_background=True)
            
        return extract_recipe_data(html_content, url, filename, category)
    except Exception as e:
        print(f"      Error processing {url}: {e}")
        return None
    finally:
        await context.close()

async def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    processed_urls = set()
    total_added = 0
    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            processed_urls = {row['URL'] for row in reader}
            print(f"Loaded {len(processed_urls)} existing recipes. Skipping duplicates.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for category, base_url in MEAL_CATEGORIES.items():
            print(f"\n======= STARTING CATEGORY: {category} =======")
            page_num = 1
            empty_page_count = 0
            
            while True:
                url = f"{base_url}?page={page_num}"
                print(f"--- Indexing {category} Page {page_num} ---")
                
                index_context = await browser.new_context()
                index_page = await index_context.new_page()
                try:
                    await index_page.goto(url, wait_until="load")
                    links = await index_page.query_selector_all('a[href^="/recipes/"]')
                    urls_to_process = []
                    for link in links:
                        href = await link.get_attribute('href')
                        if href and "/recipes/" in href:
                            full_url = f"https://cooking.nytimes.com{href.split('?')[0]}"
                            if full_url not in processed_urls:
                                urls_to_process.append(full_url)
                    
                    await index_context.close()
                    
                    if not urls_to_process:
                        empty_page_count += 1
                        if empty_page_count >= 2: break
                        page_num += 1
                        continue

                    empty_page_count = 0 
                    print(f"    Found {len(urls_to_process)} potential new recipes.")
                    
                    for i in range(0, len(urls_to_process), CONCURRENT_TASKS):
                        batch = urls_to_process[i:i + CONCURRENT_TASKS]
                        tasks = [process_recipe(browser, u, category) for u in batch]
                        results = await asyncio.gather(*tasks)
                        
                        new_rows = [r for r in results if r]
                        if new_rows:
                            safe_save_csv(new_rows)
                            for r in new_rows: 
                                processed_urls.add(r['URL'])
                                total_added += 1
                                print(f"    [SAVED] {r['Title']}")
                    
                    page_num += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error on {category} page {page_num}: {e}")
                    break

        await browser.close()
        print(f"\nScraping complete! Added {total_added} new recipes locally.")

if __name__ == "__main__":
    asyncio.run(main())
