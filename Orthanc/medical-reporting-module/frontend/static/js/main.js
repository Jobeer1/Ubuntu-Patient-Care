/**
 * Medical Reporting Module - Main JavaScript
 * Production-ready frontend functionality
 */

class MedicalReportingApp {
    constructor() {
        this.isOnline = navigator.onLine;
        this.voiceRecording = false;
        this.currentStudy = null;
        this.currentReport = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.wsIntegration = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkConnectivity();
        this.initializeVoiceRecognition();
        this.initializeWebSocket();
        this.loadDashboard();
        
        // Check connectivity every 30 seconds
        setInterval(() => this.checkConnectivity(), 30000);
    }
    
    initializeWebSocket() {
        // Initialize WebSocket integration if available
        if (typeof WebSocketIntegration !== 'undefined') {
            try {
                this.wsIntegration = new WebSocketIntegration(this, 'doctor_user');
                console.log('WebSocket integration initialized');
            } catch (error) {
                console.warn('WebSocket integration failed:', error);
            }
        }
    }

    setupEventListeners() {
        // Connectivity events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Voice control events
        const voiceBtn = document.getElementById('voice-button');
        if (voiceBtn) {
            voiceBtn.addEventListener('click', () => this.toggleVoiceRecording());
        }
        
        // Navigation events
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                this.handleAction(e.target.dataset.action, e.target);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveReport();
                        break;
                    case 'n':
                        e.preventDefault();
                        this.createNewReport();
                        break;
                    case 'm':
                        e.preventDefault();
                        this.toggleVoiceRecording();
                        break;
                }
            }
        });
    }

    // Connectivity Management
    checkConnectivity() {
        fetch('/health')
            .then(response => {
                if (response.ok) {
                    this.handleOnline();
                } else {
                    throw new Error('Server not responding');
                }
            })
            .catch(() => this.handleOffline());
    }

    handleOnline() {
        this.isOnline = true;
        this.updateConnectivityUI(true);
        this.syncOfflineData();
    }

    handleOffline() {
        this.isOnline = false;
        this.updateConnectivityUI(false);
    }

    updateConnectivityUI(online) {
        const onlineBadge = document.getElementById('online-badge');
        const offlineBadge = document.getElementById('offline-badge');
        
        if (online) {
            onlineBadge?.classList.remove('hidden');
            offlineBadge?.classList.add('hidden');
        } else {
            onlineBadge?.classList.add('hidden');
            offlineBadge?.classList.remove('hidden');
        }
    }

    // Voice Recognition
    initializeVoiceRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onresult = (event) => this.handleSpeechResult(event);
            this.recognition.onerror = (event) => this.handleSpeechError(event);
            this.recognition.onend = () => this.handleSpeechEnd();
        }
        
        // Initialize media recorder for audio capture
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    this.mediaRecorder = new MediaRecorder(stream);
                    this.mediaRecorder.ondataavailable = (event) => {
                        this.audioChunks.push(event.data);
                    };
                    this.mediaRecorder.onstop = () => this.processAudioRecording();
                })
                .catch(err => console.warn('Microphone access denied:', err));
        }
    }

    toggleVoiceRecording() {
        if (this.voiceRecording) {
            this.stopVoiceRecording();
        } else {
            this.startVoiceRecording();
        }
    }

    startVoiceRecording() {
        this.voiceRecording = true;
        this.audioChunks = [];
        
        // Update UI
        const voiceBtn = document.getElementById('voice-button');
        const voiceStatus = document.getElementById('voice-status');
        
        if (voiceBtn) {
            voiceBtn.classList.add('recording');
            voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
        }
        
        if (voiceStatus) {
            voiceStatus.textContent = 'Recording...';
        }
        
        // Start WebSocket voice session
        if (this.wsIntegration && this.currentReport) {
            this.wsIntegration.startVoiceSession(this.currentReport.id);
        }
        
        // Start recording
        if (this.mediaRecorder && this.mediaRecorder.state === 'inactive') {
            this.mediaRecorder.start();
        }
        
        // Start speech recognition
        if (this.recognition) {
            this.recognition.start();
        }
    }

    stopVoiceRecording() {
        this.voiceRecording = false;
        
        // Update UI
        const voiceBtn = document.getElementById('voice-button');
        const voiceStatus = document.getElementById('voice-status');
        
        if (voiceBtn) {
            voiceBtn.classList.remove('recording');
            voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
        
        if (voiceStatus) {
            voiceStatus.textContent = 'Click to start recording';
        }
        
        // End WebSocket voice session
        if (this.wsIntegration) {
            this.wsIntegration.endVoiceSession();
        }
        
        // Stop recording
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }
        
        // Stop speech recognition
        if (this.recognition) {
            this.recognition.stop();
        }
    }

    handleSpeechResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Check for voice commands
        if (finalTranscript) {
            this.processVoiceCommand(finalTranscript);
            this.appendToReport(finalTranscript);
        }
        
        // Update interim results
        this.updateInterimTranscript(interimTranscript);
    }

    processVoiceCommand(transcript) {
        const command = transcript.toLowerCase().trim();
        
        // Template commands
        if (command.includes('load template')) {
            const templateName = command.replace('load template', '').trim();
            this.loadTemplate(templateName);
        }
        
        // Navigation commands
        if (command.includes('new report')) {
            this.createNewReport();
        }
        
        if (command.includes('save report')) {
            this.saveReport();
        }
        
        // Layout commands
        if (command.includes('two by two layout')) {
            this.changeViewportLayout('2x2');
        }
        
        if (command.includes('single viewport')) {
            this.changeViewportLayout('1x1');
        }
    }

    handleSpeechError(event) {
        console.error('Speech recognition error:', event.error);
        this.showNotification('Voice recognition error: ' + event.error, 'error');
    }

    handleSpeechEnd() {
        if (this.voiceRecording) {
            // Restart recognition if still recording
            setTimeout(() => {
                if (this.voiceRecording && this.recognition) {
                    this.recognition.start();
                }
            }, 100);
        }
    }

    processAudioRecording() {
        if (this.audioChunks.length === 0) return;
        
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        
        // Send to server for processing if online
        if (this.isOnline) {
            this.sendAudioToServer(audioBlob);
        } else {
            // Store for offline processing
            this.storeAudioOffline(audioBlob);
        }
    }

    sendAudioToServer(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('report_id', this.currentReport?.id || '');
        
        fetch('/api/voice/transcribe', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.transcript) {
                this.appendToReport(data.transcript);
            }
        })
        .catch(err => {
            console.error('Audio transcription failed:', err);
            this.showNotification('Transcription failed, working offline', 'warning');
        });
    }

    // Report Management
    createNewReport() {
        const data = {
            study_id: this.currentStudy?.id || null,
            template_id: null
        };
        
        if (this.isOnline) {
            fetch('/api/reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(report => {
                this.currentReport = report;
                this.loadReportEditor(report);
            })
            .catch(err => this.handleOfflineReportCreation(data));
        } else {
            this.handleOfflineReportCreation(data);
        }
    }

    saveReport() {
        if (!this.currentReport) return;
        
        const reportContent = document.getElementById('report-content')?.value || '';
        
        const data = {
            ...this.currentReport,
            content: reportContent,
            updated_at: new Date().toISOString()
        };
        
        if (this.isOnline) {
            fetch(`/api/reports/${this.currentReport.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(report => {
                this.currentReport = report;
                this.showNotification('Report saved successfully', 'success');
            })
            .catch(err => this.handleOfflineReportSave(data));
        } else {
            this.handleOfflineReportSave(data);
        }
    }

    loadTemplate(templateName) {
        if (this.isOnline) {
            fetch(`/api/templates/search?name=${encodeURIComponent(templateName)}`)
                .then(response => response.json())
                .then(templates => {
                    if (templates.length > 0) {
                        this.applyTemplate(templates[0]);
                    }
                })
                .catch(err => console.error('Template loading failed:', err));
        } else {
            // Load from offline cache
            this.loadOfflineTemplate(templateName);
        }
    }

    applyTemplate(template) {
        const reportContent = document.getElementById('report-content');
        if (reportContent && template.content) {
            reportContent.value = template.content;
            this.showNotification(`Template "${template.name}" applied`, 'success');
        }
    }

    appendToReport(text) {
        const reportContent = document.getElementById('report-content');
        if (reportContent) {
            const currentContent = reportContent.value;
            const newContent = currentContent + (currentContent ? ' ' : '') + text;
            reportContent.value = newContent;
            
            // Auto-save draft
            this.autoSaveDraft();
        }
    }

    updateInterimTranscript(text) {
        const interimElement = document.getElementById('interim-transcript');
        if (interimElement) {
            interimElement.textContent = text;
        }
    }

    // DICOM Viewer
    changeViewportLayout(layout) {
        const viewportGrid = document.querySelector('.viewport-grid');
        if (viewportGrid) {
            viewportGrid.className = `viewport-grid layout-${layout}`;
            this.showNotification(`Layout changed to ${layout}`, 'success');
        }
    }

    loadStudy(studyId) {
        if (this.isOnline) {
            fetch(`/api/studies/${studyId}`)
                .then(response => response.json())
                .then(study => {
                    this.currentStudy = study;
                    this.loadStudyImages(study);
                })
                .catch(err => this.loadOfflineStudy(studyId));
        } else {
            this.loadOfflineStudy(studyId);
        }
    }

    // Offline Management
    handleOfflineReportCreation(data) {
        const offlineReport = {
            id: 'offline_' + Date.now(),
            ...data,
            created_at: new Date().toISOString(),
            status: 'draft',
            offline: true
        };
        
        this.storeOfflineData('reports', offlineReport);
        this.currentReport = offlineReport;
        this.loadReportEditor(offlineReport);
        this.showNotification('Working offline - report will sync when online', 'warning');
    }

    handleOfflineReportSave(data) {
        this.storeOfflineData('reports', data);
        this.showNotification('Report saved offline - will sync when online', 'warning');
    }

    storeOfflineData(type, data) {
        const key = `medical_reporting_${type}`;
        let stored = JSON.parse(localStorage.getItem(key) || '[]');
        
        const existingIndex = stored.findIndex(item => item.id === data.id);
        if (existingIndex >= 0) {
            stored[existingIndex] = data;
        } else {
            stored.push(data);
        }
        
        localStorage.setItem(key, JSON.stringify(stored));
    }

    syncOfflineData() {
        // Sync reports
        const offlineReports = JSON.parse(localStorage.getItem('medical_reporting_reports') || '[]');
        offlineReports.forEach(report => {
            if (report.offline) {
                this.syncOfflineReport(report);
            }
        });
        
        // Sync audio recordings
        const offlineAudio = JSON.parse(localStorage.getItem('medical_reporting_audio') || '[]');
        offlineAudio.forEach(audio => {
            this.syncOfflineAudio(audio);
        });
    }

    // UI Management
    loadDashboard() {
        // Load recent reports
        this.loadRecentReports();
        
        // Load system status
        this.updateSystemStatus();
        
        // Load today's stats
        this.loadTodayStats();
    }

    loadRecentReports() {
        if (this.isOnline) {
            fetch('/api/reports/recent')
                .then(response => response.json())
                .then(reports => this.displayRecentReports(reports))
                .catch(err => this.loadOfflineRecentReports());
        } else {
            this.loadOfflineRecentReports();
        }
    }

    displayRecentReports(reports) {
        const container = document.getElementById('recent-reports');
        if (!container) return;
        
        container.innerHTML = reports.map(report => `
            <tr class="border-b hover:bg-gray-50 cursor-pointer" data-action="load-report" data-report-id="${report.id}">
                <td class="px-4 py-2">${report.patient_name || 'Unknown'}</td>
                <td class="px-4 py-2">${new Date(report.created_at).toLocaleDateString()}</td>
                <td class="px-4 py-2">${report.modality || 'N/A'}</td>
                <td class="px-4 py-2">
                    <span class="status-indicator status-${report.status}">
                        ${report.status}
                    </span>
                </td>
                <td class="px-4 py-2">
                    <button class="btn btn-primary btn-sm" data-action="edit-report" data-report-id="${report.id}">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    handleAction(action, element) {
        const reportId = element.dataset.reportId;
        const studyId = element.dataset.studyId;
        
        switch (action) {
            case 'new-report':
                this.createNewReport();
                break;
            case 'load-report':
            case 'edit-report':
                this.loadReport(reportId);
                break;
            case 'load-study':
                this.loadStudy(studyId);
                break;
            case 'voice-dictation':
                this.toggleVoiceRecording();
                break;
            case 'save-report':
                this.saveReport();
                break;
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
        
        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
    }

    autoSaveDraft() {
        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            if (this.currentReport) {
                this.saveReport();
            }
        }, 2000); // Auto-save after 2 seconds of inactivity
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.medicalApp = new MedicalReportingApp();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MedicalReportingApp;
}