# weekly_parser.py

import os
from datetime import date, timedelta
from gtfs_parser import generate_schedule # ייבוא פונקציית הליבה מהקובץ הקיים
from gtfs_utils import CRITICAL_STOP_CODES # ייבוא קבועים קריטיים
# נניח ש-gtfs_utils מכיל את הפונקציות הבאות:
# get_service_id_for_date, map_service_ids_for_date

ZIP_FILE_PATH = "path/to/your/gtfs.zip" 
OUTPUT_FILE_PATH = "schedule2.txt"

def get_day_info_for_date(target_date):
    """
    מחשבת את מחרוזת התאריך ואת אינדקס יום השבוע (GTFS) עבור תאריך נתון.
    GTFS index: 0=ראשון, 6=שבת.
    """
    date_str = target_date.strftime('%Y%m%d')
    # יום שני הוא 0 ב-Python, אנו רוצים ראשון להיות 0 כפי שמקובל ב-GTFS
    day_index = (target_date.weekday() + 1) % 7  
    return date_str, day_index


def generate_weekly_schedule(zip_path, output_path):
    """
    מייצרת קובץ לוח זמנים שבועי המשלב את כל 7 הימים הבאים.
    """
    
    # 1. חישוב 7 הימים הקרובים (0=היום, 1=מחר, ... 6=היום השישי)
    start_date = date.today()
    week_days = []
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        date_str, gtfs_day_index = get_day_info_for_date(current_date)
        
        week_days.append({
            'offset': day_offset,
            'date_str': date_str,
            'gtfs_day_index': gtfs_day_index
        })
    
    all_output_lines = []
    
    # 2. הרצת הפארסר עבור כל יום בנפרד
    for day in week_days:
        temp_output_path = f"temp_schedule_{day['offset']}.txt"
        
        print(f"\n--- Starting parsing for Day Offset {day['offset']} ({day['date_str']}) ---")
        
        try:
            # הפעלת הפארסר הראשי עבור היום הספציפי
            generate_schedule(
                zip_path, 
                temp_output_path, 
                day_info=(day['date_str'], day['gtfs_day_index'])
            )
            
            # 3. קריאת הפלט הזמני ושילוב מפתח היום
            with open(temp_output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # הפורמט הנוכחי הוא: RouteID|StopCode:times
            # הפורמט החדש הוא: RouteID|StopCode|DayOffset:times
            for line in lines:
                if ':' in line:
                    key_part, times_part = line.split(':', 1)
                    # יצירת המפתח המורכב: קו|תחנה|מספר_יום_רציף
                    new_key = f"{key_part}|{day['offset']}"
                    all_output_lines.append(f"{new_key}:{times_part.strip()}")
            
            os.remove(temp_output_path) # מחיקת הקובץ הזמני
            
        except Exception as e:
            print(f"WARNING: Skipping Day Offset {day['offset']} due to error: {e}")
            if os.path.exists(temp_output_path):
                 os.remove(temp_output_path)

    # 4. כתיבת הקובץ הסופי
    if all_output_lines:
        print(f"\nSUCCESS: Writing {len(all_output_lines)} combined schedule lines to {output_path}.")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_output_lines))
    else:
        print("CRITICAL: No schedule data generated for the entire week.")


if __name__ == '__main__':
    # יש להחליף בנתיבים האמיתיים שלך
    # generate_weekly_schedule(ZIP_FILE_PATH, OUTPUT_FILE_PATH)
    print("Please configure ZIP_FILE_PATH and run generate_weekly_schedule.")
