import subprocess
import sys
import os

def run_command(command):
    print(f"\n>>> Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"!!! Error: Command failed with return code {result.returncode}")
        sys.exit(1)

def main():
    print("=== NYT RECIPE UPDATE WORKFLOW ===")
    
    # 1. Scrape new recipes
    run_command([sys.executable, "nyt_recipe_scraper.py"])
    
    # 2. Enhance with ratings (Fast mode: only first 5 pages)
    run_command([sys.executable, "nyt_enhancer.py", "--fast"])
    
    # 3. Sync to Google Drive and Sheets
    if os.path.exists("credentials.json"):
        run_command([sys.executable, "google_sync.py"])
    else:
        print("\n!!! Warning: 'credentials.json' not found.")
        print("Scraping and Enhancing completed locally, but Google Sync was skipped.")
        print("To enable sync, download your OAuth 2.0 Client ID JSON from Google Cloud Console,")
        print("rename it to 'credentials.json', and run this script again.")

    print("\n=== WORKFLOW COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
