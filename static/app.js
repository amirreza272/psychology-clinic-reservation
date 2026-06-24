/* ============================================================
   کلینیک مسیر — app.js
   تقویم شمسی + فرم رزرو + اتصال به API
   ============================================================ */

// ─── وضعیت کلی برنامه ───────────────────────────────────────
const state = {
    sessionType: null,      // 'online' | 'inperson'
    selectedDate: null,     // '1404-05-12'  (شمسی)
    selectedDateGreg: null, // '2025-08-03'  (میلادی برای API)
    selectedTime: null,     // '17:00'
    name: '',
    phone: '',
    notes: '',
    calYear: null,
    calMonth: null,
    availableDays: [],      // لیست روزهای آزاد از API (میلادی)
};

// ─── تبدیل اعداد فارسی ──────────────────────────────────────
const FA = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
function toFa(n) {
    return String(n).replace(/\d/g, d => FA[d]);
}

// ─── تبدیل تقویم شمسی ↔ میلادی ─────────────────────────────
// الگوریتم جلالی — بدون نیاز به کتابخانه
const JalaliToGregorian = (jy, jm, jd) => {
    let jy1 = jy - 979;
    let jm1 = jm - 1;
    let jd1 = jd - 1;
    let j_day_no = 365 * jy1 + Math.floor(jy1 / 33) * 8 + Math.floor((jy1 % 33 + 3) / 4);
    for (let i = 0; i < jm1; ++i) j_day_no += (i < 6) ? 31 : 30;
    j_day_no += jd1;
    let g_day_no = j_day_no + 79;
    let gy = 1600 + 400 * Math.floor(g_day_no / 146097);
    g_day_no %= 146097;
    let leap = true;
    if (g_day_no >= 36525) { g_day_no--; gy += 100 * Math.floor(g_day_no / 36524); g_day_no %= 36524; if (g_day_no >= 365) g_day_no++; else leap = false; }
    gy += 4 * Math.floor(g_day_no / 1461);
    g_day_no %= 1461;
    if (g_day_no >= 366) { leap = false; g_day_no--; gy += Math.floor(g_day_no / 365); g_day_no %= 365; }
    const gDays = [31, (leap ? 29 : 28), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let gm;
    for (gm = 0; gm < 12 && g_day_no >= gDays[gm]; gm++) g_day_no -= gDays[gm];
    return [gy, gm + 1, g_day_no + 1];
};

const GregorianToJalali = (gy, gm, gd) => {
    const g_d_no = 365 * gy + Math.floor((gy + 3) / 4) - Math.floor((gy + 99) / 100) + Math.floor((gy + 399) / 400);
    const gDays2 = [31, (gy % 4 === 0 && (gy % 100 !== 0 || gy % 400 === 0)) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    let g_d_no2 = g_d_no;
    for (let i = 0; i < gm - 1; i++) g_d_no2 += gDays2[i];
    g_d_no2 += gd - 1;
    let j_day_no = g_d_no2 - 79;
    let j_np = Math.floor(j_day_no / 12053);
    j_day_no %= 12053;
    let jy = 979 + 33 * j_np + 4 * Math.floor(j_day_no / 1461);
    j_day_no %= 1461;
    if (j_day_no >= 366) { jy += Math.floor((j_day_no - 1) / 365); j_day_no = (j_day_no - 1) % 365; }
    const jDays = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
    let jm;
    for (jm = 0; jm < 11 && j_day_no >= jDays[jm]; jm++) j_day_no -= jDays[jm];
    return [jy, jm + 1, j_day_no + 1];
};

// ─── نام ماه‌های شمسی ────────────────────────────────────────
const JALALI_MONTHS = [
    'فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور',
    'مهر','آبان','آذر','دی','بهمن','اسفند'
];

// روزهای هر ماه شمسی
function jalaliMonthLen(jy, jm) {
    if (jm <= 6) return 31;
    if (jm <= 11) return 30;
    // اسفند
    const [gy] = JalaliToGregorian(jy, 12, 29);
    const isLeap = (gy % 4 === 0 && (gy % 100 !== 0 || gy % 400 === 0));
    return isLeap ? 30 : 29;
}

// اول ماه شمسی چه روزی از هفته است؟  (0=شنبه … 6=جمعه)
function jalaliFirstWeekday(jy, jm) {
    const [gy, gm, gd] = JalaliToGregorian(jy, jm, 1);
    const d = new Date(gy, gm - 1, gd).getDay(); // 0=Sun
    // تبدیل به ترتیب شنبه-اول: Sat=0,Sun=1,...,Fri=6
    return (d + 1) % 7;
}

// ─── مقداردهی اولیه ─────────────────────────────────────────
function init() {
    const today = new Date();
    const [jy, jm] = GregorianToJalali(
        today.getFullYear(), today.getMonth() + 1, today.getDate()
    );
    state.calYear = jy;
    state.calMonth = jm;

    // بارگذاری روزهای آزاد از API
    fetch('/api/available-days')
        .then(r => r.json())
        .then(days => {
            state.availableDays = days; // آرایه‌ای از رشته‌های میلادی مثل '2026-06-25'
            renderCalendar();
        })
        .catch(() => renderCalendar());

    // رویدادهای انتخاب نوع جلسه
    document.querySelectorAll('input[name="session_type"]').forEach(radio => {
        radio.addEventListener('change', onSessionTypeChange);
    });
}

// ─── مرحله ۱: نوع جلسه ──────────────────────────────────────
function onSessionTypeChange(e) {
    state.sessionType = e.target.value;

    document.querySelectorAll('.session-card').forEach(c => c.classList.remove('selected'));
    e.target.closest('.session-card').classList.add('selected');

    document.getElementById('inperson-notice').style.display =
        state.sessionType === 'inperson' ? 'block' : 'none';

    document.getElementById('btn-step1').disabled = false;

    // اگر ساعت انتخاب شده بود و الان inperson شد و ساعت 21 بود، پاک کن
    if (state.sessionType === 'inperson' && state.selectedTime === '21:00') {
        state.selectedTime = null;
        document.getElementById('btn-step2').disabled = true;
    }
    // بازسازی ساعت‌ها اگر روز انتخاب شده
    if (state.selectedDate) renderSlots();
}

// ─── تغییر ماه تقویم ────────────────────────────────────────
function changeMonth(dir) {
    state.calMonth += dir;
    if (state.calMonth > 12) { state.calMonth = 1; state.calYear++; }
    if (state.calMonth < 1)  { state.calMonth = 12; state.calYear--; }
    renderCalendar();
}

// ─── رندر تقویم شمسی ────────────────────────────────────────
function renderCalendar() {
    const { calYear: jy, calMonth: jm } = state;

    document.getElementById('cal-month-label').textContent =
        `${JALALI_MONTHS[jm - 1]} ${toFa(jy)}`;

    const todayG = new Date();
    const [todayJY, todayJM, todayJD] = GregorianToJalali(
        todayG.getFullYear(), todayG.getMonth() + 1, todayG.getDate()
    );

    const totalDays = jalaliMonthLen(jy, jm);
    const startWD   = jalaliFirstWeekday(jy, jm); // 0=شنبه

    const grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    // خانه‌های خالی ابتدا
    for (let i = 0; i < startWD; i++) {
        const empty = document.createElement('div');
        empty.className = 'cal-day empty';
        grid.appendChild(empty);
    }

    for (let d = 1; d <= totalDays; d++) {
        const [gy, gm, gd] = JalaliToGregorian(jy, jm, d);
        const gregStr = `${gy}-${String(gm).padStart(2,'0')}-${String(gd).padStart(2,'0')}`;
        const jalaliStr = `${jy}-${String(jm).padStart(2,'0')}-${String(d).padStart(2,'0')}`;

        // چه روزی از هفته؟ (0=شنبه … 6=جمعه)
        const jsDay = new Date(gy, gm - 1, gd).getDay();
        const weekDay = (jsDay + 1) % 7; // Sat=0

        const isToday   = (jy === todayJY && jm === todayJM && d === todayJD);
        const isPast    = (jy < todayJY) || (jy === todayJY && jm < todayJM) || (jy === todayJY && jm === todayJM && d <= todayJD);
        const isFriday  = weekDay === 6;
        const isAvail   = state.availableDays.includes(gregStr);
        const isSelected = (jalaliStr === state.selectedDate);

        const btn = document.createElement('button');
        btn.className = 'cal-day';
        btn.textContent = toFa(d);

        if (isSelected) btn.classList.add('selected');
        if (isToday)    btn.classList.add('today');
        if (isPast)     btn.classList.add('past');
        if (isFriday)   btn.classList.add('friday');
        if (!isAvail || isPast || isFriday) btn.classList.add('disabled');

        if (isAvail && !isPast && !isFriday) {
            btn.onclick = () => selectDate(jalaliStr, gregStr);
        }

        grid.appendChild(btn);
    }

    // دکمه ماه قبل — اگر ماه جاری است، غیرفعال شود
    document.getElementById('btn-prev-month').disabled =
        (jy === todayJY && jm === todayJM);
}

// ─── انتخاب روز ─────────────────────────────────────────────
function selectDate(jalaliStr, gregStr) {
    state.selectedDate = jalaliStr;
    state.selectedDateGreg = gregStr;
    state.selectedTime = null;

    document.getElementById('btn-step2').disabled = true;
    document.getElementById('slots-wrap').style.display = 'block';

    renderCalendar();     // تازه‌سازی برای نمایش انتخاب
    renderSlots();
}

// ─── بارگذاری و رندر ساعت‌های آزاد ─────────────────────────
function renderSlots() {
    const grid = document.getElementById('slots-grid');
    grid.innerHTML = '<div class="loading-slots">در حال بارگذاری ساعت‌ها...</div>';

    const type = state.sessionType === 'inperson' ? 'inperson' : 'online';

    fetch(`/api/slots?date=${state.selectedDateGreg}&type=${type}`)
        .then(r => r.json())
        .then(slots => {
            grid.innerHTML = '';
            if (!slots.length) {
                grid.innerHTML = '<div class="loading-slots">ساعت خالی برای این روز وجود ندارد.</div>';
                return;
            }
            slots.forEach(time => {
                const btn = document.createElement('button');
                btn.className = 'slot-btn';
                btn.textContent = toFa(time);
                if (time === state.selectedTime) btn.classList.add('selected');
                btn.onclick = () => selectTime(time, btn);
                grid.appendChild(btn);
            });
        })
        .catch(() => {
            grid.innerHTML = '<div class="loading-slots">خطا در بارگذاری. دوباره تلاش کنید.</div>';
        });
}

// ─── انتخاب ساعت ────────────────────────────────────────────
function selectTime(time, btn) {
    state.selectedTime = time;
    document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById('btn-step2').disabled = false;
}

// ─── validate مرحله ۳ ────────────────────────────────────────
function validateStep3() {
    const name  = document.getElementById('input-name').value.trim();
    const phone = document.getElementById('input-phone').value.trim();
    const valid = name.length >= 2 && /^09\d{9}$/.test(phone);
    document.getElementById('btn-step3').disabled = !valid;
    state.name  = name;
    state.phone = phone;
    state.notes = document.getElementById('input-notes').value.trim();
}

// ─── رندر خلاصه رزرو ────────────────────────────────────────
function renderSummary(containerId) {
    const sessionLabel = state.sessionType === 'online' ? 'آنلاین' : 'حضوری';
    const container = document.getElementById(containerId);

    if (containerId === 'booking-summary-top') {
        container.innerHTML = `
            <div><span class="label">نوع جلسه:</span><span class="val">${sessionLabel}</span></div>
            <div><span class="label">تاریخ:</span><span class="val">${toFa(state.selectedDate)}</span></div>
            <div><span class="label">ساعت:</span><span class="val">${toFa(state.selectedTime)}</span></div>
        `;
    } else {
        container.innerHTML = `
            <div class="row"><span class="label">نام</span><span class="val">${state.name}</span></div>
            <div class="row"><span class="label">موبایل</span><span class="val">${toFa(state.phone)}</span></div>
            <div class="row"><span class="label">نوع جلسه</span><span class="val">${sessionLabel}</span></div>
            <div class="row"><span class="label">تاریخ</span><span class="val">${toFa(state.selectedDate)}</span></div>
            <div class="row"><span class="label">ساعت</span><span class="val">${toFa(state.selectedTime)}</span></div>
        `;
    }
}

// ─── جابجایی بین مراحل ──────────────────────────────────────
function goToStep(step) {
    // مخفی کردن همه مراحل
    [1, 2, 3, 4].forEach(s => {
        document.getElementById(`step-${s}`).classList.add('hidden');
        const dot = document.getElementById(`step-dot-${s}`);
        dot.classList.remove('active', 'done');
    });

    // فعال کردن مرحله جاری
    document.getElementById(`step-${step}`).classList.remove('hidden');

    // بروزرسانی نوار مراحل
    for (let s = 1; s <= 4; s++) {
        const dot = document.getElementById(`step-dot-${s}`);
        if (s < step) dot.classList.add('done');
        else if (s === step) dot.classList.add('active');
    }

    // کارهای خاص هر مرحله
    if (step === 3) {
        state.name  = document.getElementById('input-name').value.trim();
        state.phone = document.getElementById('input-phone').value.trim();
        state.notes = document.getElementById('input-notes').value.trim();
        renderSummary('booking-summary-top');
    }

    if (step === 4) {
        state.name  = document.getElementById('input-name').value.trim();
        state.phone = document.getElementById('input-phone').value.trim();
        state.notes = document.getElementById('input-notes').value.trim();
        renderSummary('final-summary');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ─── ارسال رزرو به API ───────────────────────────────────────
function submitBooking() {
    const btn = document.getElementById('btn-pay');
    btn.disabled = true;
    btn.textContent = 'در حال ثبت...';

    const payload = {
        name:         state.name,
        phone:        state.phone,
        date:         state.selectedDateGreg,
        time:         state.selectedTime,
        session_type: state.sessionType,
        notes:        state.notes,
    };

    fetch('/api/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // ─── موفق: نمایش صفحه موفقیت ───
            // (بعداً اینجا ریدایرکت به زرین‌پال اضافه می‌شود)
            showSuccess();
        } else {
            btn.disabled = false;
            btn.textContent = 'پرداخت و ثبت نوبت';
            showError(data.message || 'خطایی رخ داد. دوباره تلاش کنید.');
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.textContent = 'پرداخت و ثبت نوبت';
        showError('خطا در اتصال به سرور. اینترنت خود را بررسی کنید.');
    });
}

// ─── نمایش پیام خطا ─────────────────────────────────────────
function showError(msg) {
    // حذف خطای قبلی اگر وجود داشت
    const old = document.getElementById('error-box');
    if (old) old.remove();

    const box = document.createElement('div');
    box.id = 'error-box';
    box.style.cssText = `
        background:#fff0f0; border:1px solid #f0aaaa; border-radius:8px;
        padding:12px 16px; color:#c0392b; font-size:13px;
        margin-top:12px; text-align:center;
    `;
    box.textContent = '⚠️ ' + msg;
    document.getElementById('step-4').appendChild(box);

    setTimeout(() => box.remove(), 5000);
}

// ─── نمایش صفحه موفقیت ──────────────────────────────────────
function showSuccess() {
    [1,2,3,4].forEach(s => document.getElementById(`step-${s}`).classList.add('hidden'));
    document.getElementById('step-success').classList.remove('hidden');

    const sessionLabel = state.sessionType === 'online' ? 'آنلاین' : 'حضوری';
    document.getElementById('success-summary').innerHTML = `
        <div><span class="label">نام:</span><span class="val">${state.name}</span></div>
        <div><span class="label">نوع جلسه:</span><span class="val">${sessionLabel}</span></div>
        <div><span class="label">تاریخ:</span><span class="val">${toFa(state.selectedDate)}</span></div>
        <div><span class="label">ساعت:</span><span class="val">${toFa(state.selectedTime)}</span></div>
    `;

    // بروزرسانی نوار مراحل — همه done
    for (let s = 1; s <= 4; s++) {
        const dot = document.getElementById(`step-dot-${s}`);
        dot.classList.remove('active');
        dot.classList.add('done');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ─── شروع ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
