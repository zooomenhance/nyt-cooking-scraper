import os
import csv
import io
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1U4QvXod6Fj8m22OwcQOC96XGkuBgMgJl54jric-WUWA'
DRIVE_FOLDER_ID = '1L9UoykuM2oeYvVl5AtLtcoHEs45CtcEz'
CSV_FILENAME = 'nyt_recipes_index.csv'
PDF_DIR = 'nyt_recipes_pdfs'
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"!!! Error refreshing credentials: {e}")
                print("Deleting token.pickle and restarting authentication flow...")
                if os.path.exists(TOKEN_FILE):
                    try:
                        os.remove(TOKEN_FILE)
                    except:
                        pass
                creds = None
        
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: {CREDENTIALS_FILE} not found.")
                print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console")
                print("and rename it to 'credentials.json' in this directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def sync_pdfs(drive_service):
    print("Checking Google Drive for existing PDFs...")
    existing_files = {}
    page_token = None
    
    while True:
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token
        ).execute()
        
        for f in results.get('files', []):
            existing_files[f['name']] = f['id']
            
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    local_pdfs = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
    print(f"Found {len(local_pdfs)} local PDFs. (Drive has {len(existing_files)} files).")
    
    count = 0
    for pdf in local_pdfs:
        if pdf not in existing_files:
            print(f"  Uploading {pdf}...")
            file_metadata = {'name': pdf, 'parents': [DRIVE_FOLDER_ID]}
            media = MediaFileUpload(os.path.join(PDF_DIR, pdf), mimetype='application/pdf')
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            count += 1
    
    print(f"Finished PDF sync. {count} new PDFs uploaded.")

def sync_spreadsheet(sheet_service):
    print("Checking Google Sheet for existing entries...")
    # Read the sheet headers and URL column
    sheet = sheet_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='A:Z').execute()
    values = result.get('values', [])
    
    if not values:
        print("Error: Could not read sheet or sheet is empty.")
        return

    headers = values[0]
    try:
        url_index = headers.index('URL')
    except ValueError:
        print("Error: Could not find 'URL' column in the Sheet.")
        return

    existing_urls = {row[url_index] for row in values[1:] if len(row) > url_index}
    
    # Read local CSV
    new_rows = []
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['URL'] not in existing_urls:
                # Align row data with sheet headers
                ordered_row = []
                for h in headers:
                    ordered_row.append(row.get(h, '')) # Fill missing columns with empty string
                new_rows.append(ordered_row)
    
    if not new_rows:
        print("No new recipes to append to the Sheet.")
        return

    print(f"Appending {len(new_rows)} new recipes to the Sheet...")
    body = {'values': new_rows}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID, 
        range='A1', 
        valueInputOption='USER_ENTERED', 
        body=body
    ).execute()
    
    print("Finished Spreadsheet sync.")

def main():
    creds = get_credentials()
    if not creds: return
    
    drive_service = build('drive', 'v3', credentials=creds)
    sheet_service = build('sheets', 'v4', credentials=creds)
    
    sync_pdfs(drive_service)
    sync_spreadsheet(sheet_service)

if __name__ == '__main__':
    main()
