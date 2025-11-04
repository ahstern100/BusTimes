import os
from datetime import datetime
import gtfs_parser 

# --- הגדרות ---
OUTPUT_FILENAME = "gtfs.zip"
OUTPUT_SCHEDULE_FILENAME = "schedule.txt"

# פונקציית ההורדה הוסרה לחלוטין!

if __name__ == '__main__':
    # *** התיקון הקריטי: ודא שהקובץ gtfs.zip קיים לפני הפארסינג ***
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"FATAL ERROR: Downloaded file {OUTPUT_FILENAME} not found. Aborting parsing.")
        # נדפיס רק הודעת Commit ריקה
        commit_msg = f"Failed GTFS Update for {datetime.now().strftime('%Y-%m-%d')}"
        files_to_commit = ""
    else:
        
        # --- שלב חדש: הפעלת קובץ הניתוח ---
        print("\n--- Starting GTFS Parsing and Schedule Generation ---")
        schedule_generated = False 

        try:
            # הפעלת הפונקציה הראשית מקובץ gtfs_parser.py
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate schedule.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to run gtfs_parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** בדיקה מפורשת אם הקובץ נוצר (כפי שתיקנו קודם) ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for commit.")
            schedule_generated = True
        else:
            # אם אין schedule.txt, לא נבצע commit על כלום כדי למנוע שגיאות
            print(f"WARNING: {OUTPUT_SCHEDULE_FILENAME} was NOT generated. No files will be committed.")
            
        # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
        commit_msg = f"Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
        
        if schedule_generated:
            # *** התיקון הקריטי: אנחנו שולחים רק את schedule.txt! ***
            files_to_commit = OUTPUT_SCHEDULE_FILENAME
        else:
            # אם שום דבר לא נוצר, נשלח קלט ריק
            files_to_commit = ""

        print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
        print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
