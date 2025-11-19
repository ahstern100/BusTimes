import os
from datetime import datetime
# ייבוא: מחליפים את gtfs_parser ב-weekly_parser, שהוא קובץ ה-Wrapper החדש
import weekly_parser 
# *** חדש: ייבוא הקובץ route_mapper ***
import route_mapper 
import subprocess 

# --- הגדרות ---
OUTPUT_FILENAME = "gtfs.zip"
# *** שינוי: שם קובץ הפלט מצופה כעת להיות schedule2.txt ***
OUTPUT_SCHEDULE_FILENAME = "schedule2.txt" 
# *** חדש: שם קובץ פלט המסלולים ***
OUTPUT_ROUTES_FILENAME = "routes_data.txt"


if __name__ == '__main__':
    
    commit_msg = f"GTFS Weekly Schedule Update for {datetime.now().strftime('%Y-%m-%d')}"
    files_to_commit = ""

    # *** קובץ GTFS.zip צריך להיות קיים ***
    if not os.path.exists(OUTPUT_FILENAME):
        print(f"FATAL ERROR: Downloaded file {OUTPUT_FILENAME} not found. Aborting parsing.")
    else:
        
        # --- שלב הפארסינג של לוח הזמנים ---
        print("\n--- Starting GTFS Weekly Schedule Generation ---")
        schedule_generated = False 

        try:
            # *** קריאה לפונקציה הראשית של weekly_parser.py ***
            weekly_parser.generate_weekly_schedule(OUTPUT_FILENAME, OUTPUT_SCHEDULE_FILENAME)
            print("INFO: Attempted to generate weekly schedule.")
        except Exception as e:
            # אם יש שגיאה ב-Parser, היא תודפס כאן!
            print(f"CRITICAL ERROR in Weekly Parser: {e}")
        finally:
            print("--- GTFS Parsing Process Finished ---")

        # *** בדיקה מפורשת אם קובץ הפלט החדש נוצר ***
        if os.path.exists(OUTPUT_SCHEDULE_FILENAME):
            print(f"SUCCESS: {OUTPUT_SCHEDULE_FILENAME} found and ready for route mapping.")
            schedule_generated = True
            
            # --- שלב מיפוי המסלולים (חדש) ---
            print("\n--- Starting Route Mapping Generation (routes_data.txt) ---")
            routes_generated = False
            
            try:
                # *** קריאה לפונקציה הראשית של route_mapper.py ***
                # אנחנו מעבירים את שם קובץ ה-GTFS.zip כדי שהוא יוכל לחלץ ממנו את stop_times.txt
                route_mapper.generate_routes_data(OUTPUT_FILENAME) 
                
                if os.path.exists(OUTPUT_ROUTES_FILENAME):
                    print(f"SUCCESS: {OUTPUT_ROUTES_FILENAME} generated successfully.")
                    routes_generated = True
                else:
                    print(f"WARNING: Route mapping file ({OUTPUT_ROUTES_FILENAME}) was NOT generated.")
                    
            except Exception as e:
                print(f"CRITICAL ERROR in Route Mapper: {e}")
            finally:
                print("--- Route Mapping Process Finished ---")
                
        else:
            print(f"WARNING: Schedule file ({OUTPUT_SCHEDULE_FILENAME}) was NOT generated. Check the Action logs above for Python errors.")
            
        
        # --- הכנת הקבצים ל-Commit ---
        if schedule_generated:
            files_to_commit = OUTPUT_SCHEDULE_FILENAME
        
        # אם גם קובץ המסלולים נוצר, נוסיף אותו
        if routes_generated:
            if files_to_commit:
                 files_to_commit += "," + OUTPUT_ROUTES_FILENAME
            else:
                 files_to_commit = OUTPUT_ROUTES_FILENAME
        
    
    # --- הגדרת המשתנים כהדפסה פשוטה לקונסולה ---
    print(f"ACTION_OUTPUT_COMMIT_MESSAGE:{commit_msg}")
    print(f"ACTION_OUTPUT_FILES_TO_COMMIT:{files_to_commit}")
