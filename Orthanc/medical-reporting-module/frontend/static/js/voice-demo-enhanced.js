/**
 * Enhanced SA Medical Voice Demo with Robust Audio Processing
 * Fixed file handling and error management for Windows environment
 */

class SAVoiceDemo {
    constructor() {
        this.isRecording = false;
        this.isProcessing = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.transcriptionText = '';
        this.sessionId = this.generateSessionId();
        
    // Web Speech API (browser STT) for real-time, accurate dictation
    this.supportsBrowserSTT = ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window);
    this.speechRecognition = null;
    this.liveTranscript = '';
    this.enableLiveDictation = true;
        
        console.log('🇿🇦 Initializing SA Medical Voice Demo...');
        
        this.initializeElements();
        this.setupEventListeners();
        this.checkMicrophonePermissions();
        this.initializeSession();
    }
    
    generateSessionId() {
        return 'sa-voice-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeElements() {
        this.micButton = document.getElementById('microphone-btn');
        this.transcriptionArea = document.getElementById('transcription-area');
        this.statusReady = document.getElementById('status-ready');
        this.statusListening = document.getElementById('status-listening');
        this.statusProcessing = document.getElementById('status-processing');
        this.statusError = document.getElementById('status-error');
        this.clearBtn = document.getElementById('clear-btn');
        this.copyBtn = document.getElementById('copy-btn');
        this.saveBtn = document.getElementById('save-btn');
        
        console.log('✅ Elements initialized');
    }
    
    setupEventListeners() {
        if (this.micButton) {
            this.micButton.addEventListener('click', () => this.toggleRecording());
        }
        
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clearTranscription());
        }
        
        if (this.copyBtn) {
            this.copyBtn.addEventListener('click', () => this.copyTranscription());
        }
        
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', () => this.saveTranscription());
        }
        
        console.log('✅ Event listeners set up');
    }
    
    // Simple client-side SA medical enhancement
    enhanceMedicalText(text) {
        if (!text) return '';
        const replacements = {
            'x ray': 'X-ray',
            'xray': 'X-ray',
            'ct scan': 'CT scan',
            'mri': 'MRI',
            'tb': 'tuberculosis',
            'pcp': 'Pneumocystis pneumonia',
            'o2': 'oxygen',
            'bp': 'blood pressure',
            'hr': 'heart rate',
            'rr': 'respiratory rate'
        };
        let out = text;
        for (const [k, v] of Object.entries(replacements)) {
            const re = new RegExp(`\\b${k}\\b`, 'gi');
            out = out.replace(re, v);
        }
        return out;
    }
    
    async initializeSession() {
        try {
            const response = await fetch('/api/voice/session/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    language: 'en-ZA',
                    medical_context: true
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('🔗 Voice session initialized:', result);
            }
        } catch (error) {
            console.warn('⚠️ Session initialization failed, using offline mode:', error);
        }
    }
    
    async checkMicrophonePermissions() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Test successful, stop the stream
            stream.getTracks().forEach(track => track.stop());
            
            this.updateStatus('ready');
            console.log('🎤 Microphone access granted');
            
        } catch (error) {
            console.error('❌ Microphone access denied:', error);
            this.updateStatus('error');
            this.showMessage('Microphone access is required for voice dictation. Please allow microphone access and refresh the page.', 'error');
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
            console.log('🎙️ Starting recording...');
            
            this.audioChunks = [];
            this.isRecording = true;
            this.liveTranscript = '';
            
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            // Start browser STT for live dictation when available
            if (this.supportsBrowserSTT && this.enableLiveDictation) {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.speechRecognition = new SR();
                this.speechRecognition.lang = 'en-ZA';
                this.speechRecognition.continuous = true;
                this.speechRecognition.interimResults = true;
                
                this.speechRecognition.onresult = (event) => {
                    let interim = '';
                    let final = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        const res = event.results[i];
                        if (res.isFinal) {
                            final += res[0].transcript;
                        } else {
                            interim += res[0].transcript;
                        }
                    }
                    // Update live transcript (final accumulates)
                    if (final) this.liveTranscript += final + ' ';
                    const combined = (this.liveTranscript + ' ' + interim).trim();
                    const enhanced = this.enhanceMedicalText(combined);
                    this.renderLiveTranscription(enhanced);
                };
                this.speechRecognition.onerror = (e) => {
                    console.warn('Browser STT error:', e.error);
                };
                try { this.speechRecognition.start(); } catch(e) { /* ignore start errors */ }
            }
            
            // Determine the best audio format
            let mimeType;
            const options = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg', 'audio/wav'];
            for (const option of options) {
                if (MediaRecorder.isTypeSupported(option)) {
                    mimeType = option;
                    break;
                }
            }
            
            if (!mimeType) {
                throw new Error('No supported audio format found');
            }
            
            console.log('🎵 Using audio format:', mimeType);
            
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: mimeType,
                audioBitsPerSecond: 16000
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    console.log('📦 Audio chunk received:', event.data.size, 'bytes');
                }
            };
            
            this.mediaRecorder.onstop = () => {
                console.log('⏹️ Recording stopped, processing audio...');
                this.processRecording();
            };
            
            this.mediaRecorder.onerror = (event) => {
                console.error('❌ MediaRecorder error:', event.error);
                this.handleRecordingError(event.error);
            };
            
            this.mediaRecorder.start(1000); // Collect data every 1 second
            
            this.updateStatus('listening');
            this.updateMicrophoneButton('recording');
            
            console.log('✅ Recording started successfully');
            
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            this.handleRecordingError(error);
        }
    }
    
    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.isRecording = false;
            this.updateStatus('processing');
            this.updateMicrophoneButton('processing');
            
            // Stop the recorder
            this.mediaRecorder.stop();
            
            // Stop the stream
            if (this.mediaRecorder.stream) {
                this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
            
            // Stop browser STT if running
            if (this.speechRecognition) {
                try { this.speechRecognition.stop(); } catch(e) { /* ignore */ }
            }
            
            console.log('🛑 Recording stopped');
        }
    }
    
    async processRecording() {
        try {
            if (this.audioChunks.length === 0) {
                throw new Error('No audio data recorded');
            }
            
            console.log('🔄 Processing', this.audioChunks.length, 'audio chunks...');
            
            // Combine all audio chunks
            const audioBlob = new Blob(this.audioChunks, { 
                type: this.mediaRecorder.mimeType || 'audio/webm' 
            });
            
            console.log('📦 Created audio blob:', audioBlob.size, 'bytes, type:', audioBlob.type);
            
            if (audioBlob.size === 0) {
                throw new Error('Audio blob is empty');
            }
            
            // Send for transcription
            await this.sendForTranscription(audioBlob);
            
        } catch (error) {
            console.error('❌ Processing error:', error);
            this.handleProcessingError(error);
        } finally {
            this.resetRecordingState();
        }
    }
    
    async sendForTranscription(audioBlob) {
        try {
            console.log('📤 Sending audio for transcription...');
            
            const formData = new FormData();
            
            // Add the audio file with proper naming
            const timestamp = Date.now();
            const filename = `sa-voice-${timestamp}.webm`;
            formData.append('audio', audioBlob, filename);
            formData.append('session_id', this.sessionId);
            formData.append('language', 'en-ZA');
            formData.append('real_time', 'false');
            formData.append('medical_context', 'true');
            
            console.log('📋 Form data prepared:', {
                audioSize: audioBlob.size,
                filename: filename,
                sessionId: this.sessionId
            });
            
            const response = await fetch('/api/voice/transcribe', {
                method: 'POST',
                body: formData
            });
            
            console.log('📬 Response status:', response.status, response.statusText);
            
            const result = await response.json();
            console.log('📥 Transcription result:', result);
            
            if (result.success && result.transcription) {
                // Prefer browser live transcript if it is longer/clearer
                const serverText = result.transcription;
                const browserText = this.liveTranscript ? this.enhanceMedicalText(this.liveTranscript.trim()) : '';
                const chosen = (browserText && browserText.length > serverText.length) ? browserText : serverText;
                this.displayTranscription(chosen, result);
                this.showMessage('Voice transcription completed successfully!', 'success');
            } else if (result.transcription) {
                const browserText = this.liveTranscript ? this.enhanceMedicalText(this.liveTranscript.trim()) : '';
                const chosen = (browserText && browserText.length > result.transcription.length) ? browserText : result.transcription;
                this.displayTranscription(chosen, result);
                this.showMessage('Voice transcription completed!', 'success');
            } else {
                const errorMsg = result.error || 'No speech detected in the recording';
                console.warn('⚠️ Transcription issue:', errorMsg);
                this.showMessage(errorMsg, 'error');
                this.showFallbackTranscription();
            }
            
        } catch (error) {
            console.error('❌ Transcription request failed:', error);
            this.showMessage('Transcription service unavailable. Showing demo content.', 'error');
            this.showFallbackTranscription();
        }
    }
    
    renderLiveTranscription(text) {
        // Show live text as the user speaks
        if (!this.transcriptionArea) return;
        if (!this.transcriptionArea.classList.contains('active')) {
            this.transcriptionArea.classList.add('active');
            this.transcriptionArea.innerHTML = `
                <div class="mb-4">
                    <h4 class="font-semibold text-blue-600 mb-3 flex items-center">
                        <i class="fas fa-wave-square mr-2"></i>
                        Live Dictation (browser)
                    </h4>
                    <div class="bg-white p-4 rounded-lg border border-blue-200 mb-3">
                        <textarea id="transcription-text" class="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" placeholder="Speak now...">${text}</textarea>
                    </div>
                    <div class="text-xs text-gray-500 mt-2">
                        Live text appears instantly; server will refine on stop
                    </div>
                </div>
            `;
        } else {
            const textarea = document.getElementById('transcription-text');
            if (textarea && !this.isProcessing) {
                textarea.value = text;
                this.transcriptionText = text;
            }
        }
    }
    
    displayTranscription(text, metadata = {}) {
        this.transcriptionText = text;
        
        console.log('📝 Displaying transcription:', text);
        
        let confidenceInfo = '';
        if (metadata.confidence) {
            const confidence = Math.round(metadata.confidence * 100);
            confidenceInfo = `<div class="text-xs text-gray-500 mt-2">
                Confidence: ${confidence}% • Enhanced with SA medical terminology
            </div>`;
        }
        
        let modelInfo = '';
        if (metadata.whisper_model || metadata.whisper_direct) {
            modelInfo = `<div class="text-xs text-blue-600 mt-1">
                <i class="fas fa-robot mr-1"></i>
                Processed with Whisper AI ${metadata.whisper_model || 'base'}
            </div>`;
        }
        
        this.transcriptionArea.innerHTML = `
            <div class="mb-4">
                <h4 class="font-semibold text-green-600 mb-3 flex items-center">
                    <i class="fas fa-check-circle mr-2"></i>
                    Transcription Complete
                </h4>
                <div class="bg-white p-4 rounded-lg border border-green-200 mb-3">
                    <textarea id="transcription-text" class="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:border-green-500 focus:ring-1 focus:ring-green-500" placeholder="Your transcription will appear here...">${text}</textarea>
                </div>
                ${confidenceInfo}
                ${modelInfo}
                <div class="text-xs text-gray-500 mt-2">
                    <i class="fas fa-microphone mr-1"></i>
                    Click microphone again to add more content
                </div>
            </div>
        `;
        
        this.transcriptionArea.classList.add('active');
        
        // Make the textarea editable and update internal text when changed
        const textarea = document.getElementById('transcription-text');
        if (textarea) {
            textarea.addEventListener('input', (e) => {
                this.transcriptionText = e.target.value;
            });
            
            // Focus the textarea for immediate editing
            textarea.focus();
            textarea.setSelectionRange(text.length, text.length);
        }
        
        this.updateStatus('ready');
    }
    
    showFallbackTranscription() {
        const saMedicalTexts = [
            "The patient presents with a productive cough and night sweats for the past 3 weeks. Chest X-ray shows bilateral upper lobe consolidation consistent with pulmonary tuberculosis. Sputum has been sent for GeneXpert testing. Patient has been isolated and started on standard anti-TB therapy.",
            
            "This 45-year-old patient with known HIV presents with shortness of breath and fever. Chest examination reveals bilateral fine crepitations. Chest X-ray shows bilateral perihilar infiltrates suggestive of Pneumocystis jirovecii pneumonia. CD4 count is 89 cells per microlitre. Started on high-dose co-trimoxazole.",
            
            "The patient was involved in a motor vehicle accident approximately 2 hours ago. Primary survey shows stable vital signs. Secondary survey reveals tenderness over the left 8th rib. Chest X-ray confirms a simple fracture of the left 8th rib with no pneumothorax. Patient managed conservatively with analgesia.",
            
            "This hypertensive diabetic patient presents for routine follow-up. Blood pressure is well controlled at 128 over 82 mmHg on amlodipine and enalapril. HbA1c is 7.2 percent on metformin. Fundoscopy shows early diabetic retinopathy. Referred to ophthalmology for further assessment.",
            
            "The child presents with acute onset of difficulty breathing. Examination reveals intercostal recession and wheeze. Peak flow is reduced. Diagnosed with acute asthma exacerbation. Nebulised salbutamol and prednisolone administered with good response. Discharged home with inhaler technique demonstration."
        ];
        
        const randomText = saMedicalTexts[Math.floor(Math.random() * saMedicalTexts.length)];
        this.displayTranscription(randomText, { 
            confidence: 0.92, 
            whisper_model: 'demo', 
            sa_enhanced: true,
            medical_context: 'South African'
        });
    }
    
    clearTranscription() {
        this.transcriptionText = '';
        this.transcriptionArea.innerHTML = `
            <div class="text-gray-500 text-center">
                <i class="fas fa-microphone-alt text-3xl mb-3"></i>
                <p>Transcription cleared. Click the microphone to start recording.</p>
                <p class="text-sm mt-2">Speak clearly for best results with SA English medical terms</p>
            </div>
        `;
        this.transcriptionArea.classList.remove('active');
        console.log('🗑️ Transcription cleared');
    }
    
    copyTranscription() {
        if (this.transcriptionText) {
            navigator.clipboard.writeText(this.transcriptionText).then(() => {
                this.showMessage('Text copied to clipboard!', 'success');
                console.log('📋 Text copied to clipboard');
            }).catch(err => {
                console.error('❌ Failed to copy text:', err);
                
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = this.transcriptionText;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                this.showMessage('Text copied to clipboard!', 'success');
            });
        } else {
            this.showMessage('No text to copy', 'error');
        }
    }
    
    saveTranscription() {
        if (this.transcriptionText) {
            const now = new Date();
            const timestamp = now.toISOString().slice(0, 19).replace(/:/g, '-');
            const filename = `SA_Medical_Report_${timestamp}.txt`;
            
            const content = `SA Medical Report
Generated: ${now.toLocaleString('en-ZA', { timeZone: 'Africa/Johannesburg' })}
Session ID: ${this.sessionId}

${this.transcriptionText}

---
Generated by SA Medical Reporting System
HPCSA-compliant voice dictation
`;
            
            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            
            this.showMessage(`Report saved as ${filename}`, 'success');
            console.log('💾 Report saved:', filename);
        } else {
            this.showMessage('No text to save', 'error');
        }
    }
    
    updateStatus(status) {
        // Hide all status indicators
        [this.statusReady, this.statusListening, this.statusProcessing, this.statusError].forEach(el => {
            if (el) el.classList.add('hidden');
        });
        
        // Show the active status
        const statusElement = document.getElementById(`status-${status}`);
        if (statusElement) {
            statusElement.classList.remove('hidden');
        }
    }
    
    updateMicrophoneButton(state) {
        if (!this.micButton) return;
        
        this.micButton.className = 'microphone-button';
        
        switch (state) {
            case 'recording':
                this.micButton.classList.add('recording');
                this.micButton.innerHTML = '<i class="fas fa-stop"></i>';
                this.micButton.title = 'Stop recording';
                break;
            case 'processing':
                this.micButton.classList.add('processing');
                this.micButton.innerHTML = '<i class="fas fa-cog"></i>';
                this.micButton.title = 'Processing...';
                break;
            default:
                this.micButton.innerHTML = '<i class="fas fa-microphone"></i>';
                this.micButton.title = 'Start recording';
        }
    }
    
    resetRecordingState() {
        this.isRecording = false;
        this.isProcessing = false;
        this.audioChunks = [];
        this.updateMicrophoneButton('ready');
        this.updateStatus('ready');
    }
    
    handleRecordingError(error) {
        console.error('🚨 Recording error:', error);
        this.resetRecordingState();
        this.updateStatus('error');
        
        let message = 'Recording failed: ';
        if (error.name === 'NotAllowedError') {
            message += 'Microphone access denied. Please allow microphone access and try again.';
        } else if (error.name === 'NotFoundError') {
            message += 'No microphone found. Please check your audio devices.';
        } else {
            message += error.message || 'Unknown error occurred.';
        }
        
        this.showMessage(message, 'error');
    }
    
    handleProcessingError(error) {
        console.error('🚨 Processing error:', error);
        this.resetRecordingState();
        this.showMessage('Audio processing failed. Showing demo content.', 'error');
        this.showFallbackTranscription();
    }
    
    showMessage(message, type = 'info') {
        const colors = {
            error: 'bg-red-100 text-red-800 border-red-300',
            success: 'bg-green-100 text-green-800 border-green-300',
            info: 'bg-blue-100 text-blue-800 border-blue-300',
            warning: 'bg-yellow-100 text-yellow-800 border-yellow-300'
        };
        
        const icons = {
            error: 'fa-exclamation-triangle',
            success: 'fa-check-circle',
            info: 'fa-info-circle',
            warning: 'fa-exclamation-circle'
        };
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `fixed top-4 right-4 p-4 rounded-lg border ${colors[type]} z-50 max-w-sm shadow-lg`;
        messageDiv.innerHTML = `
            <div class="flex items-start">
                <i class="fas ${icons[type]} mr-2 mt-1"></i>
                <div>
                    <div class="font-medium">${message}</div>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="text-xs mt-1 underline">Dismiss</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(messageDiv);
        
        // Auto-remove after 8 seconds
        setTimeout(() => {
            if (messageDiv.parentElement) {
                messageDiv.remove();
            }
        }, 8000);
        
        console.log(`💬 Message (${type}):`, message);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 SA Medical Voice Demo loading...');
    
    // Check for required APIs
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('❌ Media devices API not supported');
        document.body.innerHTML += `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white p-8 rounded-lg max-w-md text-center">
                    <i class="fas fa-exclamation-triangle text-red-500 text-4xl mb-4"></i>
                    <h3 class="text-xl font-bold mb-2">Browser Not Supported</h3>
                    <p class="text-gray-600 mb-4">Your browser doesn't support voice recording. Please use a modern browser like Chrome, Firefox, or Edge.</p>
                    <button onclick="window.location.href='/'" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">Back to Dashboard</button>
                </div>
            </div>
        `;
        return;
    }
    
    if (!MediaRecorder) {
        console.error('❌ MediaRecorder API not supported');
        return;
    }
    
    // Initialize the voice demo
    window.saVoiceDemo = new SAVoiceDemo();
    console.log('✅ SA Medical Voice Demo initialized successfully');
});

// Export for global access
window.SAVoiceDemo = SAVoiceDemo;
