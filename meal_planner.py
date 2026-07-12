import os
import csv
import re
import sys
import argparse

# Common pantry items that the user likely has or doesn't need to shop for specifically
PANTRY_ITEMS = {
    "salt", "kosher salt", "black pepper", "pepper", "olive oil", "vegetable oil", 
    "canola oil", "coconut oil", "butter", "unsalted butter", "water", "sugar", 
    "granulated sugar", "brown sugar", "flour", "all-purpose flour", "garlic", 
    "garlic cloves", "onion", "yellow onion", "white onion", "red onion", "ice", 
    "cornstarch", "baking powder", "baking soda", "vanilla extract", "black pepper to taste",
    "kosher salt and black pepper", "salt and black pepper", "salt and pepper", "olive oil for serving",
    "kosher salt and freshly ground black pepper", "freshly ground black pepper", "ground black pepper"
}

# Heuristics for classifying ingredients into supermarket aisles
CATEGORIES = {
    "Produce": [
        "spinach", "asparagus", "tomato", "tomatoes", "leek", "leeks", "ginger", 
        "lemon", "lime", "parsley", "cilantro", "mint", "basil", "brussels sprout", 
        "brussels sprouts", "carrot", "carrots", "celery", "jalapeño", "cabbage", 
        "potatoes", "potato", "yam", "yams", "greens", "kale", "chard", "avocado", 
        "cucumber", "peaches", "peach", "zucchini", "berries", "blueberry", "strawberries", 
        "strawberry", "onion", "garlic", "shallot", "shallots", "scallion", "scallions",
        "coriander", "rosemary", "thyme", "chives", "dill", "oregano", "mushrooms", 
        "mushroom", "peppers", "bell pepper", "bell peppers", "peapods", "peas", "squash",
        "eggplant", "cauliflower", "broccoli", "cabbage", "lettuce", "salad", "arugula"
    ],
    "Meat & Seafood": [
        "chicken", "beef", "pork", "turkey", "shrimp", "fish", "meatballs", "sausage", 
        "bacon", "salmon", "tuna", "lamb", "steak", "ground beef", "ground chicken", 
        "ground turkey", "pancetta", "ham", "prawns", "cod", "halibut", "scallops"
    ],
    "Dairy & Eggs": [
        "eggs", "egg", "feta", "parmesan", "cheddar", "cheese", "milk", "yogurt", 
        "cream", "ricotta", "mozzarella", "butter", "sour cream", "pecorino", "goat cheese",
        "halloumi", "mascarpone", "heavy cream", "buttermilk", "cheese blend"
    ],
    "Canned Goods & Grains": [
        "chickpeas", "beans", "coconut milk", "broth", "stock", "pasta", "gnocchi", 
        "rice", "cassava", "lentils", "noodles", "tortillas", "pita", "bread", "canned tomato",
        "canned tomatoes", "tomato paste", "kidney beans", "black beans", "cannellini", 
        "white beans", "couscous", "quinoa", "barley", "farro", "baguette"
    ],
    "Pantry & Spices": [
        "oil", "honey", "vinegar", "soy sauce", "fish sauce", "turmeric", "cumin", 
        "paprika", "cinnamon", "oregano", "chili powder", "nutmeg", "chile", "flour", 
        "sugar", "salt", "pepper", "curry", "sesame oil", "rice vinegar", "maple syrup",
        "mustard", "mayonnaise", "hot sauce", "tahini", "olive oil", "red-pepper flakes",
        "cayenne", "coriander seed", "cardamom", "ginger powder", "clove powder", "bay leaves"
    ]
}

MEASUREMENTS = r'\b(cup|cups|teaspoon|teaspoons|tsp|tablespoon|tablespoons|tbsp|clove|cloves|pound|pounds|lb|lbs|ounces|ounce|oz|can|cans|g|grams|bunch|piece|pieces|pinch|pinches|slice|slices|container|containers|head|heads|stalk|stalks|bag|bags|package|packages|jar|jars|bottle|bottles|gram|kilogram|kg|ml|liter|liters|l)\b'
DESCRIPTORS = r'\b(large|medium|small|chopped|diced|minced|sliced|peeled|finely|grated|kosher|ground|freshly|fresh|dried|packed|extra-virgin|unsalted|unseasoned|coarsely|thinly|halved|trimmed|drained|rinsed|shredded|crumbled|finely chopped|smashed|clove|cloves|to taste|for serving|optional|such as Diamond Crystal|peeled, smashed and minced|cooked|raw|warm|cold|hot|sliced into|cut into|cut)\b'

def normalize_ingredient(ing_text):
    # Remove text in parentheses (e.g. "1 (15-ounce) can chickpeas" -> "1 can chickpeas")
    primary = re.sub(r'\(.*?\)', '', ing_text)
    
    # Split by comma to get primary ingredient (e.g. "1 bunch Swiss chard, stems removed" -> "1 bunch Swiss chard")
    primary = primary.split(',')[0].strip().lower()
    
    # Remove numbers and fraction characters
    primary = re.sub(r'[\d\s½⅓¼¾⅛⅝%½\-]*', '', primary)
    
    # Remove measurements and descriptors
    primary = re.sub(MEASUREMENTS, '', primary)
    primary = re.sub(DESCRIPTORS, '', primary)
    
    # Clean up double spacing or leftover symbols
    primary = re.sub(r'\s+', ' ', primary).strip()
    
    # Strip common plural 's' at the end for basic matching (stemming)
    if len(primary) > 3 and primary.endswith('s') and not primary.endswith('ss'):
        primary = primary[:-1]
        
    return primary

def classify_ingredient(ing_name):
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            # Match singular/plural stemming
            stem = keyword[:-1] if keyword.endswith('s') and len(keyword) > 3 else keyword
            if stem in ing_name:
                return category
    return "Other / Miscellaneous"

def load_recipes(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        sys.exit(1)
        
    recipes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse raw ingredients list
            raw_ingredients = [i.strip() for i in row['Ingredients'].split(';') if i.strip()]
            
            # Normalize and clean ingredients
            normalized_list = []
            shopping_list = []
            for ing in raw_ingredients:
                norm = normalize_ingredient(ing)
                if norm:
                    normalized_list.append(norm)
                    if norm not in PANTRY_ITEMS:
                        shopping_list.append(norm)
                        
            row['parsed_ingredients'] = raw_ingredients
            row['normalized_ingredients'] = normalized_list
            row['shopping_ingredients'] = list(set(shopping_list))
            recipes.append(row)
    return recipes

def match_criteria(recipe, category, include_kws, exclude_kws, min_rating):
    # Ignore empty recipes or non-recipe guides
    if not recipe['Ingredients'].strip() or recipe['Method'].strip().lower() == "n/a":
        return False

    # Filter by category
    if category and category.lower() != "all":
        if recipe['Category'].lower() != category.lower():
            # Fallback check in Tags
            tags = [t.strip().lower() for t in recipe['Tags'].split(',') if t.strip()]
            if category.lower() not in tags:
                return False
                
    # Filter by rating
    try:
        rating = float(recipe['Rating']) if recipe['Rating'] != 'N/A' else 0
        if rating < min_rating:
            return False
    except ValueError:
        return False
        
    # Check exclusion keywords
    title_and_ing = (recipe['Title'] + " " + recipe['Ingredients'] + " " + recipe['Tags']).lower()
    for kw in exclude_kws:
        if kw.strip().lower() in title_and_ing:
            return False
            
    # Check inclusion keywords
    if include_kws:
        match_found = False
        for kw in include_kws:
            if kw.strip().lower() in title_and_ing:
                match_found = True
                break
        if not match_found:
            return False
            
    return True

def plan_meals(recipes, num_meals, include_kws=None):
    if not recipes:
        return []
        
    import math
    
    # Heuristic baseline quality score
    def get_quality_score(r):
        try:
            rating = float(r['Rating']) if r['Rating'] != 'N/A' else 0
            reviews = int(r['Reviews']) if r['Reviews'] != 'N/A' else 0
            return (rating, reviews)
        except ValueError:
            return (0, 0)
            
    sorted_recipes = sorted(recipes, key=get_quality_score, reverse=True)
    
    # Greedy Selection Algorithm
    selected = [sorted_recipes[0]] # Start with the highest quality matching recipe
    
    while len(selected) < num_meals and len(selected) < len(sorted_recipes):
        # Build union of shopping ingredients already selected
        current_shopping_union = set()
        for r in selected:
            current_shopping_union.update(r['shopping_ingredients'])
            
        best_next_recipe = None
        max_utility = -float('inf')
        
        # Select candidate that maximizes combined utility
        for r in sorted_recipes:
            if r in selected:
                continue
                
            recipe_ingredients = set(r['shopping_ingredients'])
            new_ingredients = recipe_ingredients - current_shopping_union
            num_new = len(new_ingredients)
            
            # Popularity factor based on reviews count and rating
            rating, reviews = get_quality_score(r)
            # Log scale: 0 for 0 reviews, ~6.9 for 1000 reviews, ~10.3 for 30000 reviews
            popularity_factor = math.log(reviews + 1) * (rating / 5.0)
            
            # Balance: -1.5 utility per new ingredient, +1.0 utility per log-popularity unit
            utility = -1.5 * num_new + 1.0 * popularity_factor
            
            # Apply diversity penalty for multiple inclusion keywords (OR matching)
            # e.g., if chicken thighs and ground turkey are specified, ensure we balance both.
            if include_kws and len(include_kws) > 1:
                title_and_ing = (r['Title'] + " " + r['Ingredients'] + " " + r['Tags']).lower()
                for kw in include_kws:
                    kw_clean = kw.strip().lower()
                    if kw_clean in title_and_ing:
                        # Count how many of the currently selected recipes contain this keyword
                        match_count = sum(1 for sel_r in selected if kw_clean in (sel_r['Title'] + " " + sel_r['Ingredients'] + " " + sel_r['Tags']).lower())
                        # Apply a penalty of 4.0 per existing matching recipe in selection
                        # This balances different proteins/ingredients beautifully
                        utility -= 4.0 * match_count
            
            if utility > max_utility:
                max_utility = utility
                best_next_recipe = r
                    
        if best_next_recipe:
            selected.append(best_next_recipe)
        else:
            break
            
    return selected

def generate_shopping_list(selected_recipes):
    shopping_items = {}
    
    # Gather raw ingredients and normalize them, mapping back to which recipes use them
    for recipe in selected_recipes:
        title = recipe['Title']
        raw_ings = recipe['parsed_ingredients']
        norm_ings = recipe['normalized_ingredients']
        
        for raw, norm in zip(raw_ings, norm_ings):
            if norm in PANTRY_ITEMS:
                continue
                
            if norm not in shopping_items:
                shopping_items[norm] = {
                    "raw_list": [],
                    "recipes": []
                }
            
            # Format raw detail
            shopping_items[norm]["raw_list"].append(raw)
            if title not in shopping_items[norm]["recipes"]:
                shopping_items[norm]["recipes"].append(title)
                
    # Classify shopping items
    classified = {}
    for norm, data in shopping_items.items():
        category = classify_ingredient(norm)
        if category not in classified:
            classified[category] = []
            
        # Select the most detailed raw description to show as shopping detail
        detailed_raw = max(data["raw_list"], key=len)
        classified[category].append({
            "name": norm,
            "detail": detailed_raw,
            "recipes": data["recipes"]
        })
        
    return classified

def main():
    parser = argparse.ArgumentParser(description="Generate an ingredient-optimized weekly meal plan.")
    parser.add_argument("--meals", type=int, default=3, help="Number of meals to plan (default: 3)")
    parser.add_argument("--category", type=str, default="Dinner", help="Meal category or Tag to filter by (default: Dinner, use 'all' for any)")
    parser.add_argument("--include", type=str, default="", help="Comma-separated ingredients or keywords to include")
    parser.add_argument("--exclude", type=str, default="", help="Comma-separated ingredients or keywords to exclude")
    parser.add_argument("--min-rating", type=float, default=4.0, help="Minimum recipe rating (default: 4.0)")
    parser.add_argument("--csv", type=str, default="nyt_recipes_index.csv", help="Path to NYT cooking database index CSV")
    
    args = parser.parse_args()
    
    include_kws = [k.strip() for k in args.include.split(',') if k.strip()]
    exclude_kws = [k.strip() for k in args.exclude.split(',') if k.strip()]
    
    print(f"Loading recipes from {args.csv}...")
    all_recipes = load_recipes(args.csv)
    print(f"Loaded {len(all_recipes)} recipes.")
    
    # Filter candidates
    candidates = [r for r in all_recipes if match_criteria(r, args.category, include_kws, exclude_kws, args.min_rating)]
    print(f"Found {len(candidates)} candidates matching criteria (Category: '{args.category}', Min Rating: {args.min_rating}+, Include: {include_kws}, Exclude: {exclude_kws}).")
    
    if not candidates:
        print("No recipes found matching your preferences. Try broadening your criteria.")
        return
        
    # Generate plan
    selected_meals = plan_meals(candidates, args.meals, include_kws)
    
    if not selected_meals:
        print("Failed to generate plan.")
        return
        
    # Generate shopping list
    shopping_list = generate_shopping_list(selected_meals)
    
    # Generate markdown file and console print
    markdown_content = []
    markdown_content.append(f"# 🗓️ Weekly Meal Plan & Shopping List")
    markdown_content.append(f"*Generated based on ingredient similarity optimization*")
    markdown_content.append(f"\n## 🍲 Selected Recipes ({len(selected_meals)} meals)")
    
    markdown_content.append("| Recipe | Rating | Category | Cook Time | Yield | PDF / Link |")
    markdown_content.append("| :--- | :---: | :--- | :---: | :---: | :---: |")
    
    for r in selected_meals:
        # Create links to local pdf and web url
        pdf_path = f"nyt_recipes_pdfs/{r['PDF Filename']}"
        link_str = f"[PDF]({pdf_path}) / [Web]({r['URL']})"
        markdown_content.append(f"| **{r['Title']}** | {r['Rating']} ⭐ | {r['Category']} | {r['Total Time']} | {r['Yield']} | {link_str} |")
        
    markdown_content.append("\n## 🛒 Optimized Shopping List")
    markdown_content.append("> [!TIP]\n> Standard pantry staples like salt, pepper, olive oil, butter, garlic, and onions have been automatically excluded from the list.")
    
    for category in ["Produce", "Meat & Seafood", "Dairy & Eggs", "Canned Goods & Grains", "Pantry & Spices", "Other / Miscellaneous"]:
        if category in shopping_list and shopping_list[category]:
            markdown_content.append(f"\n### 🟢 {category}")
            for item in sorted(shopping_list[category], key=lambda x: x['name']):
                recipes_str = ", ".join([f"*{r}*" for r in item['recipes']])
                markdown_content.append(f"- [ ] **{item['detail']}** *(used in: {recipes_str})*")
                
    markdown_content.append("\n## 📖 Prep Instructions Reference")
    for idx, r in enumerate(selected_meals):
        markdown_content.append(f"\n### {idx+1}. {r['Title']}")
        markdown_content.append(f"> **Yield**: {r['Yield']} | **Time**: {r['Total Time']}")
        markdown_content.append(f"\n**Ingredients Details**:")
        for ing in r['parsed_ingredients']:
            markdown_content.append(f"- {ing}")
        markdown_content.append(f"\n**Method**:\n{r['Method']}")
        
    plan_filename = "weekly_meal_plan.md"
    with open(plan_filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(markdown_content))
        
    print(f"\nSuccess! Meal plan generated and saved to: {plan_filename}")
    print("\n--- MEAL PLAN SUMMARY ---")
    for idx, r in enumerate(selected_meals):
        print(f"{idx+1}. {r['Title']} ({r['Rating']} stars, {r['Total Time']})")

if __name__ == "__main__":
    main()
