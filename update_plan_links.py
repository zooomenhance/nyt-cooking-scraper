import os
import re
import pickle
import json
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = 'token.pickle'
DRIVE_FOLDER_ID = '1L9UoykuM2oeYvVl5AtLtcoHEs45CtcEz'
PLAN_FILE = 'weekly_meal_plan.md'

def get_credentials():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            return pickle.load(token)
    return None

def update_meal_plan():
    creds = get_credentials()
    if not creds:
        print("Error: credentials not found.")
        return

    drive_service = build('drive', 'v3', credentials=creds)
    print("Fetching files from Google Drive...")
    
    drive_files = {}
    page_token = None
    while True:
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, webViewLink)",
            pageToken=page_token
        ).execute()
        
        for f in results.get('files', []):
            drive_files[f['name']] = f['webViewLink']
            
        page_token = results.get('nextPageToken', None)
        if not page_token:
            break
            
    print(f"Loaded {len(drive_files)} file links from Google Drive.")
    
    # Save the links mapping as JSON for the web interface
    with open('drive_links.json', 'w', encoding='utf-8') as jf:
        json.dump(drive_files, jf, indent=2)
    print("Saved Drive links mapping to drive_links.json")

    if not os.path.exists(PLAN_FILE):
        print(f"Error: {PLAN_FILE} not found.")
        return

    with open(PLAN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find relative PDF links: [PDF](nyt_recipes_pdfs/Filename.pdf)
    matches = re.findall(r'\[PDF\]\((nyt_recipes_pdfs/(.*?\.pdf))\)', content)
    updated_count = 0
    
    for full_match, pdf_name in matches:
        # Match against filenames in Google Drive (spaces vs underscores)
        drive_match = None
        for key in drive_files:
            if key.replace(" ", "_") == pdf_name or key == pdf_name:
                drive_match = key
                break
                
        if drive_match:
            drive_link = drive_files[drive_match]
            # Replace [PDF](nyt_recipes_pdfs/Filename.pdf) with [Google Drive Link](drive_link)
            content = content.replace(f"[PDF](nyt_recipes_pdfs/{pdf_name})", f"[Google Drive Link]({drive_link})")
            updated_count += 1
            print(f"Updated link for: {pdf_name} -> {drive_link}")
        else:
            print(f"Warning: could not find Google Drive link for: {pdf_name}")

    if updated_count > 0:
        with open(PLAN_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Successfully updated {updated_count} links in {PLAN_FILE} to Google Drive.")
    else:
        print("No links were updated.")

if __name__ == "__main__":
    update_meal_plan()
