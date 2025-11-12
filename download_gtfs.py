import os
from datetime import datetime
# ייבוא: מחליפים את gtfs_parser ב-weekly_parser, שהוא קובץ ה-Wrapper החדש
import weekly_parser 
import subprocess 

# --- הגדרות ---
OUTPUT_FILENAME = "gtfs.zip"
# *** שינוי: שם קובץ הפלט מצופה כעת להיות schedule2.txt ***
OUTPUT_SCHEDULE_FILENAME = "schedule2.txt" 


if __name__ == '__main__':
    
    commit_msg = f"GTFS Weekly Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
    files_to_commit = ""

    # *** קובץ GTFS.zip צריך להיות קיים ***
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"FATAL ERROR: Downloaded file {OUTPUT_FILENAME} not found. Aborting parsing.")
    else:
        
        # --- שלב הפארסינג ---
        print("\n--- Starting GTFS Weekly Schedule Generation ---")
        schedule_generated = False 

        try:
            # *** שינוי קריטי: קוראים לפונקציה הראשית של weekly_parser.py ***
            weekly_parser.generate_weekly_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate weekly schedule.")
        except Exception as e:
            # אם יש שגיאה ב-Parser, היא תודפס כאן!
            print(f"CRITICAL ERROR in Weekly Parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** בדיקה מפורשת אם קובץ הפלט החדש נוצר ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for commit.")
            schedule_generated = True
        else:
            print(f"WARNING: File was NOT generated. Check the Action logs above for Python errors.")
            
        
        # מכיוון שרק schedule2.txt נוצר, רק אותו נבקש לבצע Commit
        if schedule_generated:
            files_to_commit = OUTPUT_SCHEDULE_FILENAME
        
    
    # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
    print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
    print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
