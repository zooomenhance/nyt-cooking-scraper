import os
import csv
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Heuristics for classifying ingredients into supermarket aisles
CATEGORIES = ["Produce", "Meat & Seafood", "Dairy & Eggs", "Canned Goods & Grains", "Pantry & Spices", "Other / Miscellaneous"]

def parse_markdown_plan(plan_path):
    if not os.path.exists(plan_path):
        print(f"Error: {plan_path} not found.")
        return None
        
    with open(plan_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    return lines

def get_recipe_images(csv_path, selected_titles):
    images = {}
    if not os.path.exists(csv_path):
        return images
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row['Title']
            if title in selected_titles:
                images[title] = row.get('Image URL', '')
    return images

def build_html_email(selected_meals, shopping_list, recipe_images):
    html = """
    <html>
    <head>
        <style>
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333333; background-color: #f7f9fa; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e1e8ed; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .header { background-color: #ff3b30; color: #ffffff; padding: 30px 20px; text-align: center; }
            .header h1 { margin: 0; font-size: 24px; font-weight: bold; }
            .content { padding: 30px 25px; }
            .recipe-card { margin-bottom: 30px; border-bottom: 1px solid #f1f2f6; padding-bottom: 25px; }
            .recipe-card:last-child { border-bottom: none; }
            .recipe-title { font-size: 20px; font-weight: bold; color: #1c1c1e; margin: 0 0 10px 0; }
            .recipe-meta { font-size: 13px; color: #8e8e93; margin-bottom: 15px; }
            .recipe-img { width: 100%; max-height: 320px; object-fit: cover; border-radius: 8px; margin-bottom: 15px; border: 1px solid #e5e5ea; }
            .recipe-link { display: inline-block; background-color: #ff3b30; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: 600; margin-right: 10px; }
            .recipe-link.drive { background-color: #007aff; }
            .shopping-section { background-color: #f2f2f7; padding: 25px; border-radius: 8px; margin-top: 30px; }
            .shopping-section h2 { margin-top: 0; font-size: 18px; color: #1c1c1e; border-bottom: 2px solid #e5e5ea; padding-bottom: 8px; }
            .shopping-category { margin-bottom: 20px; }
            .shopping-category h3 { font-size: 14px; text-transform: uppercase; color: #8e8e93; letter-spacing: 0.5px; margin: 0 0 10px 0; }
            .shopping-item { margin: 6px 0; font-size: 14px; display: flex; align-items: flex-start; }
            .checkbox { margin-right: 8px; margin-top: 4px; }
            .recipe-tags { font-size: 11px; font-style: italic; color: #c7c7cc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🗓️ Your Weekly Meal Plan</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Ingredient-Optimized Shopping List & Recipes</p>
            </div>
            <div class="content">
                <h2>🍲 This Week's Menu</h2>
    """
    
    # Add Recipes Cards
    for idx, r in enumerate(selected_meals):
        img_tag = f'<img class="recipe-img" src="{recipe_images.get(r["Title"], "")}" alt="{r["Title"]}">' if recipe_images.get(r["Title"]) else ''
        html += f"""
                <div class="recipe-card">
                    <h3 class="recipe-title">{idx+1}. {r['Title']}</h3>
                    <div class="recipe-meta">Rating: {r['Rating']} ⭐ | Prep Time: {r['Total Time']} | Yield: {r['Yield']}</div>
                    {img_tag}
                    <div style="margin-top: 12px;">
                        <a class="recipe-link" href="{r['URL']}" target="_blank">View on NYT Cooking</a>
                        <a class="recipe-link drive" href="{r['DriveLink']}" target="_blank">Open PDF on Google Drive</a>
                    </div>
                </div>
        """
        
    # Add Shopping List Section
    html += """
                <div class="shopping-section">
                    <h2>🛒 Optimized Grocery Shopping List</h2>
                    <p style="font-size: 11px; color: #8e8e93; margin-top: -8px; margin-bottom: 20px;">Standard pantry staples (salt, pepper, oil, butter, garlic, onion) are excluded.</p>
    """
    
    for category, items in shopping_list.items():
        if items:
            html += f"""
                    <div class="shopping-category">
                        <h3>{category}</h3>
            """
            for item in items:
                html += f"""
                        <div class="shopping-item">
                            <input class="checkbox" type="checkbox">
                            <div><strong>{item['detail']}</strong> <span class="recipe-tags">(for: {', '.join(item['recipes'])})</span></div>
                        </div>
                """
            html += "</div>"
            
    html += """
                </div>
            </div>
            <div style="background-color: #e5e5ea; text-align: center; padding: 15px; font-size: 11px; color: #8e8e93;">
                Sent to you by Antigravity AI Coding Assistant. Enjoy your meals!
            </div>
        </div>
    </body>
    </html>
    """
    return html

def main():
    parser = argparse.ArgumentParser(description="Send your meal plan via email.")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--gmail-user", required=True, help="Your Gmail address")
    parser.add_argument("--gmail-app-password", required=True, help="Your 16-character Gmail App Password")
    parser.add_argument("--csv", default="nyt_recipes_index.csv", help="Path to NYT cooking database index CSV")
    
    args = parser.parse_args()
    
    # 1. Parse weekly_meal_plan.md to extract recipes and shopping list
    if not os.path.exists("weekly_meal_plan.md"):
        print("Error: weekly_meal_plan.md not found. Run meal_planner.py first.")
        return
        
    selected_meals = []
    shopping_list = {c: [] for c in CATEGORIES}
    
    current_category = None
    
    with open("weekly_meal_plan.md", 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract recipes from the markdown table
    # Example table row: | **Recipe Title** | 5 ⭐ | Dinner | 45m | 4 to 6 servings | [Google Drive Link](url) / [Web](url) |
    rows = re.findall(r'\|\s*\*\*(.*?)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*\[Google Drive Link\]\((.*?)\)\s*/\s*\[Web\]\((.*?)\)\s*\|', content)
    for r in rows:
        selected_meals.append({
            "Title": r[0].strip(),
            "Rating": r[1].replace("⭐", "").strip(),
            "Category": r[2].strip(),
            "Total Time": r[3].strip(),
            "Yield": r[4].strip(),
            "DriveLink": r[5].strip(),
            "URL": r[6].strip()
        })
        
    # Extract shopping list items grouped by section
    lines = content.split('\n')
    for line in lines:
        if line.startswith("### 🟢 "):
            current_category = line.replace("### 🟢 ", "").strip()
        elif line.startswith("- [ ] ") and current_category in shopping_list:
            # Parse item: - [ ] **1/3 cup sun-dried tomatoes** *(used in: *Recipe1*, *Recipe2*)*
            match = re.search(r'-\s*\[\s*\]\s*\*\*(.*?)\*\*\s*(?:\*\(used in:\s*(.*?)\)\*)?', line)
            if match:
                detail = match.group(1).strip()
                recipes_raw = match.group(2) if match.group(2) else ""
                recipes = [r.replace("*", "").strip() for r in recipes_raw.split(',') if r.strip()]
                shopping_list[current_category].append({
                    "detail": detail,
                    "recipes": recipes
                })

    titles = [m['Title'] for m in selected_meals]
    print(f"Parsed {len(selected_meals)} recipes: {', '.join(titles)}")
    
    # 2. Get recipe images
    recipe_images = get_recipe_images(args.csv, titles)
    
    # 3. Build HTML Body
    html_body = build_html_email(selected_meals, shopping_list, recipe_images)
    
    # 4. Connect to SMTP and send
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🍲 Your Weekly Meal Plan & Shopping List"
    msg['From'] = args.gmail_user
    msg['To'] = args.to
    
    msg.attach(MIMEText(html_body, 'html'))
    
    print(f"Connecting to Gmail SMTP server for {args.gmail_user}...")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(args.gmail_user, args.gmail_app_password)
        server.sendmail(args.gmail_user, args.to, msg.as_string())
        server.close()
        print(f"Success! Email sent successfully to: {args.to}")
    except Exception as e:
        print(f"!!! Error sending email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
