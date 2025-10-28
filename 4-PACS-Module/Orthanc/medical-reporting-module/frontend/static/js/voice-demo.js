/**
 * SA Medical Voice Demo - Modular Version
 * Main coordinator class that uses modular components
 */

class SAVoiceDemo {
    constructor() {
        // Guard against duplicate construction
        if (window._saVoiceDemoInstance) {
            console.warn('⚠️ Voice demo instance already exists, skipping re-initialization');
            return;
        }
        window._saVoiceDemoInstance = this;
        
        // Initialize modules
        this.audioProcessor = new AudioProcessor();
        this.uiManager = new UIManager();
        this.transcriptionService = new TranscriptionService();
        this.shortcutsManager = new ShortcutsManager();
        
        // State
        this.currentMode = 'dictation';
        this.isRecording = false;
        this.transcriptionText = '';
        this.userId = 'demo_user';
        this.initializationTimeout = null;
        
        this.initialize();
    }
    
    async initialize() {
        try {
            console.log('🇿🇦 Initializing SA Medical Voice Demo...');
            
            // Set a timeout for initialization (30 seconds)
            this.initializationTimeout = setTimeout(() => {
                console.warn('⚠️ Voice demo initialization timeout (30 seconds)');
                this.uiManager.showError('Initialization is taking longer than expected. Voice may have limited functionality.');
                this.uiManager.setStatus('warning', 'Partial initialization');
            }, 30000);
            
            // Setup UI callbacks
            this.uiManager.setCallbacks({
                onToggleRecording: () => this.toggleRecording(),
                onClearTranscription: () => this.clearTranscription(),
                onCopyTranscription: () => this.copyTranscription(),
                onSaveReport: () => this.saveReport(),
                onLoadTemplate: (template) => this.loadTemplate(template),
                onModeChange: (mode) => this.switchMode(mode),
                onEditTranscription: () => this.editTranscription()
            });
            
            // Setup audio processor callbacks
            // We intentionally do NOT process chunks in real-time for dictation to
            // avoid partial WebM/FFmpeg issues. The onChunkReady handler will be
            // enabled only when recording shortcuts (where immediate processing is required).
            this.audioProcessor.onChunkReady = null;
            this.audioProcessor.onRecordingStart = () => {
                this.uiManager.setStatus('listening', 'Recording...');
            };
            this.audioProcessor.onRecordingStop = () => {
                this.uiManager.setStatus('ready', 'Recording stopped');
            };
            this.audioProcessor.onError = (type, message) => {
                this.uiManager.showError(`Audio error: ${message}`);
                this.uiManager.setStatus('error', message);
            };
            
            // Setup transcription service callbacks
            this.transcriptionService.setCallbacks({
                onOfflineChunkProcessed: (result) => {
                    if (result.success) {
                        this.handleTranscriptionResult(result);
                    }
                }
            });
            
            // Setup shortcuts manager callbacks
            this.shortcutsManager.setCallbacks({
                onShortcutMatched: (shortcut, confidence) => {
                    this.handleShortcutMatch(shortcut, confidence);
                },
                onShortcutsUpdated: (shortcuts) => {
                    this.uiManager.updateShortcutsList(shortcuts);
                },
                onError: (message) => {
                    this.uiManager.showError(`Shortcuts error: ${message}`);
                }
            });
            
            // Initialize audio
            const audioResult = await this.audioProcessor.initializeAudio();
            if (!audioResult.success) {
                this.uiManager.showError('Failed to initialize microphone. Please check permissions.');
                return;
            }
            
            // Start transcription session
            const sessionResult = await this.transcriptionService.startSession({
                userId: this.userId
            });
            if (!sessionResult.success) {
                this.uiManager.showError('Failed to start transcription session.');
            }
            
            // Load user shortcuts
            await this.shortcutsManager.loadUserShortcuts();
            
            // Start audio visualizer
            this.startAudioVisualizer();
            
            // Set initial status
            this.uiManager.setStatus('ready', 'Ready to record');
            
            // Clear initialization timeout since we completed successfully
            if (this.initializationTimeout) {
                clearTimeout(this.initializationTimeout);
                this.initializationTimeout = null;
            }
            
            console.log('✅ SA Medical Voice Demo initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize voice demo:', error);
            this.uiManager.showError('Failed to initialize voice demo. Please refresh the page.');
            // Clear initialization timeout
            if (this.initializationTimeout) {
                clearTimeout(this.initializationTimeout);
                this.initializationTimeout = null;
            }
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
        if (this.isRecording) return;
        
        try {
            const success = this.audioProcessor.startRecording();
            if (success) {
                this.isRecording = true;
                // Immediately update UI so the microphone button turns red/indicates recording
                try {
                    this.uiManager.setStatus('listening', 'Recording...');
                } catch (e) {
                    console.warn('Failed to update UI status on startRecording', e);
                }
                // Enable per-chunk processing only for shortcuts mode
                if (this.currentMode === 'shortcuts') {
                    this.audioProcessor.onChunkReady = (audioBlob, chunkId, sequenceNumber) => {
                        return this.processAudioChunk(audioBlob, chunkId, sequenceNumber);
                    };
                } else {
                    this.audioProcessor.onChunkReady = null;
                }

                console.log('🎤 Recording started');
            } else {
                this.uiManager.showError('Failed to start recording');
            }
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.uiManager.showError('Failed to start recording');
        }
    }
    
    async stopRecording() {
        if (!this.isRecording) return;
        
        try {
            const success = this.audioProcessor.stopRecording();
            if (success) {
                this.isRecording = false;

                // Immediately update UI so the microphone button returns to ready state
                try {
                    this.uiManager.setStatus('ready', 'Recording stopped');
                } catch (e) {
                    console.warn('Failed to update UI status on stopRecording', e);
                }

                // Get full recording blob from audioProcessor and upload once
                const finalBlob = this.audioProcessor.getRecordedBlob();
                if (finalBlob) {
                    this.uiManager.setStatus('processing', 'Uploading full recording...');
                    const result = await this.transcriptionService.transcribeFinal(finalBlob);
                    if (result.success) {
                        // Apply same handling as chunk results
                        this.handleTranscriptionResult({ transcription: result.transcription });
                    } else {
                        this.uiManager.showError('Final transcription failed');
                    }
                }

                // Finalize session on server to trigger any backend assembly/cleanup
                await this.transcriptionService.finalizeSession();

                // Clear locally stored chunks after upload
                this.audioProcessor.clearRecordedChunks();

                console.log('🛑 Recording stopped');
            }
        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.uiManager.showError('Failed to stop recording');
        }
    }
    
    async processAudioChunk(audioBlob, chunkId, sequenceNumber) {
        try {
            // Only process chunks immediately when in 'shortcuts' mode or when
            // the shortcuts manager is actively recording a shortcut. For
            // regular dictation we buffer chunks locally and perform a single
            // transcription when the user presses Stop.

            // If shortcut recording is active, handle saving the shortcut audio
            if (this.shortcutsManager.isRecording()) {
                let audioToSend = audioBlob;
                try {
                    const wav = await this.audioProcessor.convertToWAV(audioBlob);
                    if (wav) audioToSend = wav;
                } catch (e) {
                    console.warn('Client WAV conversion failed for shortcut, sending original blob', e);
                }

                const result = await this.shortcutsManager.saveShortcutAudio(audioToSend);
                if (result.success) {
                    this.uiManager.showSuccess('Voice shortcut created successfully!');
                    this.switchMode('shortcuts');
                } else {
                    this.uiManager.showError('Failed to create voice shortcut');
                }
                return;
            }

            // If we are NOT in shortcuts mode, do not call server per-chunk.
            if (this.currentMode !== 'shortcuts') {
                // Chunks are already buffered by audioProcessor; nothing to do.
                return;
            }

            // From here on we are in shortcuts mode: perform matching/transcription
            // Convert to WAV for matching where possible
            let matchAudio = audioBlob;
            try {
                const wav2 = await this.audioProcessor.convertToWAV(audioBlob);
                if (wav2) matchAudio = wav2;
            } catch (e) {
                console.warn('Client WAV conversion for matching failed, proceeding with original blob', e);
            }

            const shortcutResult = await this.shortcutsManager.matchVoiceCommand(matchAudio);
            if (shortcutResult.success && shortcutResult.match.matched) {
                // Shortcut matched, don't transcribe
                return;
            }

            // Regular transcription in shortcuts mode
            this.uiManager.setStatus('processing', 'Transcribing...');
            let transcribeAudio = audioBlob;
            try {
                const wav3 = await this.audioProcessor.convertToWAV(audioBlob);
                if (wav3) transcribeAudio = wav3;
            } catch (e) {
                console.warn('Client WAV conversion for transcription failed, sending original blob', e);
            }

            const result = await this.transcriptionService.transcribeChunk(
                transcribeAudio,
                chunkId,
                sequenceNumber
            );

            if (result.success) {
                this.handleTranscriptionResult(result);
            } else {
                console.error('Transcription failed:', result.error);
                this.uiManager.setStatus('error', 'Transcription failed');
            }

        } catch (error) {
            console.error('Failed to process audio chunk:', error);
            this.uiManager.setStatus('error', 'Processing failed');
        }
    }
    
    handleTranscriptionResult(result) {
        if (!result.transcription) return;
        
        // Enhance medical text
        const enhancedText = this.transcriptionService.enhanceMedicalText(result.transcription);
        
        // Update UI
        this.uiManager.appendTranscription(enhancedText + ' ', true);
        this.transcriptionText += enhancedText + ' ';
        
        // Enable edit button when there's transcription
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            editBtn.disabled = false;
            editBtn.style.opacity = '1';
            editBtn.style.cursor = 'pointer';
            console.log('✅ Edit button enabled');
        } else {
            console.warn('⚠️ Edit button element not found in DOM');
        }
        
        // Set status back to listening if still recording
        if (this.isRecording) {
            this.uiManager.setStatus('listening', 'Recording...');
        } else {
            this.uiManager.setStatus('ready', 'Ready to record');
        }
        
        console.log(`📝 Transcription: "${enhancedText}"`);
    }
    
    handleShortcutMatch(shortcut, confidence) {
        console.log(`🎯 Shortcut matched: "${shortcut.name}" (${confidence})`);
        
        // Load the associated template
        this.loadTemplate(shortcut.template_id);
        
        // Show feedback
        this.uiManager.showSuccess(`Voice shortcut "${shortcut.name}" activated`);
    }
    
    clearTranscription() {
        this.transcriptionText = '';
        this.uiManager.clearTranscription();
        console.log('🗑️ Transcription cleared');
    }
    
    copyTranscription() {
        const text = this.uiManager.getTranscription();
        if (text) {
            navigator.clipboard.writeText(text).then(() => {
                this.uiManager.showSuccess('Transcription copied to clipboard');
            }).catch(() => {
                this.uiManager.showError('Failed to copy transcription');
            });
        }
    }
    
    async saveReport() {
        const text = this.uiManager.getTranscription();
        if (!text.trim()) {
            this.uiManager.showError('No transcription to save');
            return;
        }
        
        try {
            // In a real implementation, save to backend
            console.log('💾 Saving report:', text);
            this.uiManager.showSuccess('Report saved successfully');
        } catch (error) {
            console.error('Failed to save report:', error);
            this.uiManager.showError('Failed to save report');
        }
    }
    
    loadTemplate(templateId) {
        const templates = {
            consultation: `CONSULTATION NOTE

Date: ${new Date().toLocaleDateString()}
Patient: [Patient Name]
ID Number: [Patient ID]

CHIEF COMPLAINT:
[Chief complaint]

HISTORY OF PRESENT ILLNESS:
[History]

PHYSICAL EXAMINATION:
[Examination findings]

ASSESSMENT:
[Assessment]

PLAN:
[Treatment plan]

Dr. [Doctor Name]
[Qualification]`,
            
            discharge: `DISCHARGE SUMMARY

Patient: [Patient Name]
Admission Date: [Admission Date]
Discharge Date: ${new Date().toLocaleDateString()}

DIAGNOSIS:
[Primary and secondary diagnoses]

TREATMENT RECEIVED:
[Treatment summary]

DISCHARGE MEDICATIONS:
[Medications list]

FOLLOW-UP INSTRUCTIONS:
[Follow-up care]

Dr. [Doctor Name]`
        };
        
        const template = templates[templateId];
        if (template) {
            this.uiManager.setTranscription(template);
            this.transcriptionText = template;
            console.log(`📋 Template loaded: ${templateId}`);
        }
    }
    
    switchMode(mode) {
        this.currentMode = mode;
        
        // Stop recording when switching modes
        if (this.isRecording) {
            this.stopRecording();
        }
        
        console.log(`🔄 Switched to ${mode} mode`);
    }
    
    async editTranscription() {
        try {
            console.log('📝 Edit Transcription: Starting...');
            
            const text = this.uiManager.getTranscription();
            if (!text.trim()) {
                this.uiManager.showError('No transcription to edit');
                return;
            }
            
            console.log('📝 Edit Transcription: Text found, creating editor...');
            
            // Check if TranscriptionEditor exists
            if (typeof TranscriptionEditor === 'undefined') {
                console.error('❌ TranscriptionEditor class not found!');
                this.uiManager.showError('Editor not available. Please refresh the page.');
                return;
            }
            
            // Get current session ID for audio playback
            const sessionId = this.transcriptionService?.sessionId || null;
            console.log('📝 Edit Transcription: Session ID:', sessionId);
            
            // Create and show editor with session ID for audio playback
            const editor = new TranscriptionEditor(text, null, sessionId);
            console.log('📝 Edit Transcription: Editor created, showing modal...');
            
            const result = await editor.show();
            console.log('📝 Edit Transcription: Modal closed with result:', result);
            
            if (result.action === 'save') {
                // Update UI with corrected text
                this.uiManager.setTranscription(result.text);
                this.transcriptionText = result.text;
                console.log(`✅ Transcription updated and saved to training data (ID: ${result.sampleId})`);
                console.log(`📊 Quality Score: ${result.qualityScore}, Errors: ${result.errorCount}`);
            } else if (result.action === 'discard') {
                console.log('🗑️ Transcription discarded (not saved to training)');
            } else {
                console.log('⚪ Edit cancelled');
            }
        } catch (error) {
            console.error('❌ Error in editTranscription:', error);
            this.uiManager.showError(`Failed to open editor: ${error.message}`);
        }
    }
    
    startAudioVisualizer() {
        const updateVisualizer = () => {
            if (this.audioProcessor) {
                const level = this.audioProcessor.getAudioLevel();
                this.uiManager.updateAudioVisualizer(level);
            }
            requestAnimationFrame(updateVisualizer);
        };
        updateVisualizer();
    }
    
    // Cleanup method
    destroy() {
        // Clear initialization timeout
        if (this.initializationTimeout) {
            clearTimeout(this.initializationTimeout);
            this.initializationTimeout = null;
        }
        
        if (this.audioProcessor) {
            this.audioProcessor.cleanup();
        }
        
        if (this.transcriptionService) {
            this.transcriptionService.endSession();
        }
        
        // Clear instance reference
        window._saVoiceDemoInstance = null;
        
        console.log('🧹 Voice demo cleaned up');
    }
}

// Export for global access
window.SAVoiceDemo = SAVoiceDemo;

// Prevent duplicate initialization
let saVoiceDemoInitialized = false;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Guard against duplicate initialization
    if (saVoiceDemoInitialized) {
        console.warn('⚠️ Voice demo already initialized, skipping duplicate initialization');
        return;
    }
    saVoiceDemoInitialized = true;
    
    console.log('🇿🇦 Initializing SA Medical Voice Demo...');
    
    // Check for HTTPS
    if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
        console.warn('⚠️ HTTPS required for microphone access');
        return;
    }
    
    // Initialize voice demo
    try {
        window.saVoiceDemo = new SAVoiceDemo();
    } catch (error) {
        console.error('Failed to initialize voice demo:', error);
    }
}, { once: true });