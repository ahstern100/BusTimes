import zipfile
import csv
import io
import os
from collections import defaultdict
from datetime import datetime

# --- הגדרות ---
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"

# הקבצים הקריטיים שהלוגים חשפו
CALENDAR_FILE = 'calendar.txt' 
ROUTES_FILE = 'routes.txt'
TRIPS_FILE = 'trips.txt'
STOP_TIMES_FILE = 'stop_times.txt'


def get_current_day_info():
    """מחזיר את תאריך היום (YYYYMMDD) ואת אינדקס היום בשבוע (0=Sun, 6=Sat)."""
    today = datetime.today()
    date_str = today.strftime('%Y%m%d')
    # חישוב: 0=ראשון, 6=שבת
    day_index = (today.weekday() + 1) % 7 
    return date_str, day_index


def map_service_ids_for_today(zfile, current_day_index):
    """
    קריאת calendar.txt והחזרת סט של service_ids הפעילים היום, לפי יום בשבוע.
    """
    active_service_ids = set()
    
    # מיפוי אינדקס היום לעמודה המתאימה ב-calendar.txt
    day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday'}
    current_day_column = day_map.get(current_day_index)
    
    print(f"INFO: Processing {CALENDAR_FILE} to map active service IDs based on column '{current_day_column}'.")
    
    with zfile.open(CALENDAR_FILE) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            # בדיקה קריטית: האם ה-Service ID פעיל ביום זה (עמודה = '1')
            if row.get(current_day_column) == '1':
                active_service_ids.add(row['service_id'])
                
    print(f"DEBUG: Found {len(active_service_ids)} active service IDs for day index {current_day_index}.")
    return active_service_ids


def map_trips_for_target_routes(zfile, active_service_ids):
    """ממפה נסיעות (trips) לקווים הממוקדים הפעילים היום."""
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # 1. מפה routes.txt
    print(f"INFO: Mapping route IDs from {ROUTES_FILE}.")
    with zfile.open(ROUTES_FILE) as f:
         reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
         for row in reader:
             route_id_to_short_name[row['route_id']] = row['route_short_name']

    # 2. מפה trips.txt
    print(f"INFO: Mapping trips for target routes active today from {TRIPS_FILE}.")
    with zfile.open(TRIPS_FILE) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
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
    
    print(f"INFO: Extracting times from {STOP_TIMES_FILE}...")

    with zfile.open(STOP_TIMES_FILE) as f:
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
        today_date_str, current_day_index = get_current_day_info()
        print(f"DEBUG: Processing for date {today_date_str}. Day index: {current_day_index} (0=Sun).")
        
        with zipfile.ZipFile(zip_path, 'r') as zfile:
            
            # שלב 1: מציאת ה-Service IDs הפעילים היום (באמצעות calendar.txt)
            active_service_ids = map_service_ids_for_today(zfile, current_day_index)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found for day index {current_day_index}. This usually means no service is scheduled for this day/time frame.")
            
            # 2. מציאת הנסיעות (Trips) הרלוונטיות
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today. Check that route numbers are correct and have trips scheduled.")
            
            # 3. משיכת זמני המוצא
            final_schedule = extract_stop_times(zfile, target_trips_to_route)
            
            # 4. שמירת הפלט
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
