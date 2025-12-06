/**
 * GOTG Dictation-3: Vanilla JavaScript Application
 * 
 * Professional voice dictation system with:
 * - Real-time waveform visualization
 * - Transcription display
 * - Injury assessment rendering
 * - Offline support with IndexedDB caching
 * - Multi-user LAN support
 */

// ============================================================================
// GLOBAL STATE & CONFIGURATION
// ============================================================================

const CONFIG = {
    API_BASE: 'http://localhost:5000/api',
    SESSION_STORAGE_KEY: 'dictation3_session',
    CACHE_DB_NAME: 'dictation3_cache',
    CACHE_STORE_NAME: 'dictations'
};

let state = {
    isOnline: navigator.onLine,
    isRecording: false,
    sessionId: null,
    authToken: null,
    currentUser: null,
    recordingStartTime: null,
    recordingTime: 0,
    audioContext: null,
    analyser: null,
    mediaRecorder: null,
    chunks: [],
    currentTranscription: '',
    currentAssessment: null,
    timerInterval: null,
    animationId: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    setupEventListeners();
    setupOnlineOfflineListener();
    await checkSession();
    initializeIndexedDB();
}

function setupEventListeners() {
    // Online/offline detection
    window.addEventListener('online', () => {
        state.isOnline = true;
        updateOnlineStatus();
        syncPendingDictations();
    });

    window.addEventListener('offline', () => {
        state.isOnline = false;
        updateOnlineStatus();
    });

    // Unload handler - save state
    window.addEventListener('beforeunload', () => {
        if (state.isRecording) {
            stopRecording();
        }
    });
}

function setupOnlineOfflineListener() {
    updateOnlineStatus();
    setInterval(updateOnlineStatus, 5000);
}

// ============================================================================
// AUTHENTICATION & SESSION MANAGEMENT
// ============================================================================

async function checkSession() {
    const storedSession = localStorage.getItem(CONFIG.SESSION_STORAGE_KEY);
    
    if (storedSession) {
        try {
            state.currentUser = JSON.parse(storedSession);
            state.authToken = state.currentUser.token;
            hideLoginModal();
            loadDashboard();
        } catch (e) {
            localStorage.removeItem(CONFIG.SESSION_STORAGE_KEY);
            showLoginModal();
        }
    } else {
        showLoginModal();
    }
}

function showLoginModal() {
    const modal = document.getElementById('loginModal');
    modal.style.display = 'flex';
}

function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    modal.style.display = 'none';
}

async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('userEmail').value;
    const password = document.getElementById('userPassword').value;
    const clinic = document.getElementById('clinicSelect').value;

    try {
        showAlert('🔐 Authenticating...', 'info');
        
        const response = await fetch(`${CONFIG.API_BASE}/dictation/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                password: password,
                clinic_id: clinic
            })
        });

        if (!response.ok) {
            throw new Error('Authentication failed');
        }

        const data = await response.json();
        state.currentUser = {
            email: email,
            clinic: clinic,
            role: data.role || 'clinician',
            token: data.token
        };
        state.authToken = data.token;

        localStorage.setItem(CONFIG.SESSION_STORAGE_KEY, JSON.stringify(state.currentUser));
        hideLoginModal();
        loadDashboard();
        showAlert('✅ Login successful!', 'success');

    } catch (error) {
        showAlert('❌ Login failed: ' + error.message, 'error');
    }
}

function logout() {
    if (confirm('🚪 Are you sure you want to logout?')) {
        localStorage.removeItem(CONFIG.SESSION_STORAGE_KEY);
        state.authToken = null;
        state.currentUser = null;
        location.reload();
    }
}

function loadDashboard() {
    const userDisplay = document.getElementById('userDisplay');
    userDisplay.textContent = `👤 Welcome, ${state.currentUser.email}!`;
    refreshDictations();
}

// ============================================================================
// VOICE RECORDING
// ============================================================================

async function startRecording() {
    try {
        if (!state.mediaRecorder) {
            await setupAudioRecording();
        }

        state.chunks = [];
        state.isRecording = true;
        state.recordingStartTime = Date.now();
        state.recordingTime = 0;

        state.mediaRecorder.start();

        // Start timer
        document.getElementById('startRecordBtn').style.display = 'none';
        document.getElementById('stopRecordBtn').style.display = 'block';
        document.getElementById('recordingStatus').textContent = '🔴 Recording...';
        document.getElementById('recordingStatus').classList.add('recording');

        startTimer();
        startWaveformVisualization();

        showAlert('🎤 Recording started...', 'success');

    } catch (error) {
        showAlert('❌ Failed to start recording: ' + error.message, 'error');
    }
}

async function setupAudioRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create audio context for visualization
        state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        state.analyser = state.audioContext.createAnalyser();
        state.analyser.fftSize = 256;

        const microphone = state.audioContext.createMediaStreamSource(stream);
        microphone.connect(state.analyser);

        // Create media recorder
        state.mediaRecorder = new MediaRecorder(stream);
        state.mediaRecorder.ondataavailable = (event) => {
            state.chunks.push(event.data);
        };

    } catch (error) {
        throw new Error(`Microphone access denied: ${error.message}`);
    }
}

async function stopRecording() {
    if (!state.isRecording) return;

    state.isRecording = false;
    state.mediaRecorder.stop();
    clearInterval(state.timerInterval);

    document.getElementById('startRecordBtn').style.display = 'block';
    document.getElementById('stopRecordBtn').style.display = 'none';
    document.getElementById('recordingStatus').textContent = '⏹️ Processing...';
    document.getElementById('recordingStatus').classList.remove('recording');

    if (state.animationId) {
        cancelAnimationFrame(state.animationId);
    }

    // Process recording
    await processRecording();
}

function startTimer() {
    document.getElementById('timerDisplay').textContent = '00:00';
    state.timerInterval = setInterval(() => {
        state.recordingTime++;
        const minutes = Math.floor(state.recordingTime / 60);
        const seconds = state.recordingTime % 60;
        document.getElementById('timerDisplay').textContent = 
            `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }, 1000);
}

function startWaveformVisualization() {
    const canvas = document.getElementById('waveformCanvas');
    const canvasCtx = canvas.getContext('2d');
    const dataArray = new Uint8Array(state.analyser.frequencyBinCount);

    const draw = () => {
        state.animationId = requestAnimationFrame(draw);

        state.analyser.getByteFrequencyData(dataArray);

        canvasCtx.fillStyle = 'rgb(200, 200, 200)';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

        const barWidth = (canvas.width / dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            barHeight = (dataArray[i] / 255) * canvas.height;

            canvasCtx.fillStyle = `rgb(33, 150, 243)`;
            canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

            x += barWidth + 1;
        }
    };

    draw();
}

function clearRecording() {
    state.chunks = [];
    state.recordingTime = 0;
    document.getElementById('timerDisplay').textContent = '00:00';
    document.getElementById('recordingStatus').textContent = 'Ready';
    document.getElementById('recordingStatus').classList.remove('recording');
    document.getElementById('transcriptionCard').style.display = 'none';
    document.getElementById('assessmentCard').style.display = 'none';
    state.currentTranscription = '';
    state.currentAssessment = null;
}

// ============================================================================
// AUDIO PROCESSING & API COMMUNICATION
// ============================================================================

async function processRecording() {
    if (state.chunks.length === 0) {
        showAlert('❌ No audio recorded', 'error');
        return;
    }

    try {
        document.getElementById('processingIndicator').style.display = 'flex';
        showAlert('⏳ Processing audio...', 'info');

        // Create blob from chunks
        const audioBlob = new Blob(state.chunks, { type: 'audio/webm' });

        // Start session
        const sessionResponse = await apiCall('/dictation/session/start', 'POST', {
            clinic_id: state.currentUser.clinic
        });

        if (!sessionResponse.ok) {
            throw new Error('Failed to start session');
        }

        state.sessionId = sessionResponse.data.session_id;

        // Upload audio
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('session_id', state.sessionId);

        const uploadResponse = await fetch(
            `${CONFIG.API_BASE}/dictation/session/${state.sessionId}/upload-audio`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${state.authToken}`
                },
                body: formData
            }
        );

        if (!uploadResponse.ok) {
            throw new Error('Failed to upload audio');
        }

        // Transcribe
        const transcribeResponse = await apiCall(
            `/dictation/session/${state.sessionId}/transcribe`,
            'POST',
            { language: 'en' }
        );

        if (!transcribeResponse.ok) {
            throw new Error('Transcription failed');
        }

        state.currentTranscription = transcribeResponse.data.transcription;
        displayTranscription(transcribeResponse.data);

        // Assess injuries
        const assessResponse = await apiCall(
            `/dictation/session/${state.sessionId}/assess-injuries`,
            'POST',
            { transcription: state.currentTranscription }
        );

        if (assessResponse.ok) {
            state.currentAssessment = assessResponse.data;
            displayAssessment(assessResponse.data);
        }

        showAlert('✅ Processing complete!', 'success');

    } catch (error) {
        showAlert('❌ Processing failed: ' + error.message, 'error');
    } finally {
        document.getElementById('processingIndicator').style.display = 'none';
        document.getElementById('recordingStatus').textContent = 'Ready';
    }
}

// ============================================================================
// DISPLAY & UI UPDATES
// ============================================================================

function displayTranscription(data) {
    document.getElementById('transcriptionCard').style.display = 'block';
    document.getElementById('transcriptionText').textContent = data.transcription;
    document.getElementById('confidenceScore').textContent = 
        Math.round(data.confidence * 100);
}

function displayAssessment(data) {
    document.getElementById('assessmentCard').style.display = 'block';

    // Severity badge
    const severityBadge = document.getElementById('severityBadge');
    const severityText = getSeverityText(data.primary_injury.severity);
    severityBadge.textContent = severityText;
    severityBadge.className = `severity-badge ${getSeverityClass(data.primary_injury.severity)}`;

    // Primary injury
    document.getElementById('primaryInjury').innerHTML = `
        <p class="injury-name">${data.primary_injury.injury_type}</p>
        <p class="injury-category">Category: ${data.primary_injury.category}</p>
        <p class="injury-icd10">ICD-10: ${data.primary_injury.icd10_code}</p>
    `;

    // Severity indicator
    const severityBar = document.getElementById('severityBar');
    severityBar.style.width = `${(data.primary_injury.severity / 4) * 100}%`;
    severityBar.className = `severity-bar ${getSeverityClass(data.primary_injury.severity)}`;
    document.getElementById('severityText').textContent = `Severity: ${data.primary_injury.severity.toFixed(1)}/4.0`;

    // All injuries
    const injuryList = document.getElementById('injuryList');
    if (data.injuries && data.injuries.length > 0) {
        injuryList.innerHTML = data.injuries.map(injury => `
            <div class="injury-item">
                <span class="injury-name">${injury.injury_type}</span>
                <span class="injury-confidence">${Math.round(injury.confidence * 100)}% confidence</span>
                <span class="injury-severity">${getSeverityEmoji(injury.severity)}</span>
            </div>
        `).join('');
    } else {
        injuryList.innerHTML = '<p>No significant injuries detected</p>';
    }

    // Vital signs
    if (data.vital_signs && Object.keys(data.vital_signs).length > 0) {
        document.getElementById('hrValue').textContent = data.vital_signs.heart_rate || '-';
        document.getElementById('bpValue').textContent = data.vital_signs.blood_pressure || '-';
        document.getElementById('o2Value').textContent = data.vital_signs.oxygen_sat || '-';
        document.getElementById('tempValue').textContent = data.vital_signs.temperature || '-';
    }

    // Clinical observations
    const observations = document.getElementById('clinicalObservations');
    if (data.clinical_observations && Object.keys(data.clinical_observations).length > 0) {
        observations.innerHTML = `
            <ul>
                ${Object.entries(data.clinical_observations)
                    .map(([key, value]) => `<li>${key}: ${value}</li>`)
                    .join('')}
            </ul>
        `;
    }

    // Processing details
    document.getElementById('processingTime').textContent = 
        `⏱️ Processing time: ${data.processing_time_ms || '-'}ms`;
    document.getElementById('assessmentTimestamp').textContent = 
        `📅 Assessment at: ${new Date().toLocaleString()}`;
}

function editTranscription() {
    document.getElementById('editTranscriptionText').value = state.currentTranscription;
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
}

function saveEditedTranscription() {
    const edited = document.getElementById('editTranscriptionText').value;
    state.currentTranscription = edited;
    document.getElementById('transcriptionText').textContent = edited;
    closeEditModal();
    showAlert('✅ Transcription updated', 'success');
}

function copyTranscription() {
    navigator.clipboard.writeText(state.currentTranscription);
    showAlert('📋 Transcription copied to clipboard', 'success');
}

async function saveDictation() {
    if (!state.currentAssessment) {
        showAlert('❌ No assessment to save', 'error');
        return;
    }

    try {
        const response = await apiCall(
            `/dictation/session/${state.sessionId}/complete`,
            'POST',
            {
                transcription: state.currentTranscription,
                assessment: state.currentAssessment
            }
        );

        if (response.ok) {
            showAlert('✅ Dictation saved successfully!', 'success');
            clearRecording();
            await cacheToIndexedDB(state.currentAssessment);
            await refreshDictations();
        }
    } catch (error) {
        showAlert('❌ Failed to save: ' + error.message, 'error');
    }
}

function printAssessment() {
    const printWindow = window.open('', '_blank');
    const content = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Injury Assessment Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { border-bottom: 2px solid #333; margin-bottom: 20px; }
                .section { margin: 20px 0; }
                .section h3 { background: #f0f0f0; padding: 10px; }
                table { width: 100%; border-collapse: collapse; }
                td { border: 1px solid #ddd; padding: 8px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 Injury Assessment Report</h1>
                <p>Generated: ${new Date().toLocaleString()}</p>
            </div>
            <div class="section">
                <h3>Transcription</h3>
                <p>${state.currentTranscription}</p>
            </div>
            <div class="section">
                <h3>Primary Injury</h3>
                <p><strong>${state.currentAssessment.primary_injury.injury_type}</strong></p>
                <p>Severity: ${state.currentAssessment.primary_injury.severity}/4.0</p>
            </div>
        </body>
        </html>
    `;
    printWindow.document.write(content);
    printWindow.document.close();
    printWindow.print();
}

function exportAssessment() {
    const data = JSON.stringify(state.currentAssessment, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `assessment_${state.sessionId}.json`;
    a.click();
    showAlert('📥 Assessment exported', 'success');
}

// ============================================================================
// DICTATIONS LIST & RECENT ITEMS
// ============================================================================

async function refreshDictations() {
    try {
        const response = await apiCall('/dictation/sessions', 'GET');

        if (response.ok && response.data.sessions) {
            const list = document.getElementById('dictationsList');
            const sessions = response.data.sessions;

            if (sessions.length === 0) {
                list.innerHTML = '<p>No dictations yet. Start recording!</p>';
            } else {
                list.innerHTML = sessions.slice(0, 10).map(session => `
                    <div class="dictation-item">
                        <div class="dictation-header">
                            <span class="dictation-time">📅 ${new Date(session.created_at).toLocaleString()}</span>
                            <span class="dictation-severity ${getSeverityClass(session.primary_severity)}">${getSeverityEmoji(session.primary_severity)}</span>
                        </div>
                        <p class="dictation-injury">${session.primary_injury || 'No primary injury'}</p>
                        <p class="dictation-transcription">${session.transcription.substring(0, 100)}...</p>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        document.getElementById('dictationsList').innerHTML = '<p>Error loading dictations</p>';
    }
}

// ============================================================================
// STATUS & NOTIFICATIONS
// ============================================================================

function updateOnlineStatus() {
    const indicator = document.getElementById('onlineIndicator');
    if (state.isOnline) {
        indicator.textContent = '🟢 Online';
        indicator.className = 'indicator online';
    } else {
        indicator.textContent = '🔴 Offline';
        indicator.className = 'indicator offline';
    }
}

async function syncPendingDictations() {
    if (!state.isOnline || !state.authToken) return;

    try {
        const response = await apiCall('/dictation/pending-sync', 'GET');
        if (response.ok && response.data.pending) {
            const count = response.data.pending.length;
            document.getElementById('pendingSyncDisplay').textContent = 
                count > 0 ? `📤 ${count} Pending Sync` : '✅ All Synced';
        }
    } catch (error) {
        console.error('Sync check failed:', error);
    }
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.style.display='none';" class="alert-close">&times;</button>
    `;
    container.appendChild(alert);

    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

// ============================================================================
// API HELPERS
// ============================================================================

async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.authToken}`
            }
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, options);
        const data = await response.json();

        return {
            ok: response.ok,
            status: response.status,
            data: data
        };
    } catch (error) {
        throw error;
    }
}

// ============================================================================
// INDEXEDDB CACHING
// ============================================================================

function initializeIndexedDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(CONFIG.CACHE_DB_NAME, 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(CONFIG.CACHE_STORE_NAME)) {
                db.createObjectStore(CONFIG.CACHE_STORE_NAME, { keyPath: 'session_id' });
            }
        };
    });
}

async function cacheToIndexedDB(assessment) {
    try {
        const db = await initializeIndexedDB();
        const transaction = db.transaction([CONFIG.CACHE_STORE_NAME], 'readwrite');
        const store = transaction.objectStore(CONFIG.CACHE_STORE_NAME);
        store.add(assessment);
    } catch (error) {
        console.error('Caching failed:', error);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getSeverityText(severity) {
    if (severity >= 3.5) return '🚨 CRITICAL';
    if (severity >= 2.5) return '⚠️ SEVERE';
    if (severity >= 1.5) return 'ℹ️ MODERATE';
    if (severity >= 0.5) return '🟡 MINOR';
    return '✅ NONE';
}

function getSeverityClass(severity) {
    if (severity >= 3.5) return 'critical';
    if (severity >= 2.5) return 'severe';
    if (severity >= 1.5) return 'moderate';
    if (severity >= 0.5) return 'minor';
    return 'none';
}

function getSeverityEmoji(severity) {
    if (severity >= 3.5) return '🚨';
    if (severity >= 2.5) return '⚠️';
    if (severity >= 1.5) return 'ℹ️';
    if (severity >= 0.5) return '🟡';
    return '✅';
}
