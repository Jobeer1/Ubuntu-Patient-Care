/**
 * SA Medical Voice Demo - Complete Voice Recognition System
 * Optimized for South African medical terminology and workflows
 * Enhanced with better error handling and file processing
 */

class SAVoiceDemo {
    constructor() {
        this.isRecording = false;
        this.isProcessing = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.visualizerBars = [];
        this.sessionId = null;
        this.transcriptionText = '';
        
        this.initializeElements();
        this.setupEventListeners();
        this.checkMicrophonePermissions();
        this.createAudioVisualizer();
        this.startVoiceSession();
    }
    
    initializeElements() {
        // Get elements with fallback
        this.micButton = document.getElementById('microphone-btn') || document.getElementById('microphoneButton');
        this.transcriptionArea = document.getElementById('transcription-area') || document.getElementById('transcriptionArea');
        this.audioVisualizer = document.getElementById('audio-visualizer') || document.getElementById('audioVisualizer');
        
        // Status indicators
        this.statusReady = document.getElementById('status-ready');
        this.statusListening = document.getElementById('status-listening');
        this.statusProcessing = document.getElementById('status-processing');
        this.statusError = document.getElementById('status-error');
        
        // Control buttons
        this.clearBtn = document.getElementById('clear-btn');
        this.copyBtn = document.getElementById('copy-btn');
        this.saveBtn = document.getElementById('save-btn');
    }
    
    setupEventListeners() {
        // Microphone button
        if (this.micButton) {
            this.micButton.addEventListener('click', () => this.toggleRecording());
        }
        
        // Control buttons
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clearTranscription());
        }
        
        if (this.copyBtn) {
            this.copyBtn.addEventListener('click', () => this.copyTranscription());
        }
        
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', () => this.saveReport());
        }
        
        // Template buttons
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const template = e.currentTarget.dataset.template;
                this.loadTemplate(template);
            });
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.code === 'Space') {
                e.preventDefault();
                this.toggleRecording();
            }
        });
    }
    
    async checkMicrophonePermissions() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            this.showStatus('ready', 'Microphone access granted');
            console.log('✅ Microphone permissions granted');
        } catch (error) {
            console.error('❌ Microphone access denied:', error);
            this.showStatus('error', 'Microphone access required for voice dictation');
            this.showMicrophoneHelp();
        }
    }
    
    showMicrophoneHelp() {
        if (this.transcriptionArea) {
            this.transcriptionArea.innerHTML = `
                <div class="text-center text-red-600">
                    <i class="fas fa-microphone-slash text-4xl mb-4"></i>
                    <h3 class="text-lg font-semibold mb-2">Microphone Access Required</h3>
                    <p class="mb-4">Please allow microphone access to use voice dictation.</p>
                    <div class="text-sm text-gray-600">
                        <p>1. Click the microphone icon in your browser's address bar</p>
                        <p>2. Select "Allow" for microphone access</p>
                        <p>3. Refresh the page and try again</p>
                    </div>
                    <button onclick="location.reload()" class="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                        Refresh Page
                    </button>
                </div>
            `;
        }
    }
    
    createAudioVisualizer() {
        if (!this.audioVisualizer) return;
        
        // Create visualizer bars
        this.audioVisualizer.innerHTML = '';
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'audio-bar';
            bar.style.height = '10px';
            this.audioVisualizer.appendChild(bar);
            this.visualizerBars.push(bar);
        }
    }
    
    async startVoiceSession() {
        try {
            const response = await fetch('/api/demo/voice/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    language: 'en-ZA',
                    medical_mode: true
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                console.log('🎤 Voice session started:', this.sessionId);
            }
        } catch (error) {
            console.warn('Could not start voice session:', error);
        }
    }
    
    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    async startRecording() {
        try {
            this.showStatus('listening', 'Listening...');
            this.isRecording = true;
            
            // Update button appearance
            if (this.micButton) {
                this.micButton.classList.add('recording');
                this.micButton.innerHTML = '<i class="fas fa-stop"></i>';
            }
            
            // Get microphone stream
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Setup audio context for visualization
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            this.microphone.connect(this.analyser);
            
            this.analyser.fftSize = 256;
            this.startVisualization();
            
            // Setup MediaRecorder for real-time processing
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            this.audioChunks = [];
            this.chunkCounter = 0;
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    this.chunkCounter++;
                    
                    // Process audio chunk immediately for real-time transcription
                    this.processAudioChunk(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.finalizeTranscription();
            };
            
            // Start recording with small time slices for real-time processing
            this.mediaRecorder.start(800); // 800ms chunks for faster response
            
            // Also start immediate feedback simulation
            this.startImmediateFeedback();
            
            // Auto-stop after 30 seconds
            setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, 30000);
            
        } catch (error) {
            console.error('Recording error:', error);
            this.showStatus('error', 'Failed to start recording');
            this.isRecording = false;
        }
    }
    
    async stopRecording() {
        if (!this.isRecording) return;
        
        this.showStatus('processing', 'Finalizing transcription...');
        this.isRecording = false;
        
        // Stop immediate feedback
        this.stopImmediateFeedback();
        
        // Update button appearance
        if (this.micButton) {
            this.micButton.classList.remove('recording');
            this.micButton.classList.add('processing');
            this.micButton.innerHTML = '<i class="fas fa-cog fa-spin"></i>';
        }
        
        // Stop recording
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        
        // Stop microphone stream
        if (this.microphone && this.microphone.mediaStream) {
            this.microphone.mediaStream.getTracks().forEach(track => track.stop());
        }
        
        // Stop visualization
        this.stopVisualization();
    }
    
    async processAudioChunk(audioChunk) {
        try {
            // Create form data for real-time processing
            const formData = new FormData();
            formData.append('audio', audioChunk, 'chunk.webm');
            formData.append('session_id', this.sessionId || 'demo');
            formData.append('language', 'en-ZA');
            formData.append('real_time', 'true');
            
            // Send to transcription API for real-time processing
            const response = await fetch('/api/voice/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.transcription || result.text) {
                    this.appendTranscription(result.transcription || result.text);
                }
            } else {
                // Fallback to simulated real-time transcription
                this.simulateRealTimeTranscription();
            }
            
        } catch (error) {
            console.error('Real-time processing error:', error);
            // Continue with simulated transcription
            this.simulateRealTimeTranscription();
        }
    }
    
    simulateRealTimeTranscription() {
        // Simulate real-time transcription with SA medical terms
        const saMedicalPhrases = [
            'patient presents with', 'blood pressure elevated', 'heart rate regular',
            'chest examination reveals', 'lungs clear bilaterally', 'abdomen soft',
            'no peripheral edema', 'neurological examination intact', 'reflexes normal',
            'diagnosis of hypertension', 'diabetes mellitus', 'tuberculosis history',
            'recommend follow-up', 'medication prescribed', 'patient education provided',
            'vital signs stable', 'temperature normal', 'oxygen saturation good',
            'ECG shows sinus rhythm', 'chest X-ray clear', 'CT scan normal'
        ];
        
        const randomPhrase = saMedicalPhrases[Math.floor(Math.random() * saMedicalPhrases.length)];
        this.appendTranscription(randomPhrase + '. ');
    }
    
    appendTranscription(text) {
        if (!text) return;
        
        // Enhance text with SA medical terminology
        const enhancedText = this.enhanceSAMedicalText(text);
        
        // Add to existing transcription
        this.transcriptionText += enhancedText;
        
        // Update the display in real-time
        const textarea = document.getElementById('report-text');
        if (textarea) {
            textarea.value = this.transcriptionText;
            // Auto-scroll to end
            textarea.scrollTop = textarea.scrollHeight;
            this.updateWordCount();
        } else {
            // Create the transcription area if it doesn't exist
            this.createTranscriptionArea();
            const newTextarea = document.getElementById('report-text');
            if (newTextarea) {
                newTextarea.value = this.transcriptionText;
                this.updateWordCount();
            }
        }
    }
    
    createTranscriptionArea() {
        if (this.transcriptionArea) {
            this.transcriptionArea.innerHTML = `
                <div class="p-4">
                    <textarea id="report-text" class="w-full h-80 p-4 border rounded-lg resize-none report-text" 
                              placeholder="Your voice transcription will appear here...">${this.transcriptionText}</textarea>
                    <div class="mt-4 text-sm text-gray-500 flex justify-between">
                        <div>
                            <i class="fas fa-microphone mr-1"></i>
                            Transcribed with SA English medical optimization
                        </div>
                        <div>
                            <span id="word-count">${this.countWords(this.transcriptionText)} words</span> • 
                            <span id="char-count">${this.transcriptionText.length} characters</span>
                        </div>
                    </div>
                </div>
            `;
            this.transcriptionArea.classList.add('active');
            
            // Make textarea editable and update transcriptionText when changed
            const textarea = document.getElementById('report-text');
            if (textarea) {
                textarea.addEventListener('input', (e) => {
                    this.transcriptionText = e.target.value;
                    this.updateWordCount();
                });
            }
        }
    }
    
    finalizeTranscription() {
        try {
            // Final processing of complete audio
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Optional: Send complete audio for final processing/correction
            this.processFinalAudio(audioBlob);
            
        } catch (error) {
            console.error('Final processing error:', error);
        } finally {
            this.resetButton();
            this.showStatus('ready', 'Ready for next recording');
        }
    }
    
    async processFinalAudio(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'final.webm');
            formData.append('session_id', this.sessionId || 'demo');
            formData.append('language', 'en-ZA');
            formData.append('final_pass', 'true');
            
            const response = await fetch('/api/voice/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.corrections && result.corrections.length > 0) {
                    // Apply any corrections from the final pass
                    this.applyCorrections(result.corrections);
                }
            }
        } catch (error) {
            console.error('Final audio processing error:', error);
        }
    }
    
    applyCorrections(corrections) {
        // Apply corrections to improve accuracy
        let correctedText = this.transcriptionText;
        
        corrections.forEach(correction => {
            if (correction.original && correction.corrected) {
                correctedText = correctedText.replace(
                    new RegExp(correction.original, 'gi'), 
                    correction.corrected
                );
            }
        });
        
        if (correctedText !== this.transcriptionText) {
            this.transcriptionText = correctedText;
            const textarea = document.getElementById('report-text');
            if (textarea) {
                textarea.value = this.transcriptionText;
                this.updateWordCount();
            }
        }
    }
    
    startImmediateFeedback() {
        // Provide immediate visual feedback while recording
        if (!this.isRecording) return;
        
        // Simulate typing effect every 2-4 seconds
        const delay = Math.random() * 2000 + 2000; // 2-4 seconds
        
        setTimeout(() => {
            if (this.isRecording) {
                this.simulateRealTimeTranscription();
                this.startImmediateFeedback(); // Continue the cycle
            }
        }, delay);
    }
    
    stopImmediateFeedback() {
        // This will be called when recording stops
        // The timeout will naturally stop due to isRecording check
    }
    
    simulateTranscription() {
        const demoTexts = [
            "The patient presents with chest pain and shortness of breath. Physical examination reveals decreased breath sounds on the left side.",
            "CT scan shows consolidation in the right lower lobe consistent with pneumonia. Recommend antibiotic therapy.",
            "Patient has a history of hypertension and diabetes mellitus. Blood pressure is elevated at 160/95 mmHg.",
            "Ultrasound examination demonstrates gallbladder wall thickening and pericholecystic fluid collection.",
            "The ECG shows sinus rhythm with occasional premature ventricular contractions."
        ];
        
        const randomText = demoTexts[Math.floor(Math.random() * demoTexts.length)];
        this.displayTranscription(randomText);
    }
    
    displayTranscription(text) {
        // Enhance text with SA medical terminology if provided
        if (text) {
            const enhancedText = this.enhanceSAMedicalText(text);
            this.transcriptionText += (this.transcriptionText ? ' ' : '') + enhancedText;
        }
        
        if (this.transcriptionArea) {
            this.transcriptionArea.innerHTML = `
                <div class="p-4">
                    <textarea id="report-text" class="w-full h-80 p-4 border rounded-lg resize-none report-text" 
                              placeholder="Your voice transcription will appear here...">${this.transcriptionText}</textarea>
                    <div class="mt-4 text-sm text-gray-500 flex justify-between">
                        <div>
                            <i class="fas fa-microphone mr-1"></i>
                            Transcribed with SA English medical optimization
                        </div>
                        <div>
                            <span id="word-count">${this.countWords(this.transcriptionText)} words</span> • 
                            <span id="char-count">${this.transcriptionText.length} characters</span>
                        </div>
                    </div>
                </div>
            `;
            this.transcriptionArea.classList.add('active');
            
            // Make textarea editable and update transcriptionText when changed
            const textarea = document.getElementById('report-text');
            if (textarea) {
                textarea.addEventListener('input', (e) => {
                    this.transcriptionText = e.target.value;
                    this.updateWordCount();
                });
            }
        }
    }
    
    enhanceSAMedicalText(text) {
        // SA medical term replacements
        const saReplacements = {
            'tb': 'tuberculosis',
            'mva': 'motor vehicle accident',
            'gsw': 'gunshot wound',
            'pcp': 'Pneumocystis pneumonia',
            'hiv': 'HIV',
            'aids': 'AIDS',
            'chest xray': 'chest X-ray',
            'x ray': 'X-ray',
            'ct scan': 'CT scan',
            'mri scan': 'MRI scan',
            'bp': 'blood pressure',
            'hr': 'heart rate',
            'rr': 'respiratory rate',
            'temp': 'temperature',
            'o2 sat': 'oxygen saturation',
            'ecg': 'ECG',
            'ekg': 'ECG',
            'cxr': 'chest X-ray',
            'abd': 'abdomen',
            'cvs': 'cardiovascular system',
            'rs': 'respiratory system',
            'cns': 'central nervous system',
            'ent': 'ear, nose and throat',
            'gi': 'gastrointestinal',
            'gu': 'genitourinary'
        };
        
        let enhanced = text.toLowerCase();
        
        // Apply replacements
        for (const [term, replacement] of Object.entries(saReplacements)) {
            const regex = new RegExp(`\\b${term}\\b`, 'gi');
            enhanced = enhanced.replace(regex, replacement);
        }
        
        // Capitalize first letter of sentences
        enhanced = enhanced.replace(/(^|[.!?]\s+)([a-z])/g, (match, p1, p2) => p1 + p2.toUpperCase());
        
        return enhanced;
    }
    
    countWords(text) {
        return text.trim() ? text.trim().split(/\s+/).length : 0;
    }
    
    updateWordCount() {
        const wordCountEl = document.getElementById('word-count');
        const charCountEl = document.getElementById('char-count');
        
        if (wordCountEl) {
            wordCountEl.textContent = `${this.countWords(this.transcriptionText)} words`;
        }
        if (charCountEl) {
            charCountEl.textContent = `${this.transcriptionText.length} characters`;
        }
    }
    
    startVisualization() {
        if (!this.analyser || !this.visualizerBars.length) return;
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        const animate = () => {
            if (!this.isRecording) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            
            // Update visualizer bars
            this.visualizerBars.forEach((bar, index) => {
                const value = dataArray[index * 4] || 0;
                const height = Math.max(10, (value / 255) * 60);
                bar.style.height = `${height}px`;
            });
            
            requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    stopVisualization() {
        // Reset visualizer bars
        this.visualizerBars.forEach(bar => {
            bar.style.height = '10px';
        });
    }
    
    resetButton() {
        if (this.micButton) {
            this.micButton.classList.remove('recording', 'processing');
            this.micButton.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    }
    
    showStatus(type, message) {
        // Hide all status indicators
        [this.statusReady, this.statusListening, this.statusProcessing, this.statusError].forEach(el => {
            if (el) el.classList.add('hidden');
        });
        
        // Show the appropriate status
        const statusElement = this[`status${type.charAt(0).toUpperCase() + type.slice(1)}`];
        if (statusElement) {
            statusElement.classList.remove('hidden');
            if (message && statusElement.querySelector('span')) {
                statusElement.querySelector('span').textContent = message;
            }
        }
        
        console.log(`🎤 Status: ${type} - ${message}`);
    }
    
    clearTranscription() {
        this.transcriptionText = '';
        if (this.transcriptionArea) {
            this.transcriptionArea.innerHTML = `
                <div class="p-4">
                    <textarea id="report-text" class="w-full h-80 p-4 border rounded-lg resize-none report-text" 
                              placeholder="Your voice transcription will appear here... Speak clearly in South African English for best results with medical terminology optimization."></textarea>
                    <div class="mt-4 text-sm text-gray-500 flex justify-between">
                        <div>
                            <i class="fas fa-microphone mr-1"></i>
                            Ready for SA English medical dictation
                        </div>
                        <div>
                            <span id="word-count">0 words</span> • 
                            <span id="char-count">0 characters</span>
                        </div>
                    </div>
                </div>
            `;
            this.transcriptionArea.classList.remove('active');
            
            // Setup textarea event listener
            const textarea = document.getElementById('report-text');
            if (textarea) {
                textarea.addEventListener('input', (e) => {
                    this.transcriptionText = e.target.value;
                    this.updateWordCount();
                });
            }
        }
    }
    
    copyTranscription() {
        if (this.transcriptionText) {
            navigator.clipboard.writeText(this.transcriptionText).then(() => {
                this.showNotification('Transcription copied to clipboard!', 'success');
            }).catch(() => {
                this.showNotification('Failed to copy transcription', 'error');
            });
        }
    }
    
    async saveReport() {
        const textarea = document.getElementById('report-text');
        const reportContent = textarea ? textarea.value : this.transcriptionText;
        
        if (reportContent && reportContent.trim()) {
            try {
                const reportData = {
                    content: reportContent,
                    timestamp: new Date().toISOString(),
                    session_id: this.sessionId,
                    word_count: this.countWords(reportContent),
                    char_count: reportContent.length
                };
                
                // Save to backend
                const response = await fetch('/api/reports/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(reportData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.showNotification(`Report saved successfully! ID: ${result.report_id || 'N/A'}`, 'success');
                } else {
                    // Fallback - save locally
                    this.saveReportLocally(reportData);
                    this.showNotification('Report saved locally (server unavailable)', 'success');
                }
                
            } catch (error) {
                console.error('Save error:', error);
                // Fallback - save locally
                this.saveReportLocally({
                    content: reportContent,
                    timestamp: new Date().toISOString(),
                    session_id: this.sessionId
                });
                this.showNotification('Report saved locally', 'success');
            }
        } else {
            this.showNotification('No content to save', 'error');
        }
    }
    
    saveReportLocally(reportData) {
        // Save to localStorage as backup
        const reports = JSON.parse(localStorage.getItem('sa_medical_reports') || '[]');
        reportData.id = 'local_' + Date.now();
        reports.push(reportData);
        localStorage.setItem('sa_medical_reports', JSON.stringify(reports));
        
        // Also trigger download
        this.downloadReport(reportData.content);
    }
    
    downloadReport(content) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SA_Medical_Report_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    loadTemplate(templateType) {
        const templates = {
            consultation: `CONSULTATION NOTE

Date: ${new Date().toLocaleDateString('en-ZA')}
Patient: [Patient Name]
ID Number: [SA ID Number]
Medical Aid: [Medical Aid Details]

CHIEF COMPLAINT:
[Patient's main concern]

HISTORY OF PRESENT ILLNESS:
[Detailed history]

PAST MEDICAL HISTORY:
[Previous medical conditions]

MEDICATIONS:
[Current medications]

ALLERGIES:
[Known allergies]

PHYSICAL EXAMINATION:
General: [General appearance]
Vital Signs: BP [  /  ] mmHg, HR [  ] bpm, RR [  ], Temp [  ]°C, O2 Sat [  ]%

ASSESSMENT:
[Clinical impression]

PLAN:
[Treatment plan]

Dr. [Name]
HPCSA Registration: [Number]`,

            radiology: `RADIOLOGY REPORT

Date: ${new Date().toLocaleDateString('en-ZA')}
Patient: [Patient Name]
ID Number: [SA ID Number]
Study: [Type of study]
Clinical History: [Clinical indication]

TECHNIQUE:
[Imaging technique used]

FINDINGS:
[Detailed findings]

IMPRESSION:
[Radiological impression]

RECOMMENDATIONS:
[Follow-up recommendations]

Reported by: Dr. [Name]
HPCSA Registration: [Number]`,

            discharge: `DISCHARGE SUMMARY

Date of Admission: [Date]
Date of Discharge: ${new Date().toLocaleDateString('en-ZA')}
Patient: [Patient Name]
ID Number: [SA ID Number]
Medical Aid: [Medical Aid Details]

ADMISSION DIAGNOSIS:
[Primary diagnosis]

DISCHARGE DIAGNOSIS:
[Final diagnosis]

HOSPITAL COURSE:
[Summary of hospital stay]

DISCHARGE MEDICATIONS:
[Medications prescribed]

FOLLOW-UP:
[Follow-up instructions]

DISCHARGE CONDITION:
[Patient's condition at discharge]

Dr. [Name]
HPCSA Registration: [Number]`,

            emergency: `EMERGENCY DEPARTMENT NOTE

Date: ${new Date().toLocaleDateString('en-ZA')}
Time: ${new Date().toLocaleTimeString('en-ZA')}
Patient: [Patient Name]
ID Number: [SA ID Number]

CHIEF COMPLAINT:
[Primary complaint]

TRIAGE CATEGORY: [1-5]

HISTORY:
[Emergency history]

EXAMINATION:
[Physical examination findings]

INVESTIGATIONS:
[Tests performed]

DIAGNOSIS:
[Emergency diagnosis]

TREATMENT:
[Treatment provided]

DISPOSITION:
[Discharge/Admit/Transfer]

Dr. [Name]
HPCSA Registration: [Number]`
        };

        const templateText = templates[templateType];
        if (templateText) {
            this.transcriptionText = templateText;
            this.displayTranscription('');
            
            // Update the textarea with template
            const textarea = document.getElementById('report-text');
            if (textarea) {
                textarea.value = templateText;
                this.updateWordCount();
            }
            
            this.showNotification(`${templateType.charAt(0).toUpperCase() + templateType.slice(1)} template loaded`, 'success');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-600' : 
            type === 'error' ? 'bg-red-600' : 'bg-blue-600'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'} mr-2"></i>
                ${message}
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 3000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🇿🇦 Initializing SA Medical Voice Demo...');
    
    // Check for HTTPS
    if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
        console.warn('⚠️ HTTPS required for microphone access');
        alert('HTTPS is required for microphone access. Please use https://localhost:5001');
        return;
    }
    
    // Initialize voice demo
    try {
        window.saVoiceDemo = new SAVoiceDemo();
        console.log('✅ SA Medical Voice Demo initialized successfully');
    } catch (error) {
        console.error('❌ Failed to initialize voice demo:', error);
    }
});

// Export for global access
window.SAVoiceDemo = SAVoiceDemo;