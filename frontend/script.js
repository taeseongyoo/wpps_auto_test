// Supabase Client Setup
const { createClient } = supabase;
const supabaseClient = createClient(ENV.SUPABASE_URL, ENV.SUPABASE_KEY);

// DOM Elements
const loginModal = document.getElementById('login-modal');
const loginBtn = document.getElementById('login-btn');
const apiEndpointInput = document.getElementById('api-endpoint');

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const previewSection = document.getElementById('preview-section');
const fileNameDisplay = document.getElementById('file-name');
const rowCountDisplay = document.getElementById('row-count');
const startBtn = document.getElementById('start-btn');

// Favorites DOM
const favListEl = document.getElementById('favorites-list');
const favNameInput = document.getElementById('fav-name');
const favDestInput = document.getElementById('fav-dest');
const favTypeInput = document.getElementById('fav-type');
const favQtyInput = document.getElementById('fav-qty');
const addFavBtn = document.getElementById('add-fav-btn');
const quickStartBtn = document.getElementById('quick-start-btn');

const scheduleTypeSelect = document.getElementById('schedule-type');
const scheduleValWeekly = document.getElementById('schedule-val-weekly');
const scheduleValMonthly = document.getElementById('schedule-val-monthly');
const activeScheduleStatus = document.getElementById('active-schedule-status');
const scheduleTimeInput = document.getElementById('schedule-time');
const saveScheduleBtn = document.getElementById('save-schedule-btn');

const currCountDisplay = document.getElementById('today-count');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const taskPercent = document.getElementById('task-percent');
const progressDetail = document.getElementById('progress-detail');
const liveLogs = document.getElementById('live-logs');
const savedTimeDisplay = document.getElementById('saved-time');

let parsedData = [];
let AWS_API_URL = "http://localhost:8000"; // Default
let sessionUserId = "ADMIN_DEMO";

// --- Login Check ---
loginBtn.addEventListener('click', () => {
    // Demo authentication bypass
    AWS_API_URL = apiEndpointInput.value;
    loginModal.classList.add('hidden');
    initRealtimeListener();
    fetchStats();
});

// --- File Upload Handling (PapaParse CSV) ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if(e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
    if(e.target.files.length) handleFile(e.target.files[0]);
});

function handleFile(file) {
    if(!file.name.endsWith('.csv')) {
        alert("현재는 CSV 파일만 지원됩니다.");
        return;
    }
    fileNameDisplay.textContent = file.name;
    
    Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: function(results) {
            // Expected headers: dest_code, type_code, quantity
            // Mapping default template if exact headers miss match
            parsedData = results.data.map(row => ({
                dest_code: row.dest_code || Object.values(row)[0] || "601494",
                type_code: row.type_code || Object.values(row)[1] || "N11",
                quantity: row.quantity || Object.values(row)[2] || "4"
            }));
            
            rowCountDisplay.textContent = `${parsedData.length}건 확인됨`;
            previewSection.classList.remove('hidden');
        }
    });
}

// --- Submit to Backend API (FastAPI Queue) ---
startBtn.addEventListener('click', async () => {
    if(parsedData.length === 0) return;
    
    startBtn.disabled = true;
    startBtn.textContent = "전송 중...";
    startBtn.classList.remove('pulse-animation');
    
    const payload = {
        items: parsedData,
        user_id: sessionUserId
    };

    try {
        const res = await fetch(`${AWS_API_URL}/api/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if(res.ok) {
            addLog("System", `성공적으로 서버 큐에 ${parsedData.length}건을 전송했습니다.`, "info");
            progressContainer.classList.remove('hidden');
            progressDetail.textContent = "AWS 서버가 작업을 할당받고 가동을 시작했습니다.";
        } else {
            alert("API 호출 실패: " + JSON.stringify(data));
        }
    } catch(err) {
        addLog("Error", `통신 오류: ${err.message}. 백엔드/CORS를 확인하세요.`, "error");
        alert("서버 통신 실패. 로컬 테스트 중이라면 파이썬 서버가 켜져 있는지 확인하세요.");
    } finally {
        startBtn.textContent = "엑셀 대량 자동화 시작 🚀";
        startBtn.disabled = false;
        previewSection.classList.add('hidden');
    }
});

// --- Favorites List Management ---
let favorites = JSON.parse(localStorage.getItem('wpps_favorites')) || [
    { dest_name: "오픈한(샘플)", dest_code: "601494", type_code: "N11", quantity: "4", selected: true }
];

function saveFavorites() {
    localStorage.setItem('wpps_favorites', JSON.stringify(favorites));
}

function renderFavorites() {
    favListEl.innerHTML = '';
    let needsSave = false;
    
    favorites.forEach((item, index) => {
        if (item.selected === undefined) {
            item.selected = true; // backward compatibility
            needsSave = true;
        }
        
        const tr = document.createElement('tr');
        tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        tr.innerHTML = `
            <td style="padding: 10px 0; text-align: center;">
                <input type="checkbox" class="select-fav-cb" data-index="${index}" style="cursor:pointer; width: 16px; height: 16px;">
            </td>
            <td style="padding: 10px 0; color: white; text-align: left;">${item.dest_name || '-'}</td>
            <td style="padding: 10px 0; color: var(--text-muted); text-align: left;">${item.dest_code}</td>
            <td style="padding: 10px 0; text-align: center; color: var(--text-muted);">${item.type_code}</td>
            <td style="padding: 10px 0; text-align: right; color: white;">${item.quantity}</td>
            <td style="padding: 10px 0; text-align: right;">
                <button class="delete-fav-btn" data-index="${index}" style="background:transparent; border:none; color:var(--danger); font-size: 1.1rem; cursor:pointer;">✕</button>
            </td>
        `;
        favListEl.appendChild(tr);
    });
    
    if (needsSave) saveFavorites();
    
    document.querySelectorAll('.delete-fav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = e.target.getAttribute('data-index');
            favorites.splice(idx, 1);
            saveFavorites();
            renderFavorites();
        });
    });

    document.querySelectorAll('.select-fav-cb').forEach(cb => {
        const idx = cb.getAttribute('data-index');
        cb.checked = favorites[idx].selected; // Force sync DOM state with JS
        
        cb.addEventListener('change', (e) => {
            favorites[idx].selected = e.target.checked;
            saveFavorites();
            updateSchedulePreview();
        });
    });
    
    updateSchedulePreview();
}

addFavBtn.addEventListener('click', () => {
    const n = favNameInput.value.trim();
    const d = favDestInput.value.trim();
    const t = favTypeInput.value.trim() || 'N11';
    const q = favQtyInput.value.trim();
    
    if(!d || !q) {
        alert("⚠️ [하차지 코드]와 [수량]을 반드시 입력해주세요!\n(이름을 비워둘 경우 코드가 이름으로 사용됩니다.)");
        return;
    }
    
    favorites.push({ dest_name: n || d, dest_code: d, type_code: t, quantity: q, selected: true });
    saveFavorites();
    renderFavorites();
    
    favNameInput.value = '';
    favDestInput.value = '';
    favTypeInput.value = 'N11';
    favQtyInput.value = '';
});

// Initialize
renderFavorites();

// --- Submit Favorites Quick Payload ---
quickStartBtn.addEventListener('click', async () => {
    const selectedFavorites = favorites.filter(f => f.selected);
    
    if(selectedFavorites.length === 0) {
        alert("선택된 즐겨찾기 항목이 없습니다. 표에서 체크박스를 선택해주세요.");
        return;
    }

    quickStartBtn.disabled = true;
    quickStartBtn.textContent = "가동 중... ⚡";
    
    const payload = {
        items: selectedFavorites,
        user_id: sessionUserId
    };

    try {
        const res = await fetch(`${AWS_API_URL}/api/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if(res.ok) {
            addLog("System", `성공적으로 즐겨찾기 ${favorites.length}건을 지시했습니다.`, "info");
            progressContainer.classList.remove('hidden');
            progressDetail.textContent = "즐겨찾기 배치 처리 시작!";
        } else {
            alert("API 호출 실패: " + JSON.stringify(data));
        }
    } catch(err) {
        if (err.name === 'TypeError' && err.message === 'Failed to fetch') {
            alert("⚠️ 서버 연결 차단됨 (Mixed Content Error)\n\nVercel(보안 HTTPS)에서 내 PC(일반 HTTP)로 직접 통신하는 것을 브라우저가 보안상 차단했습니다.\n\n해결책: 터미널에서 ngrok을 실행하여 HTTPS 주소를 발급받은 뒤, 로그인 창의 API 주소칸에 넣어주세요!\n명령어: ngrok http 8000");
            addLog("Error", `브라우저 보안 차단 (HTTPS -> HTTP 연결 불가)`, "error");
        } else {
            addLog("Error", `통신 오류: ${err.message}`, "error");
        }
    } finally {
        setTimeout(() => {
            quickStartBtn.textContent = "⚡ 1건 즉시 출하통보 (Quick Start)";
            quickStartBtn.disabled = false;
        }, 2000);
    }
});

// --- Schedule Preview ---
function updateSchedulePreview() {
    const previewContainer = document.getElementById('schedule-preview');
    if(!previewContainer) return; // If DOM element not added yet
    
    const selectedFavorites = favorites.filter(f => f.selected);
    if(selectedFavorites.length === 0) {
        previewContainer.innerHTML = '<span style="color:var(--danger); font-size: 0.8rem;">⚠️ 현재 선택된 예약 대상이 없습니다. 우측 표에서 대상을 체크해주세요.</span>';
        saveScheduleBtn.disabled = true;
        saveScheduleBtn.style.opacity = '0.5';
        return;
    }
    
    saveScheduleBtn.disabled = false;
    saveScheduleBtn.style.opacity = '1';
    
    let previewHtml = `<div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">현재 예약 대기 중인 항목 (${selectedFavorites.length}건):</div>`;
    previewHtml += `<div style="display:flex; flex-wrap:wrap; gap:6px;">`;
    
    selectedFavorites.forEach(f => {
        const nameDisp = f.dest_name && f.dest_name !== f.dest_code ? f.dest_name : f.dest_code;
        previewHtml += `<span style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem;">${nameDisp}</span>`;
    });
    previewHtml += `</div>`;
    
    previewContainer.innerHTML = previewHtml;
}

scheduleTypeSelect.addEventListener('change', (e) => {
    scheduleValWeekly.classList.add('hidden');
    scheduleValMonthly.classList.add('hidden');
    
    if(e.target.value === 'weekly') scheduleValWeekly.classList.remove('hidden');
    if(e.target.value === 'monthly') scheduleValMonthly.classList.remove('hidden');
});

function renderActiveSchedule(scheduleData) {
    if(!scheduleData) {
        activeScheduleStatus.style.display = 'none';
        return;
    }
    
    let freqStr = "";
    if(scheduleData.recurrence === 'daily') freqStr = "매일";
    if(scheduleData.recurrence === 'weekly') {
        const days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"];
        freqStr = `매주 ${days[scheduleData.recurrence_val]}`;
    }
    if(scheduleData.recurrence === 'monthly') freqStr = `매월 ${scheduleData.recurrence_val}일`;
    
    let itemsHtml = `<ul style="margin-top: 8px; margin-bottom: 0; padding-left: 20px; list-style-type: disc; color: var(--text-muted);">`;
    if(scheduleData.items && scheduleData.items.length > 0) {
        scheduleData.items.forEach(item => {
            const nameDisp = item.dest_name && item.dest_name !== item.dest_code ? `${item.dest_name}(${item.dest_code})` : item.dest_code;
            itemsHtml += `<li>하차지: <strong style="color:#10b981;">${nameDisp}</strong> | 유형: ${item.type_code} | 수량: ${item.quantity}개</li>`;
        });
    } else {
        itemsHtml += `<li>총 ${scheduleData.items_count}건의 목록</li>`;
    }
    itemsHtml += `</ul>`;
    
    activeScheduleStatus.innerHTML = `<div style="margin-bottom: 4px;"><strong>🟢 현재 예약 켜짐:</strong> ${freqStr} <strong>${scheduleData.time}</strong> 자동 실행 대기 중</div>${itemsHtml}`;
    activeScheduleStatus.style.display = 'block';
}

// Load from local storage on init
let savedSchedule = JSON.parse(localStorage.getItem('wpps_schedule'));
if(savedSchedule) renderActiveSchedule(savedSchedule);


saveScheduleBtn.addEventListener('click', async () => {
    const timeVal = scheduleTimeInput.value;
    const typeVal = scheduleTypeSelect.value;
    let recVal = null;
    
    if(typeVal === 'weekly') recVal = scheduleValWeekly.value;
    if(typeVal === 'monthly') {
        recVal = scheduleValMonthly.value;
        if(!recVal || recVal < 1 || recVal > 31) {
            alert("1일부터 31일 사이의 날짜를 입력하세요.");
            return;
        }
    }

    if(!timeVal) return;
    
    const selectedFavorites = favorites.filter(f => f.selected);
    if(selectedFavorites.length === 0) {
        alert("예약할 고정값 항목이 선택되지 않았습니다. 먼저 체크박스를 선택해주세요.");
        return;
    }
    
    saveScheduleBtn.disabled = true;
    saveScheduleBtn.textContent = "저장 중...";
    
    try {
        const res = await fetch(`${AWS_API_URL}/api/schedule`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                time: timeVal,
                recurrence: typeVal,
                recurrence_val: recVal,
                items: selectedFavorites,
                user_id: sessionUserId
            })
        });
        
        const data = await res.json();
        if(res.ok) {
            addLog("System", `⏰ 스케줄 설정 완료.`, "info");
            saveScheduleBtn.textContent = "예약 완료 ✓";
            saveScheduleBtn.style.background = "var(--success)";
            
            // Save to local storage and update UI
            const newScheduleData = {
                time: timeVal,
                recurrence: typeVal,
                recurrence_val: recVal,
                items_count: selectedFavorites.length,
                items: selectedFavorites
            };
            localStorage.setItem('wpps_schedule', JSON.stringify(newScheduleData));
            renderActiveSchedule(newScheduleData);
            
        } else {
            alert("스케줄 예약 실패: " + JSON.stringify(data));
            saveScheduleBtn.textContent = "예약 저장";
        }
    } catch(err) {
        addLog("Error", `통신 오류: ${err.message}`, "error");
        saveScheduleBtn.textContent = "예약 저장";
    } finally {
        setTimeout(() => {
            saveScheduleBtn.disabled = false;
        }, 2000);
    }
});

// --- Supabase Real-Time Updates ---
function initRealtimeListener() {
    // Listen to new inserts on "automation_logs" table
    supabaseClient
        .channel('schema-db-changes')
        .on(
            'postgres_changes',
            { event: 'INSERT', schema: 'public', table: 'automation_logs' },
            (payload) => {
                const newLog = payload.new;
                
                // Add to log window
                const msg = `[${newLog.dest_code}] 수량 ${newLog.quantity}개 입력 완료`;
                const type = newLog.status === 'SUCCESS' ? 'success' : 'error';
                addLog("Bot", msg, type);
                
                // Update stats
                fetchStats();
                
                // Update Progress Bar (Mocked to increment slightly visually on each hit)
                let tempPercent = parseFloat(taskPercent.textContent.replace('%',''));
                if(tempPercent < 100) {
                    tempPercent += 10;
                    if(tempPercent >= 100) {
                        tempPercent = 100;
                        triggerCompletionUX();
                    }
                    progressFill.style.width = `${tempPercent}%`;
                    taskPercent.textContent = `${tempPercent}%`;
                }
            }
        )
        .subscribe();
}

// --- Completion UX & Auto-Redirect ---
let completionTimeout = null;
function triggerCompletionUX() {
    progressDetail.innerHTML = `<span style="color:var(--success); font-weight:bold;">✅ 모든 작업이 완료되었습니다! 3초 뒤 로지스올(WPPS) 확인 페이지로 이동합니다...</span>
    <br><button id="manual-wpps-btn" style="margin-top: 8px; padding: 6px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; color: white; cursor: pointer; font-size: 0.8rem;">👉 팝업이 차단된 경우 여기를 눌러 이동</button>`;
    
    document.getElementById('manual-wpps-btn').addEventListener('click', () => {
        window.open('https://wpps.logisall.net/', '_blank');
        if(completionTimeout) clearTimeout(completionTimeout);
        progressDetail.innerHTML = `<span style="color:var(--text-muted);">로지스올(WPPS) 탭이 열렸습니다. 작업을 확인해주세요.</span>`;
    });
    
    let countdown = 3;
    const countInterval = setInterval(() => {
        countdown--;
        const txt = progressDetail.querySelector('span');
        if(txt) txt.innerHTML = `✅ 모든 작업이 완료되었습니다! ${countdown}초 뒤 로지스올(WPPS) 확인 페이지로 이동합니다...`;
        
        if(countdown <= 0) {
            clearInterval(countInterval);
            const popup = window.open('https://wpps.logisall.net/', '_blank');
            if(!popup) {
                // Popup blocked
                if(txt) txt.innerHTML = `⚠️ 팝업이 차단되었습니다. 아래 버튼을 눌러 이동해주세요.`;
            } else {
                if(txt) txt.innerHTML = `<span style="color:var(--text-muted);">자동으로 로지스올(WPPS) 탭이 열렸습니다.</span>`;
            }
        }
    }, 1000);
}

// Fetch Initial Stats
async function fetchStats() {
    const { data, count, error } = await supabaseClient
        .from('automation_logs')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'SUCCESS');
        
    if(!error && count !== null) {
        animateValue(currCountDisplay, parseInt(currCountDisplay.textContent), count, 1000);
        
        // Mock estimate: 1 task = 2 mins saved
        const minutesSaved = count * 2; 
        const hoursSaved = (minutesSaved / 60).toFixed(1);
        savedTimeDisplay.textContent = `${hoursSaved}h`;
    }
}

// Utilities
function addLog(source, message, type) {
    const time = new Date().toLocaleTimeString('ko-KR', {hour12: false});
    const logEl = document.createElement('div');
    logEl.className = 'log-item';
    
    let statusSpan = ``;
    if(type === 'success') statusSpan = `<span class="status-success">[성공]</span>`;
    if(type === 'error') statusSpan = `<span class="status-error">[실패]</span>`;
    
    logEl.innerHTML = `<span class="time">${time}</span> ${statusSpan} <span class="msg">${message}</span>`;
    
    // remove empty log message if present
    const emptyLog = liveLogs.querySelector('.empty-log');
    if(emptyLog) emptyLog.remove();
    
    liveLogs.prepend(logEl);
}

// Simple counter animation
function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
