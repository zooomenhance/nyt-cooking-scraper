import asyncio
import os
import csv
import json
import re
import ast
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

CSV_FILENAME = "nyt_recipes_index.csv"
ENHANCED_CSV = "nyt_recipes_index_enhanced.csv"

def clean_image_url(img_data):
    if not img_data or img_data == "N/A": return ""
    # If it's already a clean URL
    if img_data.startswith('http') and "'" not in img_data and "{" not in img_data:
        return img_data
    try:
        if img_data.startswith('{'):
            # Convert string representation of dict to real dict
            data = ast.literal_eval(img_data)
            if isinstance(data, dict):
                return data.get('url') or data.get('contentUrl') or ""
    except:
        # Fallback to regex if ast fails
        match = re.search(r'(https://static01.nyt.com/[^\s\'"]+)', img_data)
        if match: return match.group(1).rstrip('},').rstrip("'")
    return img_data

def extract_ratings_from_json(data, rating_lookup):
    """Recursively search for ratings in the JSON structure."""
    if isinstance(data, dict):
        if 'id' in data and 'ratings' in data and isinstance(data['ratings'], dict):
            recipe_id = str(data['id'])
            rating_lookup[recipe_id] = data['ratings']
        for key, value in data.items():
            extract_ratings_from_json(value, rating_lookup)
    elif isinstance(data, list):
        for item in data:
            extract_ratings_from_json(item, rating_lookup)

import sys

async def main(max_pages=50):
    if not os.path.exists(CSV_FILENAME):
        print("Error: Base CSV not found.")
        return

    all_recipes = []
    with open(CSV_FILENAME, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_recipes = list(reader)

    print(f"Loaded {len(all_recipes)} recipes. Scanning NYT for ratings...")
    rating_lookup = {} 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for category, base_url in MEAL_CATEGORIES.items():
            print(f"\n======= CATEGORY: {category} =======")
            page_num = 1
            empty_streak = 0
            while True:
                url = f"{base_url}?page={page_num}"
                context = await browser.new_context()
                page = await context.new_page()
                try:
                    print(f"  Indexing Page {page_num}...")
                    await page.goto(url, wait_until="load", timeout=60000)
                    
                    # Find __NEXT_DATA__ script tag
                    next_data_script = await page.query_selector('script#__NEXT_DATA__')
                    if next_data_script:
                        json_text = await next_data_script.inner_text()
                        try:
                            data = json.loads(json_text)
                            before_count = len(rating_lookup)
                            extract_ratings_from_json(data, rating_lookup)
                            added = len(rating_lookup) - before_count
                            print(f"    Collected {added} new ratings from JSON (Total: {len(rating_lookup)})")
                            
                            if added == 0:
                                empty_streak += 1
                            else:
                                empty_streak = 0
                        except Exception as e:
                            print(f"    JSON Parse Error: {e}")
                            empty_streak += 1
                    else:
                        print("    __NEXT_DATA__ not found on this page.")
                        empty_streak += 1
                    
                    # Check for "Load More" or if we should stop
                    if empty_streak >= 3 or page_num >= max_pages: 
                        print(f"  Finished {category} (empty streak or page limit reached).")
                        await context.close()
                        break
                    
                    page_num += 1
                    await context.close()
                except Exception as e:
                    print(f"    Error on {url}: {e}")
                    await context.close()
                    break
        await browser.close()

    print("\nProcessing final CSV updates...")
    enhanced_data = []
    for r in all_recipes:
        # Clean Image URL
        r['Image URL'] = clean_image_url(r.get('Image URL', ''))
        
        # Clean/Normalize URL
        url = r.get('URL')
        if not url:
            continue
            
        if url.startswith('/recipes/'): url = f"https://cooking.nytimes.com{url}"
        elif 'cooking.nytimes.com' not in url: url = f"https://cooking.nytimes.com/recipes/{url.lstrip('/')}"
        url = url.split('?')[0].replace('http://', 'https://').strip()
        r['URL'] = url
        
        # Extract ID and lookup ratings
        recipe_id = "0"
        match = re.search(r'/recipes/(\d+)', url)
        if match: recipe_id = match.group(1)
        
        rating_info = rating_lookup.get(recipe_id, {})
        # avgRating might be 0, 4.5, 5 etc. numRatings is count.
        r['Rating'] = rating_info.get('avgRating', 'N/A')
        r['Reviews'] = rating_info.get('numRatings', '0')
        enhanced_data.append(r)

    if enhanced_data:
        # Organize columns: Category, Title, Rating, Reviews, ...
        first_recipe = enhanced_data[0]
        keys = list(first_recipe.keys())
        
        # Remove Rating/Reviews if they were already there (to avoid duplicates)
        for col in ['Rating', 'Reviews']:
            if col in keys: keys.remove(col)
        
        # Insert them at the desired position
        keys.insert(2, 'Rating')
        keys.insert(3, 'Reviews')
            
        with open(ENHANCED_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(enhanced_data)
        
        # Backup old file and replace
        bak_file = CSV_FILENAME + ".bak"
        if os.path.exists(bak_file):
            try: os.remove(bak_file)
            except: pass
            
        if os.path.exists(CSV_FILENAME):
            os.rename(CSV_FILENAME, bak_file)
        os.rename(ENHANCED_CSV, CSV_FILENAME)
        print(f"Success! {CSV_FILENAME} is fully cleaned and enhanced.")
        print(f"Total recipes processed: {len(enhanced_data)}")
    else:
        print("No data to save.")

if __name__ == "__main__":
    max_p = 50
    if "--fast" in sys.argv:
        max_p = 5
        print("Fast mode enabled: Scraping only first 5 pages per category.")
    asyncio.run(main(max_pages=max_p))
