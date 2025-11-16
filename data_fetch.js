// data_fetch.js (מתוקן: הסרת הצהרות כפולות ועדכון מפתחות גלובליים ל-V2)

// הגדרת קבוע עבור URL בלבד, כיוון שהוא מיוחד לקובץ זה
const GITHUB_RAW_URL = "https://raw.githubusercontent.com/ahstern100/BusTimes/main/schedule2.txt"; 

// *** עדכון ערכי המפתחות הגלובליים שהוצהרו ב-utils.js ***
// (אין const/let/var כאן כדי למנוע את שגיאת הכפילות)
STORAGE_KEY_DATA = "scheduleData_V2"; 
STORAGE_KEY_DATE = "scheduleDate_V2";


// פונקציות טעינה ו-INIT

function init() {
    logDebug('INFO: Application initialized. Binding controls.');
    
    // קשירת כפתורים
    const copyBtn = document.getElementById('copyLogBtn');
    if (copyBtn) {
        copyBtn.onclick = copyLog; 
    } else {
        logDebug('ERROR: Could not find element #copyLogBtn.');
    }

    const clearBtn = document.getElementById('clearCacheBtn');
    if (clearBtn) {
        clearBtn.onclick = clearLocalData; 
    } else {
        logDebug('ERROR: Could not find element #clearCacheBtn.');
    }

    // לוגיקת טעינת הנתונים: משתמש במשתנים הגלובליים המעודכנים (V2)
    const lastUpdateDate = localStorage.getItem(STORAGE_KEY_DATE);
    
    if (lastUpdateDate === TODAY && localStorage.getItem(STORAGE_KEY_DATA)) {
        showFloatingMessage("נתונים עדכניים נטענו מהזיכרון המקומי.");
        logDebug(`DEBUG: Data is current for ${TODAY}. Loading from localStorage.`);
        loadData();
    } else {
        showFloatingMessage("מוריד נתונים שבועיים חדשים מ-GitHub...");
        logDebug(`DEBUG: Data is either old (${lastUpdateDate}) or missing. Fetching new data.`);
        fetchData();
    }
}

async function fetchData() {
    logDebug(`DEBUG: Fetching data from ${GITHUB_RAW_URL}`);
    try {
        const response = await fetch(GITHUB_RAW_URL);
        
        if (!response.ok) {
            logDebug(`ERROR: HTTP request failed with status ${response.status}.`);
            throw new Error(`שגיאת HTTP: ${response.status}`);
        }
        
        const data = await response.text();
        
        if (data.includes('<html>') || data.length < 100) { 
             logDebug(`WARNING: Downloaded file size is very small (${data.length} bytes). Might be an error page.`);
        } else {
             logDebug(`DEBUG: Successfully downloaded ${data.length} bytes.`);
        }
        
        // שמירה באמצעות המפתחות הגלובליים המעודכנים (V2)
        localStorage.setItem(STORAGE_KEY_DATA, data);
        localStorage.setItem(STORAGE_KEY_DATE, TODAY);
        
        showFloatingMessage("✔ לוח זמנים שבועי עודכן בהצלחה.");
        
        loadData();

    } catch (error) {
        logDebug(`CRITICAL ERROR: Failed to fetch or process data: ${error.message}`);
        showFloatingMessage(`❌ שגיאה בהורדה. מציג נתונים ישנים (אם קיימים).`);
        loadData();
    }
}

function loadData() {
    // קריאה באמצעות המפתחות הגלובליים המעודכנים (V2)
    const rawData = localStorage.getItem(STORAGE_KEY_DATA);
    
    const success = processRawData(rawData); 
    
    if (success) {
        initializeUI(); 
    }
}

document.addEventListener('DOMContentLoaded', init);