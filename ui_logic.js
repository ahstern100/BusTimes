// ui_logic.js (הגרסה המתוקנת - הוסרו הצהרות כפולות + תמיכה בבחירת יום)

// משתנים גלובליים (מוגדרים ב-data_process.js, נגישים כאן):
// scheduleData, groupedScheduleData, currentRouteId, currentDayOffset

let currentStopKey = null; // משתנה זה מוגדר רק כאן
const DAY_BUTTON_COUNT = 7; 

function initializeUI() {
    // 1. יוצרים את כפתורי הימים (בפעם הראשונה)
    populateDayButtons();
    
    // 2. יוצרים את כפתורי הקווים (וברירת המחדל שלהם תפעיל את שאר ה-UI)
    populateRouteButtons();
}


// *** פונקציות לניהול ימים ***

function populateDayButtons() {
    const container = document.getElementById('dayButtonsContainer');
    container.innerHTML = '';
    
    // יצירת 7 כפתורי ימים (0 עד 6)
    for (let i = 0; i < DAY_BUTTON_COUNT; i++) {
        const button = document.createElement('button');
        button.className = 'day-button';
        button.textContent = getDayName(i); // קורא לפונקציה מ-data_process.js
        button.dataset.dayOffset = i;
        button.onclick = () => handleDaySelect(i, button);
        container.appendChild(button);
    }
    
    // ברירת מחדל: בחירת היום הנוכחי (Offset 0)
    const firstButton = container.querySelector(`[data-day-offset="${currentDayOffset}"]`);
    if (firstButton) {
        handleDaySelect(currentDayOffset, firstButton);
    }
}

function handleDaySelect(dayOffset, selectedButton) {
    // 1. ניהול סמני בחירה של ימים
    document.querySelectorAll('.day-button').forEach(btn => btn.classList.remove('selected'));
    if (selectedButton) {
        selectedButton.classList.add('selected');
    }
    
    // 2. עדכון המשתנה הגלובלי
    currentDayOffset = dayOffset;

    // 3. עדכון הזמנים (שינוי יום לא משנה קו או תחנה)
    if (currentStopKey) {
        // נשתמש ב-handleStopSelect כדי לשמר את הבחירה העיצובית ולהפעיל את תצוגת הזמנים
        const selectedStopButton = document.querySelector(`#stopButtonsContainer button.selected`);
        if (selectedStopButton) {
            handleStopSelect(currentStopKey, selectedStopButton);
        } else {
             // אם אין כפתור נבחר (מצב נדיר), נפעל ישירות:
             displayTimes(currentStopKey);
        }
    }
}

// *** פונקציות לניהול קווים ותחנות ***

function populateRouteButtons() {
    const container = document.getElementById('routeButtonsContainer');
    container.innerHTML = '';
    
    const routeIds = Object.keys(groupedScheduleData).sort((a, b) => {
        const numA = parseInt(a.replace(/\D/g, ''));
        const numB = parseInt(b.replace(/\D/g, ''));
        return numA - numB;
    });

    logDebug(`DEBUG: Populating route buttons for ${routeIds.length} unique routes.`);

    let firstRouteKey = null;

    routeIds.forEach(routeId => {
        const button = document.createElement('button');
        button.className = 'route-button';
        button.textContent = routeId; 
        button.dataset.routeId = routeId;
        button.onclick = () => handleRouteSelect(routeId, button);
        container.appendChild(button);
        
        if (!firstRouteKey) {
            firstRouteKey = routeId;
        }
    });

    // ברירת מחדל 1: בחירה אוטומטית של הקו הראשון
    if (firstRouteKey) {
        const firstButton = container.querySelector(`[data-route-id="${firstRouteKey}"]`);
        handleRouteSelect(firstRouteKey, firstButton);
    }
}


function populateStopButtons(routeId) {
    const container = document.getElementById('stopButtonsContainer');
    container.innerHTML = '';
    
    const stops = groupedScheduleData[routeId];
    if (!stops) {
        logDebug(`WARNING: No stops found for route ${routeId}.`);
        return;
    }
    
    // stops הוא מערך של אובייקטי תחנות
    const sortedStops = stops.sort((a, b) => a.name.localeCompare(b.name, 'he'));
    
    logDebug(`DEBUG: Populating stop buttons for Route ${routeId} with ${sortedStops.length} stops.`);

    let firstStopKey = null;

    sortedStops.forEach(item => {
        // המפתח ב-item הוא routeId|stopCode
        const stopRouteKey = `${item.routeId}|${item.stopCode}`; 
        
        const button = document.createElement('button');
        button.className = 'stop-button';
        button.textContent = `${item.name} (${item.stopCode})`;
        button.dataset.key = stopRouteKey;
        button.onclick = () => handleStopSelect(stopRouteKey, button);
        container.appendChild(button);
        
        if (!firstStopKey) {
            firstStopKey = stopRouteKey;
        }
    });
    
    // ברירת מחדל 2: בחירה אוטומטית של התחנה הראשונה עבור הקו הנבחר
    if (firstStopKey) {
        const firstButton = container.querySelector(`[data-key="${firstStopKey}"]`);
        handleStopSelect(firstStopKey, firstButton);
    }
}


function handleRouteSelect(routeId, selectedButton) {
    // 1. ניהול סמני בחירה של קווים
    document.querySelectorAll('.route-button').forEach(btn => btn.classList.remove('selected'));
    if (selectedButton) {
        selectedButton.classList.add('selected');
    }
    
    // 2. עדכון המשתנים הגלובליים
    currentRouteId = routeId;
    currentStopKey = null; // איפוס בחירת התחנה

    // 3. יצירת כפתורי התחנות הרלוונטיים
    populateStopButtons(routeId);
}


function handleStopSelect(stopRouteKey, selectedButton) {
    // 1. ניהול סמני בחירה של תחנות
    document.querySelectorAll('#stopButtonsContainer .stop-button').forEach(btn => btn.classList.remove('selected'));
    
    if (selectedButton) {
        selectedButton.classList.add('selected');
    }
    
    // 2. עדכון המשתנה הגלובלי
    currentStopKey = stopRouteKey;
    
    // 3. הצגת הזמנים (באמצעות המפתח המשולש: קו|תחנה|יום)
    displayTimes(stopRouteKey);
}