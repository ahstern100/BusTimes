import requests
import os
from datetime import datetime
import gtfs_parser 
import urllib3 # נדרש כדי לדכא את אזהרות SSL

# --- הגדרות ---
# כתובת ה-URL לקובץ ה-GTFS (יש לוודא שהיא עדכנית!)
GTFS_URL = "https://gtfs.mot.gov.il/gtfsfiles/gtfs.zip"
OUTPUT_FILENAME = "gtfs.zip"
OUTPUT_SCHEDULE_FILENAME = "schedule.txt"

# דוחה אזהרות SSL שמופיעות כאשר משתמשים ב-verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        
def download_file(url, filename):
    """מוריד קובץ מ-URL ושומר אותו, עם כיבוי אימות SSL והוספת User-Agent."""
    print("--- Starting GTFS Download Process ---")
    print(f"DEBUG: Target URL: {url}")
    print(f"DEBUG: Output file name: {filename}")
    
    # *** התיקון: הוספת Headers כדי להיראות כמו דפדפן ***
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # שליחת בקשת HTTP עם ביטול אימות SSL והכותרות החדשות
        response = requests.get(url, stream=True, verify=False, headers=headers)
        response.raise_for_status() # זורק שגיאה אם הבקשה נכשלה (קוד 4xx או 5xx)

        # בדיקה קריטית: ודא שהתשובה אינה HTML
        if 'html' in response.headers.get('Content-Type', '').lower():
            # הדפסת התוכן לדיבוג והעלאת שגיאה מפורשת
            error_content = response.text[:200]
            print(f"FATAL ERROR: Server returned HTML page instead of ZIP. Content start: {error_content}...")
            # זריקת שגיאה כדי להפסיק את ה-Action בשלב זה
            raise requests.exceptions.RequestException("Server returned HTML error page instead of ZIP file.")

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
        schedule_generated = False # דגל חדש

        try:
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate schedule.")
        except Exception as e:
            # אם יש שגיאה קשה בקוד עצמו
            print(f"CRITICAL ERROR: Failed to run gtfs_parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** התיקון הקריטי: בדיקה אם הקובץ נוצר ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for commit.")
            schedule_generated = True
        else:
            print(f"WARNING: {OUTPUT_SCHEDULE_FILENAME} was NOT generated. Will only commit gtfs.zip.")
            
        # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
        commit_msg = f"GTFS Update for {datetime.now().strftime('%Y-%m-%d')}"
        
        if schedule_generated:
            # אם שני הקבצים נוצרו
            files_to_commit = f"{OUTPUT_FILENAME} {OUTPUT_SCHEDULE_FILENAME}"
        else:
            # אם רק קובץ ה-ZIP ירד
            files_to_commit = OUTPUT_FILENAME

        print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
        print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
