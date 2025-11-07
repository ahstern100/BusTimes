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


def get_current_gtfs_day():
    """מחשב את אינדקס היום הנוכחי בפורמט GTFS (0=ראשון, 6=שבת)."""
    return (datetime.today().weekday() + 1) % 7 


def map_service_ids_for_today(zfile, current_day_index):
    """קריאת calendar.txt והחזרת סט של service_ids הפעילים היום."""
    service_days = set()
    day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday'}
    current_day_column = day_map.get(current_day_index)
    
    print("INFO: Processing calendar.txt to map active service IDs.")
    
    with zfile.open('calendar.txt') as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            if row.get(current_day_column) == '1':
                service_days.add(row['service_id'])
                
    print(f"DEBUG: Found {len(service_days)} active service IDs for today.")
    return service_days


def map_trips_for_target_routes(zfile, active_service_ids):
    """ממפה נסיעות (trips) לקווים הממוקדים הפעילים היום."""
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # 1. מפה routes.txt
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

    print(f"DEBUG: Identified {len(target_trips_to_route)} relevant trips across target routes.")
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
    
    # *** שינוי: פתיחה עם 'w' תמיד דורסת קובץ קיים. ***
    print(f"INFO: Writing schedule to {output_path}. Existing file will be overwritten.")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for route_id, schedule_by_stop in final_schedule.items():
            for stop_id, times in schedule_by_stop.items():
                
                sorted_times = sorted(times)
                times_str = ','.join(sorted_times)
                
                outfile.write(f"{route_id},{stop_id}:{times_str}\n")
                    
    print(f"SUCCESS: Schedule generated and written.")


# -----------------------------------------------------------------
# הפונקציה הראשית (נקראת ע"י download_gtfs.py)
# -----------------------------------------------------------------

def generate_schedule(zip_path, output_path):
    """פונקציית Wrapper המשלבת את כל שלבי הפארסינג."""
    try:
        current_day_index = get_current_gtfs_day()
        print(f"DEBUG: Today's GTFS day index is {current_day_index} (0=Sun, 6=Sat).")
        
        with zipfile.ZipFile(zip_path, 'r') as zfile:
            active_service_ids = map_service_ids_for_today(zfile, current_day_index)
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids)
            final_schedule = extract_stop_times(zfile, target_trips_to_route)
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
    """כדי לשמור על תאימות עם הקוד הקודם."""
    generate_schedule(zip_path, schedule_path)
