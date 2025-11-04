import os
from datetime import datetime
import gtfs_parser 

# --- הגדרות ---
OUTPUT_FILENAME = "gtfs.zip"
OUTPUT_SCHEDULE_FILENAME = "schedule.txt"


if __name__ == '__main__':
    # *** קובץ GTFS.zip צריך להיות קיים (הורד ע"י cURL) ***
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"FATAL ERROR: Downloaded file {OUTPUT_FILENAME} not found. Aborting parsing.")
        commit_msg = f"Failed GTFS Update for {datetime.now().strftime('%Y-%m-%d')}"
        files_to_commit = ""
    else:
        
        # --- שלב הפארסינג ---
        print("\n--- Starting GTFS Parsing and Schedule Generation ---")
        schedule_generated = False 

        try:
            # הפעלת הפונקציה הראשית ב-gtfs_parser.py 
            # (מעבירים את שם קובץ ה-ZIP ואת שם קובץ הפלט)
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate schedule.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to run gtfs_parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** בדיקה מפורשת אם קובץ הפלט נוצר ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for commit.")
            schedule_generated = True
        else:
            print(f"WARNING: File was NOT generated. No files will be committed.")
            
        # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
        commit_msg = f"GTFS Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
        
        if schedule_generated:
            # *** שולחים רק את קובץ הלו"ז ***
            files_to_commit = OUTPUT_SCHEDULE_FILENAME
        else:
            files_to_commit = ""

        print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
        print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
