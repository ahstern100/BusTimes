import zipfile
import csv
import io
import os
from collections import defaultdict
from datetime import datetime

# --- הגדרות קבועות ---
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']
OUTPUT_FILENAME = "schedule.txt"

# *** הקבוע הקריטי (הוא מכיל Stop Codes) ***
CRITICAL_STOP_CODES = {'43334', '43496', '40662'}
# Stop IDs שימולאו לאחר המיפוי ההפוך:
CRITICAL_STOP_IDS = set() 


def clean_header(header):
    """מנקה BOM, רווחים לבנים ורווחים מובילים/נגררים משמות עמודות."""
    if not header: return []
    first_item = header[0].strip().lstrip('\ufeff')
    cleaned_header = [first_item] + [h.strip() for h in header[1:]]
    return cleaned_header


def debug_print_file_contents(zfile, file_name):
    # ... (פונקציה זהה) ...
    try:
        with zfile.open(file_name) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8'))
            header = next(reader, None)
            cleaned_header = clean_header(header)
            if cleaned_header:
                print(f"DEBUG: Cleaned Header for {file_name}: {cleaned_header}")
            else:
                print(f"WARNING: {file_name} appears to be empty or missing header.")
            return cleaned_header
    except KeyError:
        print(f"ERROR: File {file_name} not found in ZIP.")
        return None
    except Exception as e:
        print(f"ERROR: Failed to read header from {file_name}: {e}")
        return None


def get_csv_dict_reader(zfile, file_name, cleaned_header):
    # ... (פונקציה זהה) ...
    with zfile.open(file_name) as f:
        text_wrapper = io.TextIOWrapper(f, encoding='utf-8')
        next(text_wrapper)
        reader = csv.DictReader(text_wrapper, fieldnames=cleaned_header)
        return list(reader)


def get_current_day_info():
    # ... (פונקציה זהה) ...
    today = datetime.today()
    date_str = today.strftime('%Y%m%d')
    day_index = (today.weekday() + 1) % 7
    return date_str, day_index


def map_service_ids_for_today(zfile, current_day_index, zip_contents):
    # ... (פונקציה זהה) ...
    active_service_ids = set()
    calendar_file = 'calendar.txt'
    
    if calendar_file not in zip_contents: raise Exception(f"File {calendar_file} is not in the archive!")
    header = debug_print_file_contents(zfile, calendar_file)
    if not header or 'service_id' not in header:
        raise Exception(f"Header check failed for {calendar_file}. 'service_id' column is missing.")
        
    day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 4: 'thursday', 5: 'friday', 6: 'saturday'}
    current_day_column = day_map.get(current_day_index)
    
    print(f"INFO: Processing {calendar_file} to map active service IDs based on column '{current_day_column}'.")
    calendar_data = get_csv_dict_reader(zfile, calendar_file, header)
    
    for row in calendar_data:
        if row.get(current_day_column) == '1':
            active_service_ids.add(row['service_id'])
            
    print(f"DEBUG: Found {len(active_service_ids)} active service IDs.")
    return active_service_ids


def map_stop_info(zfile, zip_contents):
    """
    *** מעודכן: קורא stops.txt ומייצר מפות דו-כיווניות:
    1. stop_id -> stop_code
    2. stop_code -> stop_id (לצורך סינון גיאוגרפי)
    """
    stop_id_to_code = {}
    stop_code_to_id = {}
    stops_file = 'stops.txt'
    
    if stops_file not in zip_contents: 
        raise Exception(f"File {stops_file} not found. Cannot process stops.")
        
    stops_header = debug_print_file_contents(zfile, stops_file)
    if 'stop_id' not in stops_header or 'stop_code' not in stops_header:
        raise Exception(f"Required columns missing in {stops_file}. Cannot process stops.")

    print(f"INFO: Mapping stop IDs and codes from {stops_file}.")
    stops_data = get_csv_dict_reader(zfile, stops_file, stops_header)
    
    for row in stops_data:
        s_id = row['stop_id']
        s_code = row['stop_code']
        
        # 1. מפה רגילה (עבור הפלט)
        # אם stop_code ריק, נשתמש ב-stop_id
        code = s_code if s_code else s_id 
        stop_id_to_code[s_id] = code

        # 2. מפה הפוכה (עבור הסינון) - רק אם יש stop_code
        if s_code:
            stop_code_to_id[s_code] = s_id
        
    print(f"DEBUG: Mapped {len(stop_id_to_code)} stops. Found {len(stop_code_to_id)} unique stop codes.")
    return stop_id_to_code, stop_code_to_id


def convert_codes_to_ids(stop_code_to_id):
    """
    *** חדש: ממיר את CRITICAL_STOP_CODES ל-CRITICAL_STOP_IDS האמיתיים ***
    """
    converted_ids = set()
    
    for code in CRITICAL_STOP_CODES:
        s_id = stop_code_to_id.get(code)
        if s_id:
            converted_ids.add(s_id)
        else:
            print(f"WARNING: Critical Stop Code {code} not found in stops.txt. Ignoring.")
            
    # עדכון הגלובלי CRITICAL_STOP_IDS
    global CRITICAL_STOP_IDS
    CRITICAL_STOP_IDS = converted_ids
    
    return converted_ids


def find_relevant_trips_by_stops(zfile, zip_contents):
    """
    ממפה רק Trips שעוברים באחת מה-CRITICAL_STOP_IDS (שכבר מופו מה-Stop Codes).
    """
    relevant_trip_ids = set()
    stop_times_file = 'stop_times.txt'
    
    if not CRITICAL_STOP_IDS:
        print("WARNING: CRITICAL_STOP_IDS is empty after conversion. Proceeding without geographic filtering.")
        return None # נחזיר None כדי לציין שאין סינון
        
    if stop_times_file not in zip_contents: raise Exception(f"File {stop_times_file} is not in the archive!")
    stop_times_header = debug_print_file_contents(zfile, stop_times_file)
    
    print(f"INFO: Filtering trips by critical stop IDs: {CRITICAL_STOP_IDS}")
    stop_times_data = get_csv_dict_reader(zfile, stop_times_file, stop_times_header)

    for row in stop_times_data:
        if row['stop_id'] in CRITICAL_STOP_IDS:
            relevant_trip_ids.add(row['trip_id'])
            
    print(f"DEBUG: Identified {len(relevant_trip_ids)} trips that pass through the critical stops (using mapped IDs).")
    return relevant_trip_ids


def map_trips_for_target_routes(zfile, active_service_ids, relevant_trip_ids, zip_contents):
    # ... (פונקציה זו זהה ועכשיו עובדת עם ה-relevant_trip_ids המסוננים נכון) ...
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # --- 1. routes.txt ---
    routes_file = 'routes.txt'
    routes_header = debug_print_file_contents(zfile, routes_file)
    print(f"INFO: Mapping route IDs from {routes_file}.")
    routes_data = get_csv_dict_reader(zfile, routes_file, routes_header)
    for row in routes_data:
        route_id_to_short_name[row['route_id']] = row['route_short_name']

    # --- 2. trips.txt ---
    trips_file = 'trips.txt'
    trips_header = debug_print_file_contents(zfile, trips_file)

    print(f"INFO: Mapping trips for target routes active today from {trips_file}.")
    trips_data = get_csv_dict_reader(zfile, trips_file, trips_header)
    for row in trips_data:
        route_short_name = route_id_to_short_name.get(row['route_id'])
        service_id = row['service_id']
        trip_id = row['trip_id']
        
        # שלב 1: סינון לפי קו ופעילות יום
        if route_short_name in TARGET_ROUTES and service_id in active_service_ids:
            
            # שלב 2: סינון גיאוגרפי
            if relevant_trip_ids is None or trip_id in relevant_trip_ids:
                target_trips_to_route[trip_id] = route_short_name

    print(f"DEBUG: Identified {len(target_trips_to_route)} relevant trips after filtering by stops and routes.")
    return target_trips_to_route


def extract_stop_times(zfile, target_trips_to_route, stop_id_to_code, zip_contents):
    # ... (פונקציה זו זהה ועכשיו היא משתמשת ב-stop_id_to_code הנקי) ...
    final_schedule = defaultdict(lambda: defaultdict(list)) 
    all_target_trips = set(target_trips_to_route.keys())
    stop_times_file = 'stop_times.txt'
    stop_times_header = debug_print_file_contents(zfile, stop_times_file)
    
    print(f"INFO: Extracting departure times (stop_sequence=1) for {len(all_target_trips)} trips.")
    stop_times_data = get_csv_dict_reader(zfile, stop_times_file, stop_times_header)

    for row in stop_times_data:
        trip_id = row['trip_id']
        
        if trip_id in all_target_trips:
            if row['stop_sequence'] == '1': 
                
                route_short_name = target_trips_to_route[trip_id]
                departure_time = row['departure_time'][:5]
                stop_id = row['stop_id']
                
                # המרה מ-stop_id ל-stop_code
                output_stop_code = stop_id_to_code.get(stop_id, stop_id)

                final_schedule[route_short_name][output_stop_code].append(departure_time)
                
    return final_schedule


def write_final_schedule(final_schedule, output_path):
    # ... (פונקציה זהה) ...
    print(f"INFO: Writing schedule to {output_path}. Existing file will be overwritten.")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for route_id, schedule_by_stop in final_schedule.items():
            for stop_code, times in schedule_by_stop.items():
                
                sorted_times = sorted(times)
                times_str = ','.join(sorted_times)
                
                outfile.write(f"{route_id},{stop_code}:{times_str}\n")
                    
    print(f"SUCCESS: Schedule generated and written for {len(final_schedule)} routes.")


# -----------------------------------------------------------------
# הפונקציה הראשית
# -----------------------------------------------------------------

def generate_schedule(zip_path, output_path):
    """פונקציית Wrapper המשלבת את כל שלבי הפארסינג."""
    try:
        today_date_str, current_day_index = get_current_day_info()
        print(f"DEBUG: Processing for date {today_date_str}. Day index: {current_day_index} (0=Sun).")
        
        with zipfile.ZipFile(zip_path, 'r') as zfile:
            
            zip_contents = list_zip_contents(zfile)
            
            # שלב 1: מציאת ה-Service IDs הפעילים היום
            active_service_ids = map_service_ids_for_today(zfile, current_day_index, zip_contents)
            
            if not active_service_ids:
                 raise Exception(f"No active service IDs found. No service is scheduled for this day/time frame.")
            
            # *** תיקון קריטי: שלב 2-3: מיפוי קוד לתעודת זהות ***
            stop_id_to_code, stop_code_to_id = map_stop_info(zfile, zip_contents)
            
            # המרת הקבועים החיצוניים (Stop Codes) ל-Stop IDs פנימיים
            converted_ids = convert_codes_to_ids(stop_code_to_id)

            if not converted_ids:
                print("WARNING: No valid Stop IDs found for the critical Stop Codes. Proceeding without geographic filter.")
            
            # שלב 4: סינון גיאוגרפי - מציאת ה-Trips שעוברים ב-IDs הנכונים
            relevant_trip_ids = find_relevant_trips_by_stops(zfile, zip_contents)
            
            # שלב 5: מציאת הנסיעות (Trips) הרלוונטיות לאחר סינון כפול (קו + גיאוגרפיה)
            target_trips_to_route = map_trips_for_target_routes(zfile, active_service_ids, relevant_trip_ids, zip_contents)
            
            if not target_trips_to_route:
                raise Exception(f"No relevant trips found for target routes today. Check that the routes are active and pass through the critical stops.")
            
            # שלב 6: משיכת שעות המוצא (משתמש ב-stop_id_to_code לפלט)
            final_schedule = extract_stop_times(zfile, target_trips_to_route, stop_id_to_code, zip_contents)
            
            # שלב 7: שמירת הפלט
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
