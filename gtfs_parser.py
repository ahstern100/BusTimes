import zipfile
import csv
import io
from collections import defaultdict
from datetime import datetime

# --- הגדרות ---
# קווים שאתה רוצה לעקוב אחריהם (החלף במספרי הקווים שלך)
# לדוגמה: אם אתה נוסע בקווי 15 ו-42, שנה לרשימה זו.
TARGET_ROUTES = ['1', '2', '3'] # אנא שנה לרשימת הקווים שלך! 
OUTPUT_FILENAME = "schedule.txt"


def generate_schedule(zip_path, output_path):
    """
    מעבד קובץ GTFS, מוצא זמני מוצא לקווים נבחרים, ומחלק אותם לפי יום בשבוע.
    הפלט נכתב ל-schedule.txt.
    """
    
    # 1. מפות נדרשות מתוך קובצי ה-GTFS
    
    # route_id -> trip_id (איזה נסיעות שייכות לאיזה קו)
    trips_for_routes = defaultdict(list)
    # trip_id -> service_id (איזה נסיעה שייכת לאיזה מועד שירות)
    service_id_for_trip = {} 
    # service_id -> days (איזה מועד שירות פעיל באיזה ימים בשבוע)
    service_days = {} 
    # (route_id, day_index, stop_id) -> [times] (הלו"ז הסופי)
    final_schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:

            # --- א. מפה 1: ימים בשבוע (calendar.txt) ---
            # קובע איזה service_id (מועד שירות) פעיל באיזה ימים
            print("INFO: Processing calendar.txt...")
            with z.open('calendar.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                for row in reader:
                    days = []
                    # יום ראשון (0) עד שבת (6)
                    if row['sunday'] == '1': days.append(0)
                    if row['monday'] == '1': days.append(1)
                    if row['tuesday'] == '1': days.append(2)
                    if row['wednesday'] == '1': days.append(3)
                    if row['thursday'] == '1': days.append(4)
                    if row['friday'] == '1': days.append(5)
                    if row['saturday'] == '1': days.append(6)
                    
                    service_days[row['service_id']] = days
                    
            # --- ב. מפה 2: קווים ונסיעות (routes.txt ו-trips.txt) ---
            
            # קריאת routes.txt: route_id -> route_short_name (מספר קו)
            route_id_to_short_name = {}
            with z.open('routes.txt') as f:
                 reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                 for row in reader:
                     route_id_to_short_name[row['route_id']] = row['route_short_name']

            # קריאת trips.txt: route_short_name (קו) -> trip_id
            target_route_ids = set()
            with z.open('trips.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                for row in reader:
                    route_short_name = route_id_to_short_name.get(row['route_id'])
                    
                    if route_short_name in TARGET_ROUTES:
                        target_route_ids.add(row['route_id'])
                        trips_for_routes[route_short_name].append(row['trip_id'])
                        service_id_for_trip[row['trip_id']] = row['service_id']

            # --- ג. מפה 3: זמני נסיעה (stop_times.txt) ---
            
            # קריאת stop_times.txt: מציאת זמני מוצא (תחנה ראשונה בנסיעה)
            print("INFO: Processing stop_times.txt...")
            
            # סט של כל ה-trip_id שאנחנו צריכים לעקוב אחריהם
            all_target_trips = set(service_id_for_trip.keys())
            
            with z.open('stop_times.txt') as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
                for row in reader:
                    trip_id = row['trip_id']
                    
                    if trip_id in all_target_trips:
                        # אנחנו רוצים רק את תחנת המוצא
                        if row['stop_sequence'] == '1': 
                            
                            service_id = service_id_for_trip[trip_id]
                            # ימי השבוע שה-service_id הזה פעיל בהם (0-6)
                            active_days = service_days.get(service_id, []) 
                            
                            # מציאת מספר הקו
                            route_id = [k for k, v in trips_for_routes.items() if trip_id in v][0]

                            # פורמט זמן (שעתיים:דקות)
                            departure_time = row['departure_time'][:5] 
                            
                            # שמירת הנתונים לפי יום בשבוע
                            for day_index in active_days:
                                # מפתח: (קו, יום, קוד_תחנה) -> רשימת זמנים
                                final_schedule[route_id][day_index][row['stop_id']].append(departure_time)

        # --- 2. כתיבת הפלט לקובץ schedule.txt ---
        
        print(f"INFO: Writing final schedule to {output_path}...")
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for route_id, schedule_by_day in final_schedule.items():
                for day_index, schedule_by_stop in schedule_by_day.items():
                    for stop_id, times in schedule_by_stop.items():
                        
                        # סידור זמני המוצא
                        sorted_times = sorted(times)
                        times_str = ','.join(sorted_times)
                        
                        # הפורמט הסופי: [קו],[קוד_תחנה],[יום_בשבוע]:[זמן],[זמן]...
                        outfile.write(f"{route_id},{stop_id},{day_index}:{times_str}\n")
                        
        print(f"SUCCESS: Schedule generated for {len(final_schedule)} routes.")
        
    except Exception as e:
        print(f"CRITICAL PARSING ERROR: {e}")
        # אם נכשל, מוחקים את הקובץ כדי למנוע Commit של קובץ חלקי
        if os.path.exists(output_path):
             os.remove(output_path)
        raise e

# --- הפונקציה הראשית שנקראת ע"י download_gtfs.py ---
def generate_data(zip_path, schedule_path, dates_path=None):
    """
    Wrapper function to be called by download_gtfs.py.
    """
    # קוראים רק לפונקציה שאחראית על יצירת schedule.txt
    generate_schedule(zip_path, schedule_path)


if __name__ == '__main__':
    # דוגמה לשימוש מקומי (במקרה שתרצה להריץ על המחשב שלך)
    # generate_schedule('gtfs.zip', OUTPUT_FILENAME)
    pass
