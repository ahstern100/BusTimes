// utils.js (מתוקן: שינוי ל-var כדי לאפשר שינוי גלובלי)

var STORAGE_KEY_DATA = "scheduleData";
var STORAGE_KEY_DATE = "scheduleDate";
var TODAY = new Date().toISOString().slice(0, 10); 

// פונקציות עזר כלליות

function logDebug(message) {
    const console = document.getElementById('debugConsole');
    const now = new Date().toLocaleTimeString('en-US', { hour12: false });
    const p = document.createElement('p');
    p.textContent = `[${now}] ${message}`;
    console.appendChild(p);
    console.scrollTop = console.scrollHeight;
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

function showFloatingMessage(message) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.classList.add('visible');
    
    setTimeout(() => {
        statusEl.classList.remove('visible');
    }, 10000); 
}

function clearLocalData() {
    logDebug('INFO: Clearing all schedule data...');
    // מנקה את המפתחות הנוכחיים (שהם V2 אם data_fetch רץ)
    localStorage.removeItem(STORAGE_KEY_DATA);
    localStorage.removeItem(STORAGE_KEY_DATE);
    // ניקוי מפתחות ישנים אם קיימים, למקרה שזה לא V2
    localStorage.removeItem("scheduleData");
    localStorage.removeItem("scheduleDate");
    
    logDebug('SUCCESS: Local schedule data cleared. Reloading page to fetch new data.');
    
    showFloatingMessage("נתונים מקומיים נמחקו. רענן את הדף ידנית.");
}