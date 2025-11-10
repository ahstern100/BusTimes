# gtfs_utils.py
import csv
import io
import os
import configparser
from collections import defaultdict
from datetime import datetime

# ----------------------------------------------------
# I. טעינת קונפיגורציה (העדכון העיקרי)
# ----------------------------------------------------

CONFIG_FILE = 'config.ini'

def load_config_data():
    """קורא את הקווים וקודי התחנות מקובץ התצורה ומעדכן את המשתנים הגלובליים."""
    
    config = configparser.ConfigParser()
    
    if not os.path.exists(CONFIG_FILE):
        print(f"CRITICAL ERROR: Configuration file not found: {CONFIG_FILE}. Using default hardcoded lists.")
        return # ישתמש ב-CRITICAL_STOP_CODES ו-TARGET_ROUTES כפי שהם מוגדרים למטה

    try:
        # קריאת הקובץ
        config.read(CONFIG_FILE, encoding='utf-8')
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to read config file {CONFIG_FILE}: {e}. Using default hardcoded lists.")
        return

    # קריאת קווים
    lines_list = []
    if 'LINES' in config:
        # קורא את כל המפתחות בסקשן 'LINES' כרשימה, ומנקה רווחים
        lines_list = [key.strip() for key in config['LINES'].keys() if key.strip()]
        
    # קריאת קודי תחנות
    stop_codes_set = set()
    if 'STOP_CODES' in config:
        # קורא את כל המפתחות בסקשן 'STOP_CODES' כסט, ומנקה רווחים
        stop_codes_set = {key.strip() for key in config['STOP_CODES'].keys() if key.strip()}

    # עדכון המשתנים הגלובליים
    global TARGET_ROUTES
    global CRITICAL_STOP_CODES
    
    if lines_list:
        TARGET_ROUTES = lines_list
        print(f"INFO: TARGET_ROUTES loaded from config: {TARGET_ROUTES}")
    else:
        print("WARNING: 'LINES' section is empty or missing in config. Using hardcoded TARGET_ROUTES.")

    if stop_codes_set:
        CRITICAL_STOP_CODES = stop_codes_set
        print(f"INFO: CRITICAL_STOP_CODES loaded from config: {CRITICAL_STOP_CODES}")
    else:
        print("WARNING: 'STOP_CODES' section is empty or missing in config. Using hardcoded CRITICAL_STOP_CODES.")


# --- הגדרות קבועות (ערכי ברירת מחדל אם הקונפיג נכשל/ריק) ---
TARGET_ROUTES = ['20', '20א', '22', '60', '60א', '71', '71א', '631', '632', '634', '63', '163', '160', '127']

# *** הקבוע הקריטי (הוא מכיל Stop Codes) ***
CRITICAL_STOP_CODES = {'43334', '43496', '40662'}

# Stop IDs שימולאו לאחר המיפוי ההפוך:
CRITICAL_STOP_IDS = set() 

# *** הרצת פונקציית הטעינה מיד לאחר הגדרת ברירות המחדל ***
load_config_data()
# ----------------------------------------------------


def clean_header(header):
    """מנקה BOM, רווחים לבנים ורווחים מובילים/נגררים משמות עמודות."""
    if not header: return []
    # טיפול ב-BOM רק באיבר הראשון
    first_item = header[0].strip().lstrip('\ufeff')
    cleaned_header = [first_item] + [h.strip() for h in header[1:]]
    return cleaned_header


def debug_print_file_contents(zfile, file_name):
    """מדפיס את שמות העמודות הנקיות של קובץ CSV בתוך ה-ZIP."""
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
        # אם הקובץ לא נמצא, נחזיר None כדי שהקוד הראשי יטפל בכשל
        return None
    except Exception as e:
        print(f"ERROR: Failed to read header from {file_name}: {e}")
        return None


def get_csv_dict_reader(zfile, file_name, cleaned_header):
    """מחזיר רשימה של שורות (כמילונים) באמצעות הכותרת הנקייה שהכנו."""
    with zfile.open(file_name) as f:
        text_wrapper = io.TextIOWrapper(f, encoding='utf-8')
        # מדלגים על שורת הכותרת בקובץ המקורי (כי כבר השתמשנו בה)
        next(text_wrapper)
        reader = csv.DictReader(text_wrapper, fieldnames=cleaned_header)
        return list(reader)


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
    # יום שני (Monday) הוא 0 ב-weekday(), אנחנו רוצים שבת (Saturday) 6, ראשון (Sunday) 0
    # לכן, (weekday() + 1) % 7
    day_index = (today.weekday() + 1) % 7 
    return date_str, day_index


def map_service_ids_for_today(zfile, current_day_index, zip_contents):
    """קריאת calendar.txt והחזרת סט של service_ids הפעילים היום."""
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
    *** מעודכן: מייצר מפות דו-כיווניות, כולל stop_name. ***
    1. stop_id -> {stop_code, stop_name} (לצורך פלט)
    2. stop_code -> stop_id (לצורך סינון גיאוגרפי)
    """
    stop_id_to_info = {} # מחזיק את המידע המלא (קוד ושם)
    stop_code_to_id = {}
    stops_file = 'stops.txt'
    
    stops_header = debug_print_file_contents(zfile, stops_file)
    if not stops_header or 'stop_id' not in stops_header or 'stop_code' not in stops_header or 'stop_name' not in stops_header:
        raise Exception(f"Required columns missing in {stops_file}. Cannot process stops.")

    print(f"INFO: Mapping stop IDs, codes, and names from {stops_file}.")
    stops_data = get_csv_dict_reader(zfile, stops_file, stops_header)
    
    for row in stops_data:
        s_id = row['stop_id']
        s_code = row['stop_code']
        s_name = row['stop_name'].strip() # ניקוי שם התחנה
        
        # 1. מפה רגילה (עבור הפלט): stop_id -> {stop_code, stop_name}
        # אם אין stop_code, נשתמש ב-stop_id
        code = s_code if s_code else s_id 
        stop_id_to_info[s_id] = {'code': code, 'name': s_name}

        # 2. מפה הפוכה (עבור הסינון)
        if s_code:
            stop_code_to_id[s_code] = s_id
        
    print(f"DEBUG: Mapped {len(stop_id_to_info)} stops. Found {len(stop_code_to_id)} unique stop codes.")
    return stop_id_to_info, stop_code_to_id

def convert_codes_to_ids(stop_code_to_id):
    """ממיר את CRITICAL_STOP_CODES ל-CRITICAL_STOP_IDS האמיתיים."""
    converted_ids = set()
    
    for code in CRITICAL_STOP_CODES:
        s_id = stop_code_to_id.get(code)
        if s_id:
            converted_ids.add(s_id)
        else:
            print(f"WARNING: Critical Stop Code {code} not found in stops.txt. Ignoring.")
            
    # עדכון המשתנה הגלובלי בתוך קובץ העזר
    global CRITICAL_STOP_IDS
    CRITICAL_STOP_IDS = converted_ids
    
    return converted_ids


def find_relevant_trips_by_stops(zfile, zip_contents):
    """ממפה רק Trips שעוברים באחת מה-CRITICAL_STOP_IDS."""
    relevant_trip_ids = set()
    stop_times_file = 'stop_times.txt'
    
    # משתמשים ב-CRITICAL_STOP_IDS הגלובלי שהוגדר ע"י convert_codes_to_ids
    if not CRITICAL_STOP_IDS:
        print("WARNING: CRITICAL_STOP_IDS is empty after conversion. Proceeding without geographic filtering.")
        return None 
        
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
    """ממפה נסיעות (trips) לקווים הממוקדים הפעילים היום והרלוונטיים גיאוגרפית."""
    route_id_to_short_name = {}
    target_trips_to_route = {} 

    # 1. routes.txt
    routes_file = 'routes.txt'
    routes_header = debug_print_file_contents(zfile, routes_file)
    print(f"INFO: Mapping route IDs from {routes_file}.")
    routes_data = get_csv_dict_reader(zfile, routes_file, routes_header)
    for row in routes_data:
        route_id_to_short_name[row['route_id']] = row['route_short_name']

    # 2. trips.txt
    trips_file = 'trips.txt'
    trips_header = debug_print_file_contents(zfile, trips_file)

    print(f"INFO: Mapping trips for target routes active today from {trips_file}.")
    trips_data = get_csv_dict_reader(zfile, trips_file, trips_header)
    for row in trips_data:
        route_short_name = route_id_to_short_name.get(row['route_id'])
        service_id = row['service_id']
        trip_id = row['trip_id']
        
        # סינון לפי קו ופעילות יום
        if route_short_name in TARGET_ROUTES and service_id in active_service_ids:
            
            # סינון גיאוגרפי
            if relevant_trip_ids is None or trip_id in relevant_trip_ids:
                target_trips_to_route[trip_id] = route_short_name

    print(f"DEBUG: Identified {len(target_trips_to_route)} relevant trips after filtering by stops and routes.")
    return target_trips_to_route


def extract_stop_times(zfile, target_trips_to_route, stop_id_to_info, zip_contents):
    """
    *** מעודכן: מוצא את שעות המוצא ומשייך ל-Route Short Name ול-{Stop Code, Stop Name}. ***
    """
    # המבנה של final_schedule:
    # { 'RouteName': { 'StopID': { 'code': 'XXX', 'name': 'YYY', 'times': [...] } } }
    final_schedule = defaultdict(lambda: {}) 
    all_target_trips = set(target_trips_to_route.keys())
    stop_times_file = 'stop_times.txt'
    stop_times_header = debug_print_file_contents(zfile, stop_times_file)
    
    print(f"INFO: Extracting departure times (stop_sequence=1) for {len(all_target_trips)} trips.")
    stop_times_data = get_csv_dict_reader(zfile, stop_times_file, stop_times_header)

    for row in stop_times_data:
        trip_id = row['trip_id']
        
        if trip_id in all_target_trips:
            # אנחנו מעוניינים רק בזמן היציאה של תחנת המוצא (של ה-Trip), שזה בדרך כלל stop_sequence=1
            if row['stop_sequence'] == '1': 
                
                route_short_name = target_trips_to_route[trip_id]
                departure_time = row['departure_time'][:5]
                stop_id = row['stop_id']
                
                # משיכת המידע המלא על התחנה
                stop_info = stop_id_to_info.get(stop_id)
                
                if stop_info:
                    # שימוש ב-Stop ID כמפתח פנימי למניעת כפילויות של Stop Code
                    if stop_id not in final_schedule[route_short_name]:
                        final_schedule[route_short_name][stop_id] = {
                            'code': stop_info['code'],
                            'name': stop_info['name'],
                            'times': []
                        }
                    
                    final_schedule[route_short_name][stop_id]['times'].append(departure_time)
                
    return final_schedule

def write_final_schedule(final_schedule, output_path):
    """
    *** מעודכן: כתיבת הפלט בפורמט: [Route_Short_Name]|[Stop_Code]|[Stop_Name]:[Times] ***
    """
    print(f"INFO: Writing schedule to {output_path}. Existing file will be overwritten.")
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        # מיון הקווים לפני כתיבה (כדי לשמור על סדר נעים יותר)
        sorted_routes = sorted(final_schedule.keys(), key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else x)

        for route_id in sorted_routes:
            schedule_by_id = final_schedule[route_id]
            cleaned_route_id = route_id.strip() 

            for stop_id, info in schedule_by_id.items():
                
                cleaned_stop_code = info['code'].strip() 
                cleaned_stop_name = info['name'].strip() # ודא ששם התחנה נקי מרווחים
                
                # מיון הזמנים לפני הפיצול
                sorted_times = sorted(info['times'])
                times_str = ','.join(sorted_times)
                
                # הפורמט החדש: RouteID|StopCode|StopName:Times
                outfile.write(f"{cleaned_route_id}|{cleaned_stop_code}|{cleaned_stop_name}:{times_str}\n")
                    
    print(f"SUCCESS: Schedule generated and written for {len(final_schedule)} routes.")
