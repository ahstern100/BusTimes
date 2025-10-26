import requests
import os
from datetime import datetime

# כתובת ה-URL לקובץ ה-GTFS (יש לוודא שהיא עדכנית!)
GTFS_URL = "https://gtfs.mot.gov.il/gtfsfiles/gtfs.zip"
OUTPUT_FILENAME = "gtfs.zip"

def download_file(url, filename):
    """מוריד קובץ מ-URL ושומר אותו."""
    print(f"Starting download from {url}...")
    
    # שליחת בקשת HTTP
    response = requests.get(url, stream=True)
    response.raise_for_status() 

    # שמירת הקובץ
    with open(filename, 'wb') as f:
        # שמירה בפלחים (chunks) כדי לחסוך בזיכרון 
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"File successfully downloaded and saved as {filename}.")

if __name__ == "__main__':
    download_file(GTFS_URL, OUTPUT_FILENAME)
    
    # הדפסת הודעה ליומן (לצורך מעקב ב-Action)
    print(f"::set-output name=commit_message::GTFS Update for {datetime.now().strftime('%Y-%m-%d')}")
