import requests
import os
from datetime import datetime
import gtfs_parser 

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
            # הפעלת הפונקציה הראשית מקובץ gtfs_parser.py
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("SUCCESS: Schedule generated.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to run gtfs_parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # --- הדפסת המשתנים בפורמט קבוע וקל לזיהוי ע"י ה-YAML ---
        # שים לב: אין כאן שימוש ב-GITHUB_OUTPUT, אלא רק הדפסה רגילה.
        # ה-YAML משתמש ב-bash כדי ללכוד את השורות הללו.
        
        commit_msg = f"GTFS and Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
        # הערה: זהו פורמט מופרד בפסיקים (עבור file_pattern)
        files_to_commit = f"{OUTPUT_FILENAME},{OUTPUT_SCHEDULE_FILENAME}"
        
        # הדפסה עם תחילית מזהה (ללא רווחים מיותרים!)
        print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
        print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
