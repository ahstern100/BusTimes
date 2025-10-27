import requests
import os
from datetime import datetime
import gtfs_parser # ייבוא הקובץ החדש

# כתובת ה-URL לקובץ ה-GTFS (יש לוודא שהיא עדכנית!)
GTFS_URL = "https://gtfs.mot.gov.il/gtfsfiles/gtfs.zip"
OUTPUT_FILENAME = "gtfs.zip"
OUTPUT_SCHEDULE_FILENAME = "schedule.txt"

def download_file(url, filename):
    """מוריד קובץ מ-URL ושומר אותו."""
    print("--- Starting GTFS Download Process ---")
    print(f"DEBUG: Target URL: {url}")
    print(f"DEBUG: Output file name: {filename}")
    
    try:
        # שליחת בקשת HTTP
        response = requests.get(url, stream=True)
        response.raise_for_status() # זורק שגיאה אם הבקשה נכשלה

        # שמירת הקובץ
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"SUCCESS: File downloaded and saved as {filename}.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed during download: {e}")
        return False
    finally:
        print("--- GTFS Download Process Finished ---")

if __name__ == '__main__':
    if download_file(GTFS_URL, OUTPUT_FILENAME):
        
        # --- שלב חדש: הפעלת קובץ הניתוח ---
        print("\n--- Starting GTFS Parsing and Schedule Generation ---")
        try:
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("SUCCESS: Schedule generated.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to run gtfs_parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # --- התיקון המהותי: שימוש ב-GITHUB_OUTPUT לפתרון שגיאת ה-YAML ---
        
        # 1. יצירת המשתנים
        commit_msg = f"GTFS and Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
        files_to_commit = f"{OUTPUT_FILENAME},{OUTPUT_SCHEDULE_FILENAME}"
        
        # 2. כתיבה לקובץ המשתנים של GitHub Action
        # משתנה הסביבה GITHUB_OUTPUT מכיל את הנתיב לקובץ אליו יש לכתוב
        github_output_path = os.environ.get('GITHUB_OUTPUT')
        
        if github_output_path:
            print("DEBUG: Setting GitHub Action output variables using GITHUB_OUTPUT.")
            try:
                with open(github_output_path, 'a') as f:
                    # כתיבה בפורמט החדש: name=value
                    f.write(f"commit_message={commit_msg}\n")
                    f.write(f"files_to_commit={files_to_commit}\n")
                print("DEBUG: Output variables successfully set.")
            except Exception as e:
                 print(f"ERROR: Failed to write to GITHUB_OUTPUT file: {e}")
        else:
            print("WARNING: GITHUB_OUTPUT environment variable not found. Skipping output variable setting.")
