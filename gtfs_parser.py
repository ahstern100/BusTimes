import zipfile
import csv
import io
import os
from collections import defaultdict
from datetime import datetime

# --- הגדרות ---
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"


def list_zip_contents(zfile):
    """מדפיס את כל שמות הקבצים בתוך ה-ZIP לדיבוג ומחזיר את הרשימה."""
    print("--- DEBUG: ZIP Contents ---")
    file_list = zfile.namelist()
    for name in file_list:
        print(f"FILE: {name}")
    print("---------------------------")
    return file_list


def get_current_date_info():
    """מחזיר את תאריך היום בפורמט YYYYMMDD."""
    today = datetime.today()
    date_str = today.strftime('%Y%m%d')
    day_index = (today.weekday() + 1) % 7
    return date_str, day_index


def map_service_ids_for_today(zfile, today_date_str, calendar_dates_file):
    """
    קריאת קובץ נתוני הפעילות (שמועבר כארגומנט) והחזרת סט של service_ids הפעילים היום.
    """
    active_service_ids = set()
    
    print(f"INFO: Processing {calendar_dates_file} to map active service IDs.")
    
    # בגלל שבדקנו את קיום הקובץ בפונקציה הראשית, אנחנו בטוחים שהוא קיים
    with zfile.open(calendar_dates_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            if row['date'] == today_date_str and row['exception_type'] == '1':
                active_service_ids.add(row['service_id'])
        
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
            
            # שלב 1: דיבוג וזיהוי קובץ הלוחות
            zip_contents = list_zip_contents(zfile)
            
            # ניסיון לזהות את קובץ הלוחות הפעיל
            calendar_date_candidates = [f for f in zip_contents if 'calendar' in f and f.endswith('.txt')]
            
            if not calendar_date_candidates:
                 raise Exception("Cannot find any file containing 'calendar' to determine active services.")
            
            # נבחר את הקובץ הסביר ביותר (בדרך כלל calendar_dates.txt או הראשון ברשימה)
            calendar_dates_file = calendar_date_candidates[0]
            print(f"DEBUG: Auto-detected calendar file: {calendar_dates_file}")

            # 2. מציאת ה-Service IDs הפעילים היום
            active_service_ids = map_service_ids_for_today(zfile, today_date_str, calendar_dates_file)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found for {today_date_str}. Check GTFS dates or target routes.")
            
            # 3. מציאת הנסיעות (Trips) הרלוונטיות
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today.")
            
            # 4. משיכת זמני המוצא
            final_schedule = extract_stop_times(zfile, target_trips_to_route)
            
            # 5. שמירת הפלט
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
