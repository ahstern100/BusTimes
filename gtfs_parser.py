# gtfs_parser.py
import zipfile
import os
from datetime import datetime
# ייבוא כל הפונקציות מקובץ העזר
from gtfs_utils import (
    list_zip_contents, 
    get_current_day_info, 
    map_service_ids_for_today,
    map_stop_info,
    convert_codes_to_ids,
    find_relevant_trips_by_stops,
    map_trips_for_target_routes,
    extract_stop_times,
    write_final_schedule,
    CRITICAL_STOP_CODES # ייבוא קבועים קריטיים
)

def generate_schedule(zip_path, output_path):
    """פונקציית Wrapper המשלבת את כל שלבי הפארסינג."""
    try:
        today_date_str, current_day_index = get_current_day_info()
        print(f"DEBUG: Processing for date {today_date_str}. Day index: {current_day_index} (0=Sun).")
        
        # --- הגדרות קבועות (כדי שיהיו גלובליות לכל הפונקציות) ---
        # הפונקציה convert_codes_to_ids משנה את המשתנה הגלובלי CRITICAL_STOP_IDS בתוך gtfs_utils

        with zipfile.ZipFile(zip_path, 'r') as zfile:
            
            zip_contents = list_zip_contents(zfile)
            
            # 1. מציאת ה-Service IDs הפעילים היום
            active_service_ids = map_service_ids_for_today(zfile, current_day_index, zip_contents)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found. No service is scheduled for this day/time frame.")
            
            # 2. מיפוי Stop Code ל-Stop ID
            stop_id_to_code, stop_code_to_id = map_stop_info(zfile, zip_contents)
            
            # 3. המרת הקבועים החיצוניים (Stop Codes) ל-Stop IDs פנימיים
            converted_ids = convert_codes_to_ids(stop_code_to_id)

            if not converted_ids:
                print("WARNING: No valid Stop IDs found for the critical Stop Codes. Proceeding without geographic filter.")
            
            # 4. סינון גיאוגרפי - מציאת ה-Trips שעוברים ב-IDs הנכונים
            relevant_trip_ids = find_relevant_trips_by_stops(zfile, zip_contents)
            
            # 5. מציאת הנסיעות (Trips) הרלוונטיות לאחר סינון כפול
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids, relevant_trip_ids, zip_contents)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today. Check that the routes are active and pass through the critical stops.")
            
            # 6. משיכת שעות המוצא
            final_schedule = extract_stop_times(zfile, target_trips_to_route, stop_id_to_code, zip_contents)
            
            # 7. שמירת הפלט (כאן נמצא תיקון ה-strip לפורמט)
            write_final_schedule(final_schedule, output_path)

    except Exception as e:
        print(f"CRITICAL PARSING ERROR in generate_schedule: {e}")
        try:
             if os.path.exists(output_path):
                 os.remove(output_path)
        except:
            pass
        raise e

def generate_data(zip_path, schedule_path, dates_path=None):
    generate_schedule(zip_path, schedule_path)
