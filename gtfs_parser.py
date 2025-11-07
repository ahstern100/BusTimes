import zipfile
import csv
import io
import os
from collections import defaultdict
from datetime import datetime

# --- הגדרות קבועות ---
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"

# שמות הקבצים שהוכחו כקיימים מהלוגים הקודמים
FILES_TO_CHECK = ['calendar.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']


def debug_print_file_contents(zfile, file_name):
    """מדפיס את שמות העמודות (Header) של קובץ CSV בתוך ה-ZIP."""
    try:
        with zfile.open(file_name) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8'))
            header = next(reader, None)
            if header:
                print(f"DEBUG: Header for {file_name}: {header}")
            else:
                print(f"WARNING: {file_name} appears to be empty or missing header.")
            return header
    except KeyError:
        print(f"ERROR: File {file_name} not found in ZIP.")
        return None
    except Exception as e:
        print(f"ERROR: Failed to read header from {file_name}: {e}")
        return None


def list_zip_contents(zfile):
    """מדפיס את כל שמות הקבצים בתוך ה-ZIP ומחזיר את הרשימה."""
    print("--- DEBUG: ZIP Contents ---")
    file_list = zfile.namelist()
    for name in file_list:
        print(f"FILE: {name}")
    print("---------------------------")
    return file_list


def get_current_day_info():
    """מחזיר את תאריך היום (YYYYMMDD) ואת אינדקס היום בשבוע (0=Sun, 6=Sat)."""
    today = datetime.today()
    date_str = today.strftime('%Y%m%d')
    day_index = (today.weekday() + 1) % 7
    return date_str, day_index


def map_service_ids_for_today(zfile, current_day_index, zip_contents):
    """
    קריאת calendar.txt והחזרת סט של service_ids הפעילים היום, לפי יום בשבוע.
    הפונקציה כוללת בדיקות דיבוג מקיפות.
    """
    active_service_ids = set()
    calendar_file = 'calendar.txt'
    
    if calendar_file not in zip_contents:
        raise Exception(f"File {calendar_file} is not in the archive!")
    
    # 1. דיבוג: הדפסת שמות העמודות
    header = debug_print_file_contents(zfile, calendar_file)
    if not header or 'service_id' not in header:
        raise Exception(f"Header check failed for {calendar_file}. 'service_id' column is missing.")
        
    # 2. לוגיקה
    day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday'}
    current_day_column = day_map.get(current_day_index)
    
    if current_day_column not in header:
         raise Exception(f"Header check failed for {calendar_file}. Column '{current_day_column}' is missing.")
         
    print(f"INFO: Processing {calendar_file} to map active service IDs based on column '{current_day_column}'.")
    
    with zfile.open(calendar_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            if row.get(current_day_column) == '1':
                # שימו לב: ה-KeyError הקודם היה כאן! עכשיו אנחנו בודקים את העמודה.
                active_service_ids.add(row['service_id'])
                
    print(f"DEBUG: Found {len(active_service_ids)} active service IDs.")
    return active_service_ids


def map_trips_for_target_routes(zfile, active_service_ids, zip_contents):
    """ממפה נסיעות (trips) לקווים הממוקדים הפעילים היום."""
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # --- routes.txt ---
    routes_file = 'routes.txt'
    if routes_file not in zip_contents: raise Exception(f"File {routes_file} is not in the archive!")
    routes_header = debug_print_file_contents(zfile, routes_file)
    if not routes_header or 'route_id' not in routes_header:
        raise Exception(f"Header check failed for {routes_file}. 'route_id' is missing.")

    print(f"INFO: Mapping route IDs from {routes_file}.")
    with zfile.open(routes_file) as f:
         reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
         for row in reader:
             route_id_to_short_name[row['route_id']] = row['route_short_name']

    # --- trips.txt ---
    trips_file = 'trips.txt'
    if trips_file not in zip_contents: raise Exception(f"File {trips_file} is not in the archive!")
    trips_header = debug_print_file_contents(zfile, trips_file)
    if not trips_header or 'service_id' not in trips_header:
        raise Exception(f"Header check failed for {trips_file}. 'service_id' is missing.")

    print(f"INFO: Mapping trips for target routes active today from {trips_file}.")
    with zfile.open(trips_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            route_short_name = route_id_to_short_name.get(row['route_id'])
            service_id = row['service_id']
            
            if route_short_name in TARGET_ROUTES and service_id in active_service_ids:
                target_trips_to_route[row['trip_id']] = route_short_name

    print(f"DEBUG: Identified {len(target_trips_to_route)} relevant trips.")
    return target_trips_to_route


def extract_stop_times(zfile, target_trips_to_route, zip_contents):
    """מוצא את זמני המוצא (stop_sequence=1) עבור הנסיעות הרלוונטיות."""
    final_schedule = defaultdict(lambda: defaultdict(list)) 
    all_target_trips = set(target_trips_to_route.keys())
    stop_times_file = 'stop_times.txt'
    
    if stop_times_file not in zip_contents: raise Exception(f"File {stop_times_file} is not in the archive!")
    stop_times_header = debug_print_file_contents(zfile, stop_times_file)
    if not stop_times_header or 'stop_sequence' not in stop_times_header:
         raise Exception(f"Header check failed for {stop_times_file}.")

    print(f"INFO: Extracting times from {stop_times_file}...")

    with zfile.open(stop_times_file) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            trip_id = row['trip_id']
            
            if trip_id in all_target_trips:
                if row['stop_sequence'] == '1': 
                    
                    # קוראים את Route ID מהמפה שיצרנו, לא מה-GTFS
                    route_short_name = target_trips_to_route[trip_id]
                    departure_time = row['departure_time'][:5] # HH:MM

                    final_schedule[route_short_name][row['stop_id']].append(departure_time)
                    
    return final_schedule


def write_final_schedule(final_schedule, output_path):
    """כתיבת הלו"ז המעובד לקובץ הפלט schedule.txt."""
    print(f"INFO: Writing schedule to {output_path}. Existing file will be overwritten.")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        # הקוד הזה בטוח ואינו דורש דיבוג מיוחד
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
            
            # שלב 1: דיבוג תוכן ה-ZIP
            zip_contents = list_zip_contents(zfile)
            
            # 2. מציאת ה-Service IDs הפעילים היום
            active_service_ids = map_service_ids_for_today(zfile, current_day_index, zip_contents)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found. No service is scheduled for this day/time frame.")
            
            # 3. מציאת הנסיעות (Trips) הרלוונטיות
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids, zip_contents)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today.")
            
            # 4. משיכת זמני המוצא
            final_schedule = extract_stop_times(zfile, target_trips_to_route, zip_contents)
            
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
