import pandas as pd
import zipfile
import io
from datetime import datetime

# --- הגדרות משתמש קבועות ---
# הקווים הרצויים: חשוב להפריד בין קו '20' ל-'20א'
TARGET_LINES = [
    '20', '20א', '22', '60', '60א', '71', '71א', 
    '63', '632', '634', '160', '127', '163', '942'
]

# קודי התחנות הרצויים (stop_code)
TARGET_STOP_CODES = [43496, 40571, 40662]
# -----------------------------

def load_gtfs_files(zip_file_handler):
    """
    מתודה לטעינת קבצי ה-GTFS הנדרשים לתוך DataFrame של Pandas.
    היא מחזירה מילון של ה-DataFrames שנטענו.
    """
    file_list = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt']
    loaded_data = {}
    print("DEBUG: Starting file loading...")
    
    try:
        for filename in file_list:
            print(f"DEBUG: Loading {filename}...")
            # שימוש ב-TextIOWrapper עבור קריאה מקובץ בתוך ZIP עם קידוד UTF-8
            loaded_data[filename.replace('.txt', '_df')] = pd.read_csv(
                io.TextIOWrapper(zip_file_handler.open(filename), encoding='utf-8')
            )
            print(f"DEBUG: {filename} loaded successfully with {len(loaded_data[filename.replace('.txt', '_df')])} rows.")
            
        return loaded_data
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load GTFS files: {e}")
        raise

def filter_trips(data):
    """
    מתודה לסינון הנסיעות (Trips) הרלוונטיות:
    א. ששייכות לקווים המבוקשים (TARGET_LINES).
    ב. שעוברות באחת התחנות המבוקשות (TARGET_STOP_CODES).
    """
    print("DEBUG: Starting trip filtering process...")
    
    # 1. סינון קווים
    target_routes_df = data['routes_df'][
        data['routes_df']['route_short_name'].astype(str).isin(TARGET_LINES)
    ]
    target_route_ids = target_routes_df['route_id'].unique()
    print(f"DEBUG: Found {len(target_route_ids)} route_ids for target lines.")
    
    if not target_route_ids.size:
        print("WARNING: No matching route_id found for target lines. Returning empty.")
        return None, None
        
    # 2. סינון תחנות (stop_code -> stop_id)
    target_stops_df = data['stops_df'][
        data['stops_df']['stop_code'].astype(str).isin([str(c) for c in TARGET_STOP_CODES])
    ]
    target_stop_ids = target_stops_df['stop_id'].unique()
    print(f"DEBUG: Found {len(target_stop_ids)} stop_ids for target stop codes.")

    if not target_stop_ids.size:
        print("WARNING: No matching stop_id found for target stop codes. Returning empty.")
        return None, None
        
    # 3. מציאת נסיעות שעוצרות בתחנות הרצויות
    relevant_stop_times = data['stop_times_df'][
        data['stop_times_df']['stop_id'].isin(target_stop_ids)
    ]
    relevant_trip_ids = relevant_stop_times['trip_id'].unique()
    print(f"DEBUG: Found {len(relevant_trip_ids)} trips passing through target stops.")
    
    # 4. חיתוך: נסיעות ששייכות לקווים הרצויים וגם עוברות בתחנות הרצויות
    final_trips_df = data['trips_df'][
        data['trips_df']['route_id'].isin(target_route_ids) & 
        data['trips_df']['trip_id'].isin(relevant_trip_ids)
    ]
    
    if final_trips_df.empty:
        print("WARNING: No trips found matching BOTH line and stop filters. Returning empty.")
        return None, None

    print(f"DEBUG: Final filtered trips count: {len(final_trips_df)}")
    return final_trips_df, target_routes_df

def extract_departure_times(data, final_trips_df, target_routes_df):
    """
    מתודה לחילוץ זמני היציאה מתחנת המוצא של הנסיעות המסוננות, והסרת כפילויות.
    """
    print("DEBUG: Starting extraction of departure times...")
    final_trip_ids = final_trips_df['trip_id'].unique()

    # 1. קבלת כל זמני העצירה של הנסיעות המסוננות
    final_stop_times = data['stop_times_df'][
        data['stop_times_df']['trip_id'].isin(final_trip_ids)
    ]

    # 2. מציאת העצירה הראשונה (תחנת המוצא) של כל נסיעה
    first_stops_df = final_stop_times.loc[
        final_stop_times.groupby('trip_id')['stop_sequence'].idxmin()
    ]
    print(f"DEBUG: Identified first stop for {len(first_stops_df)} trips.")

    # 3. מיזוג נתונים לקבלת שם הקו ושם התחנה
    
    # קבלת route_id ושם הקו (route_short_name)
    result = pd.merge(
        first_stops_df, 
        final_trips_df[['trip_id', 'route_id']], 
        on='trip_id'
    )
    result = pd.merge(
        result,
        target_routes_df[['route_id', 'route_short_name']],
        on='route_id'
    )
    
    # קבלת שם התחנה
    result = pd.merge(
        result, 
        data['stops_df'][['stop_id', 'stop_name']],
        on='stop_id'
    )

    # 4. הסרת כפילויות (זמני יציאה זהים עבור אותו קו)
    result_schedule = result[[
        'route_short_name', 'departure_time', 'stop_id', 'stop_name'
    ]].copy()
    
    initial_count = len(result_schedule)
    result_schedule.drop_duplicates(
        subset=['route_short_name', 'departure_time'], 
        keep='first', 
        inplace=True
    )
    final_count = len(result_schedule)
    print(f"DEBUG: Removed {initial_count - final_count} duplicate departure times.")

    # 5. סידור וארגון
    result_schedule.sort_values(
        by=['route_short_name', 'departure_time'], 
        inplace=True
    )
    
    print("DEBUG: Extraction and deduplication complete.")
    return result_schedule

def save_schedule_to_file(schedule_df, output_path):
    """
    מתודה לשמירת ה-DataFrame של הלו"ז לקובץ טקסט מסודר.
    """
    print(f"DEBUG: Starting save operation to {output_path}")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"--- Bus Departure Schedule Generated on {current_time} ---\n")
        f.write(f"Target Lines: {', '.join(TARGET_LINES)}\n")
        f.write(f"Filter Stops (Codes): {', '.join(map(str, TARGET_STOP_CODES))}\n\n")
        
        # כתיבה מסודרת של לו"ז לכל קו
        for line in sorted(schedule_df['route_short_name'].unique()):
            line_data = schedule_df[schedule_df['route_short_name'] == line]
            
            # מציאת תחנת המוצא (היא זהה לכל הנסיעות של אותו קו בתוצאה)
            origin_stop_name = line_data['stop_name'].iloc[0]
            origin_stop_id = line_data['stop_id'].iloc[0]
            
            f.write(f"** Line {line} **\n")
            f.write(f"Origin Stop: {origin_stop_name} (ID: {origin_stop_id})\n")
            
            # איסוף ופורמט זמני היציאה
            times = ', '.join(line_data['departure_time'].tolist())
            f.write(f"Departure Times: {times}\n\n")

    print(f"SUCCESS: Final schedule saved to {output_path}.")


def generate_schedule(gtfs_zip_path, output_schedule_path):
    """
    המתודה הראשית המשלבת את כל השלבים. זו המתודה שנקראת מתוך download_gtfs.py.
    """
    print(f"DEBUG: generate_schedule called for file: {gtfs_zip_path}")
    
    try:
        with zipfile.ZipFile(gtfs_zip_path, 'r') as zf:
            
            # 1. טעינת קבצי ה-GTFS
            data = load_gtfs_files(zf)
            
            # 2. סינון נסיעות (Trips)
            final_trips_df, target_routes_df = filter_trips(data)
            
            if final_trips_df is None:
                print("PROCESS HALTED: No relevant trips found after filtering.")
                # שמירה של קובץ ריק במקרה של כשלון
                with open(output_schedule_path, 'w', encoding='utf-8') as f:
                    f.write("No matching schedules found.")
                return

            # 3. חילוץ זמני יציאה והסרת כפילויות
            schedule_df = extract_departure_times(data, final_trips_df, target_routes_df)
            
            if schedule_df.empty:
                print("PROCESS HALTED: Schedule DataFrame is empty after extraction/deduplication.")
                return

            # 4. שמירת התוצאות לקובץ
            save_schedule_to_file(schedule_df, output_schedule_path)
            
    except zipfile.BadZipFile:
        print(f"CRITICAL ERROR: The file {gtfs_zip_path} is not a valid ZIP file.")
    except FileNotFoundError:
        print(f"CRITICAL ERROR: GTFS file not found at {gtfs_zip_path}.")
    except Exception as e:
        print(f"CRITICAL ERROR: An unexpected error occurred in generate_schedule: {e}")
        raise


if __name__ == '__main__':
    print("gtfs_parser.py loaded. This file should be run via download_gtfs.py.")
