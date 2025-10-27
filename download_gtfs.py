name: Daily GTFS Fetch and Schedule Generation

on:
  # הרצה יומית בשעה 03:00 UTC (06:00 או 05:00 בוקר בישראל)
  schedule:
    - cron: '0 3 * * *'
  # מאפשר הרצה ידנית מהממשק הגרפי
  workflow_dispatch:

jobs:
  fetch_and_commit:
    # ודא כי הרפוזיטורי הוא BusTimes
    name: Running on BusTimes
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository code
        # מוריד את הקוד של הרפוזיטורי
        uses: actions/checkout@v4
        with:
          # חיוני כדי לאפשר לקוד לבצע Commit חדש
          token: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Set up Python
        # הגדרת סביבת Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10' # משתמשים בגרסה יציבה
          
      - name: Install dependencies (requests and pandas)
        # התקנת ספריות Python הנדרשות
        run: |
          echo "DEBUG: Installing requests and pandas..."
          pip install requests pandas
          echo "DEBUG: Installation complete."

      - name: Run GTFS Download and Parsing Script
        # מריץ את קובץ הראשי שלנו
        id: run_script
        run: |
          echo "DEBUG: Starting download_gtfs.py..."
          python download_gtfs.py
          echo "DEBUG: Script finished."
      
      - name: Commit files if changed (GTFS.zip and schedule.txt)
        # משתמש ב-Action של צד שלישי לביצוע Add ו-Commit
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: ${{ steps.run_script.outputs.commit_message }}
          # קבלת רשימת הקבצים ל-Commit מקובץ הפייתון
          files: ${{ steps.run_script.outputs.files_to_commit }}
          # מאפשר ריצה אוטומטית גם אם אין שינויים (כדי לא לשבור את ה-workflow)
          commit_options: '--allow-empty'
          skip_dirty_check: true # דילוג על בדיקה כדי לוודא שאין תקיעות
          
      - name: Final Success Check
        if: success()
        run: echo "SUCCESS: Action completed. Check the 'BusTimes' repository for the updated files."
