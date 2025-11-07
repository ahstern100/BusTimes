import os
from datetime import datetime
import gtfs_parser 
import subprocess # חדש: נשתמש בו כדי להריץ את הפארסר בצורה נפרדת

# --- הגדרות ---
OUTPUT_FILENAME = "gtfs.zip"
OUTPUT_SCHEDULE_FILENAME = "schedule.txt"


if __name__ == '__main__':
    
    commit_msg = f"GTFS Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
    files_to_commit = ""

    # *** קובץ GTFS.zip צריך להיות קיים ***
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"FATAL ERROR: Downloaded file {OUTPUT_FILENAME} not found. Aborting parsing.")
    else:
        
        # --- שלב הפארסינג ---
        print("\n--- Starting GTFS Parsing and Schedule Generation ---")
        schedule_generated = False 

        try:
            # קוראים ישירות לפונקציה הראשית של gtfs_parser.py
            gtfs_parser.generate_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate schedule.")
        except Exception as e:
            # אם יש שגיאה ב-Parser, היא תודפס כאן!
            print(f"CRITICAL ERROR in Parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** בדיקה מפורשת אם קובץ הפלט נוצר ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for commit.")
            schedule_generated = True
        else:
            print(f"WARNING: File was NOT generated. Check the Action logs above for Python errors.")
            
        
        if schedule_generated:
            files_to_commit = OUTPUT_SCHEDULE_FILENAME
        
    
    # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
    print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
    print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
