import zipfile
import csv
import io
import os
from collections import defaultdict
from datetime import datetime

# --- הגדרות ---
# רשימת הקווים הממוקדים שלך
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"


def get_current_date_info():
    """מחזיר את תאריך היום בפורמט YYYYMMDD."""
    today = datetime.today()
    date_str = today.strftime('%Y%m%d')
    # האינדקס משמש אותנו רק לדיבוג פנימי, אבל הנתון הקריטי הוא התאריך
    day_index = (today.weekday() + 1) % 7 # 0=Sun, 6=Sat
    return date_str, day_index


def map_service_ids_for_today(zfile, today_date_str):
    """
    קריאת calendar_dates.txt (השיטה הישראלית) והחזרת סט של service_ids הפעילים היום.
    """
    active_service_ids = set()
    
    # 1. בדיקה האם calendar.txt קיים. אם כן, נתעלם ממנו.
    # אנחנו מתמקדים ב-calendar_dates.txt
    print("INFO: Processing calendar_dates.txt to map active service IDs.")
    
    try:
        with zfile.open('calendar_dates.txt') as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
            for row in reader:
                # בדיקה: האם התאריך הוא היום, והאם זה 'שירות רגיל' (exception_type=1)
                # ה-GTFS הישראלי משתמש ב-exception_type 1 (שירות שנוסף) או 2 (שירות שבוטל).
                # אנחנו מעוניינים בשירות שנוסף (פעיל).
                if row['date'] == today_date_str and row['exception_type'] == '1':
                    active_service_ids.add(row['service_id'])
    except KeyError as e:
        # זה קורה אם אחת העמודות חסרה, מה שלא סביר ב-calendar_dates.txt
        print(f"CRITICAL ERROR: Missing column in calendar_dates.txt: {e}")
        raise e
    except FileNotFoundError:
        print("WARNING: calendar_dates.txt not found. Unable to determine active services.")
        
    print(f"DEBUG: Found {len(active_service_ids)} active service IDs for {today_date_str}.")
    return active_service_ids


def map_trips_for_target_routes(zfile, active_service_ids):
    """ממפה נסיעות (trips) לקווים הממוקדים הפעילים היום."""
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # 1. מפה routes.txt
    print("INFO: Mapping route IDs to short names.")
    with zfile.open('routes.txt') as f:
         reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
         for row in reader:
             route_id_to_short_name[row['route_id']] = row['route_short_name']

    # 2. מפה trips.txt
    print("INFO: Mapping trips for target routes active today.")
    with zfile.open('trips.txt') as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            # כאן היה ה-KeyError הקודם (אם הקובץ calendar.txt היה נדגם לפניו)
            route_short_name = route_id_to_short_name.get(row['route_id'])
            service_id = row['service_id']
            
            if route_short_name in TARGET_ROUTES and service_id in active_service_ids:
                target_trips_to_route[row['trip_id']] = route_short_name

    print(f"DEBUG: Identified {len(target_trips_to_route)} relevant trips.")
    return target_trips_to_route


def extract_stop_times(zfile, target_trips_to_route):
    """מוצא את זמני המוצא (stop_sequence=1) עבור הנסיעות הרלוונטיות."""
    final_schedule = defaultdict(lambda: defaultdict(list)) 
    all_target_trips = set(target_trips_to_route.keys())
    
    print(f"INFO: Extracting times from stop_times.txt...")

    with zfile.open('stop_times.txt') as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            trip_id = row['trip_id']
            
            if trip_id in all_target_trips:
                if row['stop_sequence'] == '1': 
                    
                    route_short_name = target_trips_to_route[trip_id]
                    departure_time = row['departure_time'][:5] # HH:MM

                    final_schedule[route_short_name][row['stop_id']].append(departure_time)
                    
    return final_schedule


def write_final_schedule(final_schedule, output_path):
    """כתיבת הלו"ז המעובד לקובץ הפלט schedule.txt."""
    print(f"INFO: Writing schedule to {output_path}. Existing file will be overwritten.")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for route_id, schedule_by_stop in final_schedule.items():
            for stop_id, times in schedule_by_stop.items():
                
                sorted_times = sorted(times)
                times_str = ','.join(sorted_times)
                
                outfile.write(f"{route_id},{stop_id}:{times_str}\n")
                    
    print(f"SUCCESS: Schedule generated and written for {len(final_schedule)} routes.")


# -----------------------------------------------------------------
# הפונקציה הראשית (נקראת ע"י download_gtfs.py)
# -----------------------------------------------------------------

def generate_schedule(zip_path, output_path):
    """פונקציית Wrapper המשלבת את כל שלבי הפארסינג."""
    try:
        today_date_str, current_day_index = get_current_date_info()
        print(f"DEBUG: Processing for date {today_date_str}. Day index: {current_day_index}.")
        
        with zipfile.ZipFile(zip_path, 'r') as zfile:
            # 1. מציאת ה-Service IDs הפעילים היום (באמצעות calendar_dates.txt)
            active_service_ids = map_service_ids_for_today(zfile, today_date_str)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found for {today_date_str}. Check GTFS dates.")
            
            # 2. מציאת הנסיעות (Trips) הרלוונטיות לקווים שלך ופעילות היום
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today.")
            
            # 3. משיכת זמני המוצא מהנסיעות הרלוונטיות
            final_schedule = extract_stop_times(zfile, target_trips_to_route)
            
            # 4. שמירת הפלט
            write_final_schedule(final_schedule, output_path)

    except Exception as e:
        print(f"CRITICAL PARSING ERROR in generate_schedule: {e}")
        # מנקה את קובץ הפלט כדי למנוע Commit של נתונים שגויים
        try:
             if os.path.exists(output_path):
                 os.remove(output_path)
        except:
            pass
        raise e

def generate_data(zip_path, schedule_path, dates_path=None):
    """כדי לשמור על תאימות עם הקוד הקודם."""
    generate_schedule(zip_path, schedule_path)
