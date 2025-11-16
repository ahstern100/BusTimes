// time_display.js (גרסה מתוקנת - טיפול בנתונים מקובצים ויום)

// פונקציות לאיתור וסימון הזמן הקרוב

function findNextTime(times) {
    // אם היום הנבחר הוא "היום" (Offset 0), נחשב את הזמן הקרוב.
    if (currentDayOffset === 0) { 
        const now = new Date();
        const currentMinutes = now.getHours() * 60 + now.getMinutes();
        
        let nextTime = null;
        let minDiff = Infinity;

        for (const time of times) {
            const [hour, minute] = time.split(':').map(Number);
            const timeMinutes = hour * 60 + minute;
            
            let diff = timeMinutes - currentMinutes;
            
            // מטפל במקרה שהזמן עבר (מוסיף 24 שעות)
            if (diff < 0) {
                 // זה אומר שהזמן עבר, אז נתעלם ממנו עבור החישוב של ה"קרוב ביותר"
                 // אלא אם כן אנחנו רוצים לעטוף ליום הבא, אבל במקרה הזה אנחנו מציגים רק זמנים ליום אחד
                 // נשאיר את זה כך שהזמן הקרוב יהיה רק מהרגע הנוכחי והלאה.
            } else if (diff >= 0 && diff < minDiff) {
                minDiff = diff;
                nextTime = time;
            }
        }
        
        return nextTime;
    } 
    // אם זה לא היום, אין "זמן קרוב" מיוחד, ומחזירים null
    return null;
}

function displayTimes(stopRouteKey) {
    const timesList = document.getElementById('timesList');
    timesList.innerHTML = '';
    
    const [routeId, stopCode] = stopRouteKey.split('|');
    
    // גישה לנתונים המקובצים (groupedScheduleData)
    const stopGroup = groupedScheduleData[routeId].find(g => g.stopCode === stopCode);

    if (!stopGroup || !stopGroup.timesByDay[currentDayOffset]) {
        timesList.innerHTML = '<li>אין זמני יציאה עבור יום זה.</li>';
        logDebug(`WARNING: No schedule found for key ${stopRouteKey} on day ${currentDayOffset}.`);
        return;
    }

    // שליפת הזמנים עבור היום הנבחר
    const times = stopGroup.timesByDay[currentDayOffset];
    
    logDebug(`INFO: Displaying schedule for ${stopRouteKey} on day ${currentDayOffset}. Found ${times.length} times.`);

    let nextTimeListItem = null;
    let nextTime = null;
    
    if (currentDayOffset === 0) {
        nextTime = findNextTime(times);
    }

    times.forEach(time => {
        const listItem = document.createElement('li');
        listItem.textContent = time;
        listItem.className = 'times';
        
        if (time === nextTime) {
            listItem.classList.add('next-time');
            nextTimeListItem = listItem;
        }
        
        timesList.appendChild(listItem);
    });

    // בוטל: גלילה אוטומטית לזמן הקרוב
    // if (nextTimeListItem) {
    //     nextTimeListItem.scrollIntoView({ behavior: 'smooth', block: 'center' }); 
    // }
}