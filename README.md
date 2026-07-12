# NYT Recipe App - Project Documentation

This project automates the collection, enhancement, and cloud synchronization of recipes from NYT Cooking.

## Script Overview

### 1. `recipe_workflow.py` (Master Orchestrator)
The primary entry point for the application. It runs the entire pipeline sequentially:
- Triggers the scraper to find new recipes.
- Runs the enhancer to add missing metadata/ratings.
- Executes the Google Drive sync to update your cloud spreadsheet and file storage.

**Usage:** `python recipe_workflow.py`

---

### 2. `nyt_recipe_scraper.py`
Uses **Playwright** and **BeautifulSoup4** to crawl NYT Cooking categories.
- Extracts recipe titles, URLs, and metadata.
- Saves recipe pages as **PDFs** in the `nyt_recipes_pdfs/` directory.
- Appends new findings to `nyt_recipes_index.csv`.

---

### 3. `nyt_enhancer.py`
Refines the local data index.
- Cleans up image URLs and text formatting.
- Can be run with `--fast` to only process recent entries.
- Ensures the CSV is ready for cloud synchronization.

---

### 4. `google_sync.py`
Handles all interaction with the **Google Cloud Platform**.
- **Google Sheets:** Uploads/updates the recipe index to a specific spreadsheet.
- **Google Drive:** Ensures all recipe PDFs are backed up to your designated Drive folder.
- **Auth:** Uses `credentials.json` for initial setup and `token.pickle` for persistent sessions.

---

### 5. `test_scraper.py`
A lightweight diagnostic script used to verify that Playwright and the Chromium browser are correctly installed and can reach the NYT Cooking website.

---

## Setup & Maintenance

### Dependencies
If moving to a new machine, install the following:
```powershell
pip install playwright beautifulsoup4 google-api-python-client google-auth-httplib2 google-auth-oauthlib
python -m playwright install chromium
```

### Key Files
- `nyt_recipes_index.csv`: The local master database of all found recipes.
- `nyt_recipes_pdfs/`: Folder containing the downloaded recipe documents.
- `credentials.json`: Google Cloud OAuth2 credentials (do not share).
- `token.pickle`: Your active Google login session.
