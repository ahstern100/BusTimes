import zipfile
import csv
import io
from collections import defaultdict
from datetime import datetime

# --- הגדרות ---
# רשימת הקווים הממוקדים: 20, 20א, 22, 60, 60א, 71, 71א, 631, 632, 634, 63, 163, 160, 127
# ה-GTFS משתמש ב-route_short_name, לכן נשמור אותם כ-strings.
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"


def get_current_gtfs_day():
    """מחשב את אינדקס היום הנוכחי בפורמט GTFS (0=ראשון, 6=שבת)."""
    # יום שני (0) עד יום ראשון (6) ב-Python -> יום ראשון (0) עד יום שבת (6) ב-GTFS
    return (datetime.today().weekday() + 1) % 7 


def map_service_ids_for_today(zfile, current_day_index):
    """
    קריאת calendar.txt והחזרת סט של service_ids הפעילים היום.
    """
    service_days = set()
    day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday'}
    current_day_column = day_map.get(current_day_index)
    
    print("INFO: Mapping service IDs for the current day.")
    
    with zfile.open('calendar.txt') as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            if row.get(current_day_column) == '1':
                service_days.add(row['service_id'])
                
    return service_days


def map_trips_for_target_routes(zfile, active_service_ids):
    """
    קריאת routes.txt ו-trips.txt, ומחזירה מפה של trip_id -> route_short_name 
    עבור הקווים הממוקדים והפעילים היום.
    """
    
    # route_id -> route_short_name
    route_id_to_short_name = {}
    # trip_id -> route_short_name (לקווים הממוקדים בלבד)
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
            
            # בדיקה משולשת: האם הקו ברשימת היעד, והאם הנסיעה פעילה היום?
            if route_short_name in TARGET_ROUTES and service_id in active_service_ids:
                target_trips_to_route[row['trip_id']] = route_short_name

    return target_trips_to_route


def extract_stop_times(zfile, target_trips_to_route):
    """
    קריאת stop_times.txt, מוצאת את זמני המוצא (stop_sequence=1)
    ומחזירה את הלו"ז הסופי.
    """
    # (route_short_name, stop_id) -> [times]
    final_schedule = defaultdict(lambda: defaultdict(list)) 
    
    all_target_trips = set(target_trips_to_route.keys())
    print(f"INFO: Extracting times for {len(all_target_trips)} target trips.")

    with zfile.open('stop_times.txt') as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
        for row in reader:
            trip_id = row['trip_id']
            
            if trip_id in all_target_trips:
                # אנחנו רוצים רק את תחנת המוצא
                if row['stop_sequence'] == '1': 
                    
                    route_short_name = target_trips_to_route[trip_id]
                    departure_time = row['departure_time'][:5] # HH:MM

                    # שמירת הנתונים: (קו, קוד_תחנה) -> רשימת זמנים
                    final_schedule[route_short_name][row['stop_id']].append(departure_time)
                    
    return final_schedule


def write_final_schedule(final_schedule, output_path):
    """
    כתיבת הלו"ז המעובד לקובץ הפלט schedule.txt.
    """
    print(f"INFO: Writing final schedule to {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for route_id, schedule_by_stop in final_schedule.items():
            for stop_id, times in schedule_by_stop.items():
                
                # סידור זמני המוצא
                sorted_times = sorted(times)
                times_str = ','.join(sorted_times)
                
                # הפורמט הסופי: [קו],[קוד_תחנה]:[זמן],[זמן]...
                outfile.write(f"{route_id},{stop_id}:{times_str}\n")
                    
    print(f"SUCCESS: Schedule generated for {len(final_schedule)} routes.")


# -----------------------------------------------------------------
# הפונקציה הראשית (נקראת ע"י download_gtfs.py)
# -----------------------------------------------------------------

def generate_schedule(zip_path, output_path):
    """
    פונקציית Wrapper המשלבת את כל שלבי הפארסינג.
    """
    try:
        current_day_index = get_current_gtfs_day()
        
        with zipfile.ZipFile(zip_path, 'r') as zfile:
            # 1. מציאת ה-Service IDs הפעילים היום
            active_service_ids = map_service_ids_for_today(zfile, current_day_index)
            
            # 2. מציאת הנסיעות (Trips) הרלוונטיות לקווים שלך ופעילות היום
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids)
            
            # 3. משיכת זמני המוצא מהנסיעות הרלוונטיות
            final_schedule = extract_stop_times(zfile, target_trips_to_route)
            
            # 4. שמירת הפלט
            write_final_schedule(final_schedule, output_path)

    except Exception as e:
        print(f"CRITICAL PARSING ERROR in generate_schedule: {e}")
        # מנקה את קובץ הפלט כדי למנוע Commit של נתונים שגויים
        try:
             import os
             if os.path.exists(output_path):
                 os.remove(output_path)
        except:
            pass
        raise e

# פונקציה תואמת עבור download_gtfs.py
def generate_data(zip_path, schedule_path, dates_path=None):
    """כדי לשמור על תאימות עם הקוד הקודם."""
    generate_schedule(zip_path, schedule_path)
