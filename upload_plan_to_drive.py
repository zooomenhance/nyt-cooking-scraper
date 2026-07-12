import os
import re
import pickle
import csv
import io
import datetime
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

TOKEN_FILE = 'token.pickle'
DRIVE_FOLDER_ID = '1L9UoykuM2oeYvVl5AtLtcoHEs45CtcEz'
CSV_FILENAME = 'nyt_recipes_index.csv'
PLAN_FILE = 'weekly_meal_plan.md'

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            return pickle.load(token)
    return None

def get_start_of_week_date():
    # If today is Sunday (6), next Monday is tomorrow
    # Otherwise, Monday of the current week
    today = datetime.date.today()
    if today.weekday() == 6:
        monday = today + datetime.timedelta(days=1)
    else:
        monday = today - datetime.timedelta(days=today.weekday())
    return monday.strftime("%y%m%d")

def get_or_create_meal_plans_folder(drive_service):
    q = f"name = 'Meal Plans' and mimeType = 'application/vnd.google-apps.folder' and '{DRIVE_FOLDER_ID}' in parents and trashed = false"
    results = drive_service.files().list(q=q, fields="files(id)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    
    folder_metadata = {
        'name': 'Meal Plans',
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [DRIVE_FOLDER_ID]
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    print(f"Created new folder 'Meal Plans' on Google Drive (ID: {folder['id']})")
    return folder['id']

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

def parse_meal_plan():
    if not os.path.exists(PLAN_FILE):
        print(f"Error: {PLAN_FILE} not found.")
        return None, None, None
        
    with open(PLAN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    selected_meals = []
    shopping_list = {}
    
    # Extract recipes from table
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
        
    # Extract shopping list categories
    lines = content.split('\n')
    current_category = None
    for line in lines:
        if line.startswith("### 🟢 "):
            current_category = line.replace("### 🟢 ", "").strip()
            shopping_list[current_category] = []
        elif line.startswith("- [ ] ") and current_category:
            match = re.search(r'-\s*\[\s*\]\s*\*\*(.*?)\*\*\s*(?:\*\(used in:\s*(.*?)\)\*)?', line)
            if match:
                detail = match.group(1).strip()
                recipes_raw = match.group(2) if match.group(2) else ""
                recipes = [r.replace("*", "").strip() for r in recipes_raw.split(',') if r.strip()]
                shopping_list[current_category].append({
                    "detail": detail,
                    "recipes": recipes
                })
                
    # Extract step-by-step instructions
    instructions_html = ""
    instructions_started = False
    in_list = False
    recipe_count = 0
    
    for line in lines:
        if line.startswith("## 📖 Prep Instructions Reference"):
            instructions_started = True
            instructions_html += '<div style="page-break-before: always;"><h2>📖 Prep Instructions Reference</h2></div>'
            continue
        if not instructions_started:
            continue
            
        if line.startswith("### "):
            if in_list:
                instructions_html += "</ul>"
                in_list = False
            # Close previous recipe's page-break div
            if recipe_count > 0:
                instructions_html += "</div>"
                
            recipe_title = line.replace("### ", "").strip()
            recipe_title = re.sub(r'^\d+\.\s*', '', recipe_title)
            # Wrap each recipe in a page break div
            instructions_html += f'<div style="page-break-before: always;"><h3>{recipe_title}</h3>'
            recipe_count += 1
        elif line.startswith("> **Yield**"):
            meta = line.replace("> ", "").strip()
            instructions_html += f"<p><em>{meta}</em></p>"
        elif line.startswith("**Ingredients Details**:") or line.startswith("**Method**:") or line.startswith("Ingredients Details:") or line.startswith("Method:"):
            if in_list:
                instructions_html += "</ul>"
                in_list = False
            instructions_html += f"<p><strong>{line.replace('**', '').strip()}</strong></p>"
        elif line.startswith("- "):
            if not in_list:
                instructions_html += "<ul>"
                in_list = True
            instructions_html += f"<li>{line.replace('- ', '').strip()}</li>"
        elif line.strip():
            if in_list:
                instructions_html += "</ul>"
                in_list = False
            # Clean up markdown formatting inside paragraphs
            clean_line = line.strip().replace("**", "")
            instructions_html += f"<p>{clean_line}</p>"
            
    if in_list:
        instructions_html += "</ul>"
    if recipe_count > 0:
        instructions_html += "</div>"
        
    return selected_meals, shopping_list, instructions_html

def build_html_document(selected_meals, shopping_list, recipe_images, instructions_html):
    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Arial', sans-serif; line-height: 1.5; color: #333333; }
            h1 { color: #ff3b30; border-bottom: 2px solid #ff3b30; padding-bottom: 10px; }
            h2 { color: #1c1c1e; border-bottom: 1px solid #e5e5ea; padding-bottom: 5px; margin-top: 30px; }
            h3 { color: #007aff; margin-top: 20px; margin-bottom: 5px; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            th, td { border: 1px solid #e5e5ea; padding: 8px; text-align: left; font-size: 13px; }
            th { background-color: #f2f2f7; font-weight: bold; }
            .shopping-category { margin-bottom: 15px; }
            .shopping-item { margin: 4px 0; font-size: 13px; }
            .recipe-tags { font-size: 11px; font-style: italic; color: #8e8e93; }
            .instruction-section { font-size: 13px; }
        </style>
    </head>
    <body>
        <h1>🗓️ Weekly Meal Plan & Shopping List</h1>
        <p><em>Generated based on ingredient similarity optimization from your NYT Cooking database</em></p>
        
        <h2>🍲 This Week's Menu</h2>
        <table>
            <thead>
                <tr>
                    <th>Recipe</th>
                    <th>Rating</th>
                    <th>Category</th>
                    <th>Cook Time</th>
                    <th>Yield</th>
                    <th>Links</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for r in selected_meals:
        html += f"""
                <tr>
                    <td><strong>{r['Title']}</strong></td>
                    <td>{r['Rating']} ⭐</td>
                    <td>{r['Category']}</td>
                    <td>{r['Total Time']}</td>
                    <td>{r['Yield']}</td>
                    <td><a href="{r['DriveLink']}">PDF Guide</a> / <a href="{r['URL']}">NYT Link</a></td>
                </tr>
        """
        
    html += """
            </tbody>
        </table>
    """
    
    # Recipe details with slightly larger images (280x280 px)
    html += "<h2>📸 Recipe Photos</h2>"
    html += '<table style="border: none; width: 100%;">'
    for i in range(0, len(selected_meals), 2):
        html += '<tr style="border: none;">'
        
        # Left cell
        r1 = selected_meals[i]
        img1 = recipe_images.get(r1['Title'], '')
        img1_tag = f'<img src="{img1}" alt="{r1["Title"]}" width="280" height="280" style="border-radius: 6px; border: 1px solid #e5e5ea;">' if img1 else '<p><em>No image</em></p>'
        html += f"""
            <td style="border: none; width: 50%; padding: 10px; vertical-align: top;">
                <strong>{r1['Title']}</strong><br>
                <span style="font-size: 11px; color: #8e8e93;">Rating: {r1['Rating']} ⭐ | Time: {r1['Total Time']}</span><br>
                {img1_tag}
            </td>
        """
        
        # Right cell (if exists)
        if i + 1 < len(selected_meals):
            r2 = selected_meals[i+1]
            img2 = recipe_images.get(r2['Title'], '')
            img2_tag = f'<img src="{img2}" alt="{r2["Title"]}" width="280" height="280" style="border-radius: 6px; border: 1px solid #e5e5ea;">' if img2 else '<p><em>No image</em></p>'
            html += f"""
                <td style="border: none; width: 50%; padding: 10px; vertical-align: top;">
                    <strong>{r2['Title']}</strong><br>
                    <span style="font-size: 11px; color: #8e8e93;">Rating: {r2['Rating']} ⭐ | Time: {r2['Total Time']}</span><br>
                    {img2_tag}
                </td>
            """
        else:
            html += '<td style="border: none; width: 50%;"></td>'
            
        html += '</tr>'
    html += '</table>'
        
    # Shopping List
    html += "<h2>🛒 Optimized Grocery Shopping List</h2>"
    html += "<p><em>Standard pantry staples (salt, pepper, oil, butter, garlic, onion) are automatically excluded.</em></p>"
    
    for category in ["Produce", "Meat & Seafood", "Dairy & Eggs", "Canned Goods & Grains", "Pantry & Spices", "Other / Miscellaneous"]:
        items = shopping_list.get(category, [])
        if items:
            html += f"<h3>{category}</h3>"
            for item in items:
                recipes_str = ", ".join([f"{r}" for r in item['recipes']])
                html += f'<div class="shopping-item">[ ] <strong>{item["detail"]}</strong> <span class="recipe-tags">(for: {recipes_str})</span></div>'
                
    # Add step-by-step instructions
    if instructions_html:
        html += f"<div class='instruction-section'>{instructions_html}</div>"
        
    html += """
    </body>
    </html>
    """
    return html

def upload_to_drive():
    creds = get_credentials()
    if not creds:
        print("Error: credentials not found.")
        return
        
    selected_meals, shopping_list, instructions_html = parse_meal_plan()
    if not selected_meals:
        print("Error: Could not parse meal plan file.")
        return
        
    # Get recipe images
    titles = [m['Title'] for m in selected_meals]
    recipe_images = get_recipe_images(CSV_FILENAME, titles)
    
    # Generate HTML content
    html_content = build_html_document(selected_meals, shopping_list, recipe_images, instructions_html)
    
    # Connect to Google Drive API
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Get or create "Meal Plans" folder
    meal_plans_folder_id = get_or_create_meal_plans_folder(drive_service)
    
    # Formatted document name: yymmdd weekly meal plan
    doc_name = f"{get_start_of_week_date()} weekly meal plan"
    
    # File metadata - setting mimetype to vnd.google-apps.document converts it to Google Doc
    file_metadata = {
        'name': doc_name,
        'mimeType': 'application/vnd.google-apps.document',
        'parents': [meal_plans_folder_id]
    }
    
    # Upload media stream
    media = MediaIoBaseUpload(
        io.BytesIO(html_content.encode('utf-8')), 
        mimetype='text/html', 
        resumable=True
    )
    
    # Delete previous document if it exists to avoid duplication
    q = f"name = '{doc_name}' and '{meal_plans_folder_id}' in parents and trashed = false"
    prev_results = drive_service.files().list(q=q, fields="files(id)").execute()
    for prev_file in prev_results.get('files', []):
        print(f"Deleting older copy of Google Doc '{doc_name}' (ID: {prev_file['id']})...")
        drive_service.files().delete(fileId=prev_file['id']).execute()
    
    print(f"Uploading and converting HTML to Google Doc '{doc_name}' on Drive in 'Meal Plans' folder...")
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    print(f"Success! Google Doc '{doc_name}' created successfully.")
    print(f"File ID: {file.get('id')}")
    print(f"webViewLink: {file.get('webViewLink')}")

if __name__ == "__main__":
    upload_to_drive()
