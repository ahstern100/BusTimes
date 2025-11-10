// schedule.js (עדכון סופי: UI, לוגיקה, פיצול בטוח, כולל פונקציות דיבוג)

// *** עדכן את ה-URL לפרטים שלך! ***
const GITHUB_RAW_URL = "https://raw.githubusercontent.com/ahstern100/BusTimes/main/schedule.txt"; 

const STORAGE_KEY_DATA = "scheduleData";
const STORAGE_KEY_DATE = "scheduleDate";
const TODAY = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

// המבנה החדש של scheduleData: 
// { "RouteID|StopCode": { routeId: 'X', stopCode: 'Y', name: 'StopName', times: [...] } }
let scheduleData = {}; 

// ----------------------------------------------------
// I. פונקציות דיבוג ויזואלי והגדרות
// ----------------------------------------------------

function logDebug(message) {
    const console = document.getElementById('debugConsole');
    const now = new Date().toLocaleTimeString('en-US', { hour12: false });
    const p = document.createElement('p');
    p.textContent = `[${now}] ${message}`;
    console.appendChild(p);
    console.scrollTop = console.scrollHeight;
}

// *** פונקציות העתקה שהיו חסרות ***
function copyLog() {
    const console = document.getElementById('debugConsole');
    const textToCopy = console.innerText;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy)
            .then(() => alert('יומן הדיבוג הועתק בהצלחה!'))
            .catch(err => {
                fallbackCopyTextToClipboard(textToCopy);
            });
    } else {
        fallbackCopyTextToClipboard(textToCopy);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed"; 
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        const successful = document.execCommand('copy');
        alert(successful ? 'יומן הדיבוג הועתק בהצלחה! (Fallback)' : 'שגיאה בהעתקה.');
    } catch (err) {
        alert('שגיאה: לא ניתן להעתיק את היומן.');
    }
    document.body.removeChild(textArea);
}
// **********************************

// ב. פונקציה להצגת הודעה צפה
function showFloatingMessage(message) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.classList.add('visible');
    
    // הסתרת ההודעה אחרי 10 שניות
    setTimeout(() => {
        statusEl.classList.remove('visible');
    }, 10000); 
}

function clearLocalData() {
    logDebug('INFO: Clearing local storage data...');
    localStorage.removeItem(STORAGE_KEY_DATA);
    localStorage.removeItem(STORAGE_KEY_DATE);
    logDebug('SUCCESS: Local schedule data cleared. Reloading page to fetch new data.');
    
    // ב. הצגת הודעה צפה
    showFloatingMessage("נתונים מקומיים נמחקו. רענן את הדף ידנית.");
}


// ----------------------------------------------------
// II. לוגיקת טעינה וסנכרון
// ----------------------------------------------------

function init() {
    logDebug('INFO: Application initialized.');
    
    document.getElementById('copyLogBtn').onclick = copyLog; 
    document.getElementById('routeSelect').onchange = displayTimes;
    document.getElementById('clearCacheBtn').onclick = clearLocalData; 
    
    const lastUpdateDate = localStorage.getItem(STORAGE_KEY_DATE);
    
    if (lastUpdateDate === TODAY && localStorage.getItem(STORAGE_KEY_DATA)) {
        showFloatingMessage("נתונים עדכניים נטענו מהזיכרון המקומי.");
        logDebug(`DEBUG: Data is current for ${TODAY}. Loading from localStorage.`);
        loadData();
    } else {
        showFloatingMessage("מוריד נתונים חדשים מ-GitHub...");
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
        
        localStorage.setItem(STORAGE_KEY_DATA, data);
        localStorage.setItem(STORAGE_KEY_DATE, TODAY);
        
        // ב. הצגת הודעה צפה על הצלחה
        showFloatingMessage("✔ לוח זמנים עודכן בהצלחה.");
        
        loadData();

    } catch (error) {
        logDebug(`CRITICAL ERROR: Failed to fetch or process data: ${error.message}`);
        showFloatingMessage(`❌ שגיאה בהורדה. מציג נתונים ישנים (אם קיימים).`);
        loadData();
    }
}

// ----------------------------------------------------
// III. פענוח, ממשק ותצוגה
// ----------------------------------------------------

function loadData() {
    const rawData = localStorage.getItem(STORAGE_KEY_DATA);
    if (!rawData) {
        logDebug('ERROR: No raw data found in localStorage to load.');
        showFloatingMessage("❌ אין נתונים זמינים.");
        return;
    }

    logDebug('INFO: Starting data parsing.');
    const lines = rawData.trim().split('\n');
    scheduleData = {}; // אתחול מחדש

    lines.forEach((line, lineIndex) => {
        
        const lineTrimmed = line.trim();
        if (!lineTrimmed) return;
        
        const parts = lineTrimmed.split(':'); 
        
        if (parts.length < 2) {
             return;
        }

        const routeStopName = parts[0]; 
        const timesStrRaw = parts.slice(1).join(':'); 
        
        const timesStr = timesStrRaw.replace(/[\r\n]+/g, '').trim(); 
        
        if (!timesStr) {
             return;
        }
        
        const routeParts = routeStopName.split('|'); 

        if (routeParts.length !== 3) {
             return;
        }

        const [routeId, stopCode, stopName] = routeParts.map(p => p.trim());
        
        let rawTimes = timesStr.split(',');
        let departureTimes = []; 

        rawTimes.forEach(time => {
            const timeTrimmed = time.trim();
            const timeLength = timeTrimmed.length;
            const isValid = timeLength === 5 && timeTrimmed.includes(':');

            if (isValid) {
                departureTimes.push(timeTrimmed);
            } 
        });
        
        if (routeId && stopCode && stopName && departureTimes.length > 0) {
            // ה. שמירת הנתונים לפי מפתח משולב (קו + קוד תחנה)
            const key = `${routeId}|${stopCode}`;
            scheduleData[key] = {
                routeId: routeId,
                stopCode: stopCode,
                name: stopName,
                times: departureTimes
            };
        }
    });
    
    logDebug(`DEBUG: Successfully parsed ${Object.keys(scheduleData).length} unique route/stop combinations.`);
    populateUI();
}

function populateUI() {
    const select = document.getElementById('routeSelect');
    select.innerHTML = '';
    
    const sortedKeys = Object.keys(scheduleData).sort((a, b) => {
        // מיון לפי RouteId (מספרית)
        const routeIdA = scheduleData[a].routeId;
        const routeIdB = scheduleData[b].routeId;
        const numA = parseInt(routeIdA.replace(/\D/g, ''));
        const numB = parseInt(routeIdB.replace(/\D/g, ''));
        if (numA !== numB) return numA - numB;
        // ואז מיון לפי StopCode (מספרית)
        return parseInt(scheduleData[a].stopCode) - parseInt(scheduleData[b].stopCode);
    });
    
    logDebug(`DEBUG: Populating dropdown with ${sortedKeys.length} items.`);

    sortedKeys.forEach(key => {
        const item = scheduleData[key];
        const option = document.createElement('option');
        option.value = key; // המפתח המשולב
        
        // ה. תצוגת הפריט ב-Dropdown: "22 - קידמה/התמדה (43484)"
        option.textContent = `${item.routeId} - ${item.name} (${item.stopCode})`;
        select.appendChild(option);
    });

    if (sortedKeys.length > 0) {
        displayTimes();
    } else {
        showFloatingMessage("❌ אין קווים זמינים להיום.");
        logDebug("ERROR: No route data available after parsing.");
    }
}

// ד. פונקציה להשוואת זמנים ואיתור הזמן הקרוב
function findNextTime(times) {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    
    let nextTime = null;
    let minDiff = Infinity;

    for (const time of times) {
        const [hour, minute] = time.split(':').map(Number);
        const timeMinutes = hour * 60 + minute;
        
        let diff = timeMinutes - currentMinutes;
        
        // אם עבר חצות, הוסף 24 שעות כדי למצוא את האוטובוסים של היום הבא
        if (diff < 0) {
            diff += 24 * 60; 
        }

        if (diff >= 0 && diff < minDiff) {
            minDiff = diff;
            nextTime = time;
        }
    }
    
    return nextTime;
}


function displayTimes() {
    const key = document.getElementById('routeSelect').value;
    const stopCodeDisplay = document.getElementById('stopCodeDisplay');
    const stopNameDisplay = document.getElementById('stopNameDisplay'); 
    const timesList = document.getElementById('timesList');
    
    timesList.innerHTML = '';
    
    if (!key || !scheduleData[key]) {
        stopCodeDisplay.innerHTML = '';
        stopNameDisplay.innerHTML = ''; 
        return;
    }

    const stopInfo = scheduleData[key];

    logDebug(`INFO: Displaying schedule for Key ${key}.`);

    stopNameDisplay.innerHTML = `<b>תחנת מוצא:</b> ${stopInfo.name}`;
    stopCodeDisplay.innerHTML = `<b>קוד תחנה:</b> ${stopInfo.stopCode}`;
    
    const times = stopInfo.times;
    
    // ד. איתור הזמן הקרוב
    const nextTime = findNextTime(times);
    
    logDebug(`DEBUG: Found ${times.length} departure times. Next time: ${nextTime}.`);

    times.forEach(time => {
        const listItem = document.createElement('li');
        listItem.textContent = time;
        listItem.className = 'times';
        
        // ד. סימון הזמן הקרוב
        if (time === nextTime) {
            listItem.classList.add('next-time');
            // גלול לזמן הקרוב
            listItem.scrollIntoView({ behavior: 'smooth', block: 'center' }); 
        }
        
        timesList.appendChild(listItem);
    });
}

document.addEventListener('DOMContentLoaded', init);