// data_process.js (גרסה מתוקנת: טיפול ב-4 חלקים במפתח + שמות ימים מחזוריים)

// משתנים גלובליים (הצהרה מחדש כ-let כדי להבטיח נגישות מקומית, למרות שהם var ב-utils.js)
let scheduleData = {}; 
let groupedScheduleData = {}; 
let currentRouteId = null;
let currentDayOffset = 0; 

// --- לוגיקת שמות הימים החדשה ---

// 1. קבועים לשמות הימים בעברית (0=ראשון, 6=שבת)
const HEBREW_WEEKDAYS = ["יום א'", "יום ב'", "יום ג'", "יום ד'", "יום ה'", "יום ו'", "מוצש\"ק"];

// 2. חישוב היום הנוכחי בשבוע (0=ראשון, 6=שבת)
// New Date().getDay() מחזיר 0 עבור יום ראשון.
const currentDayIndex = new Date().getDay(); 

function getDayName(offset) {
    // ה-offset מייצג את ההפרש מהיום הנוכחי (0=היום, 1=מחר, וכו').
    // המודולו ( % 7 ) מבטיח שהמחזוריות נשמרת (יום לאחר שבת הוא ראשון).
    const actualDayIndex = (currentDayIndex + offset) % 7;
    
    // שימו לב: עבור יום שבת (Day 6), השם יהיה "מוצש"ק" כפי שביקשת.
    return HEBREW_WEEKDAYS[actualDayIndex]; 
}

// ---------------------------------

function processRawData(rawData) {
    if (!rawData) {
        logDebug('ERROR: No raw data found to process.');
        showFloatingMessage("❌ אין נתונים זמינים.");
        return false;
    }

    logDebug('INFO: Starting weekly data parsing.');
    
    const lines = rawData.trim().split('\n');
    logDebug(`DEBUG: Raw data contains ${lines.length} lines.`);
    
    scheduleData = {}; 
    groupedScheduleData = {}; 
    
    let processedLinesCount = 0;

    lines.forEach((line, index) => {
        const lineTrimmed = line.trim();
        if (!lineTrimmed) return;
        
        // 1. פיצול לפי נקודתיים (:)
        const parts = lineTrimmed.split(':'); 
        logDebug(`LINE ${index}: Read line: "${lineTrimmed.substring(0, Math.min(lineTrimmed.length, 50))}..."`);
        
        if (parts.length < 2) {
            logDebug(`FAIL LINE ${index}: Skipping - Expected at least one colon (:). Found ${parts.length} parts.`);
            return;
        }

        const routeStopDayRaw = parts[0]; 
        const timesStrRaw = parts.slice(1).join(':'); 
        const timesStr = timesStrRaw.replace(/[\r\n]+/g, '').trim(); 
        
        if (!timesStr) {
            logDebug(`FAIL LINE ${index}: Skipping - Time string is empty after trimming.`);
            return;
        }
        
        // 2. פיצול המפתח Route|StopCode|StopName|Day
        const routeParts = routeStopDayRaw.split('|'); 
        logDebug(`LINE ${index}: Key parts (before trim): ${routeParts.length} parts. Expected 4.`);
        
        // *** תיקון קריטי: ודא שיש בדיוק 4 חלקים ***
        if (routeParts.length !== 4) {
            logDebug(`CRITICAL FAIL LINE ${index}: Skipping - Expected 4 key parts (Route|StopCode|StopName|Day). Found ${routeParts.length}.`);
            return;
        }

        // 3. חילוץ וניקוי החלקים
        const routeId = routeParts[0].trim();
        const stopCode = routeParts[1].trim();
        const stopName = routeParts[2].trim(); // שמירת שם התחנה
        const dayOffsetStr = routeParts[3].trim(); // היום הוא החלק הרביעי
        
        logDebug(`LINE ${index}: RouteID="${routeId}", StopCode="${stopCode}", StopName="${stopName}", DayOffsetStr="${dayOffsetStr}"`);
        
        const dayOffset = parseInt(dayOffsetStr, 10);
        
        // ודא ש-dayOffset הוא מספר תקין (0-6)
        if (isNaN(dayOffset) || dayOffset < 0 || dayOffset > 6) {
            logDebug(`FAIL LINE ${index}: Skipping - Invalid DayOffset: ${dayOffset}`);
            return;
        }
        
        // 4. חילוץ הזמנים
        let rawTimes = timesStr.split(',');
        let departureTimes = []; 

        rawTimes.forEach(time => {
            const timeTrimmed = time.trim();
            // בדיקת תקינות מינימלית
            if (timeTrimmed.match(/^\d{2}:\d{2}$/)) { 
                departureTimes.push(timeTrimmed);
            } 
        });
        
        logDebug(`LINE ${index}: Found ${departureTimes.length} valid departure times.`);
        
        if (routeId && stopCode && departureTimes.length > 0) {
            processedLinesCount++;
            
            // שמירת הנתונים במבנים הגלובליים
            const key = `${routeId}|${stopCode}|${dayOffset}`;
            const stopRouteKey = `${routeId}|${stopCode}`; 
            
            const item = {
                key: key,
                routeId: routeId,
                stopCode: stopCode,
                dayOffset: dayOffset,
                times: departureTimes
            };
            
            scheduleData[key] = item;
            
            // קיבוץ הנתונים (שימוש בשם התחנה שנמצא בקובץ)
            if (!groupedScheduleData[routeId]) {
                groupedScheduleData[routeId] = {};
            }
            if (!groupedScheduleData[routeId][stopRouteKey]) {
                groupedScheduleData[routeId][stopRouteKey] = {
                    routeId: routeId,
                    stopCode: stopCode,
                    name: stopName, // שימוש בשם התחנה שנקרא מהקובץ
                    timesByDay: {} 
                };
            }
            groupedScheduleData[routeId][stopRouteKey].timesByDay[dayOffset] = departureTimes;
            logDebug(`SUCCESS LINE ${index}: Parsed key ${key}. Stop name: ${stopName}.`);
        } else {
             logDebug(`FAIL LINE ${index}: Skipping - Missing Route/Stop or zero times left after cleanup.`);
        }
    });
    
    // ניקוי וסידור
    const finalGrouped = {};
    Object.keys(groupedScheduleData).forEach(routeId => {
        finalGrouped[routeId] = Object.values(groupedScheduleData[routeId]);
    });
    groupedScheduleData = finalGrouped;

    logDebug(`--- PARSING SUMMARY ---`);
    logDebug(`DEBUG: Total lines processed successfully: ${processedLinesCount}`);
    logDebug(`DEBUG: Successfully parsed ${Object.keys(scheduleData).length} unique items, grouped into ${Object.keys(groupedScheduleData).length} routes.`);
    logDebug(`-----------------------`);
    
    return Object.keys(scheduleData).length > 0;
}