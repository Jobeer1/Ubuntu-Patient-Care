/**
 * Transcription Service Module
 * Handles communication with the transcription API
 */

class TranscriptionService {
    constructor() {
        this.baseUrl = '/api/voice';
        this.sessionId = null;
        this.isOnline = navigator.onLine;
        this.offlineQueue = [];
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
        this.requestTimeout = 120000; // 2 minutes for transcription requests
        
        this.setupNetworkListeners();
    }
    
    setupNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processOfflineQueue();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }
    
    // Helper to add timeout to fetch calls
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeout = setTimeout(() => {
            controller.abort();
        }, options.timeout || this.requestTimeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeout);
            return response;
        } catch (error) {
            clearTimeout(timeout);
            if (error.name === 'AbortError') {
                throw new Error(`Request timeout after ${options.timeout || this.requestTimeout}ms`);
            }
            throw error;
        }
    }
    
    async startSession(options = {}) {
        try {
            const response = await this.fetchWithTimeout(`${this.baseUrl}/session/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: options.userId || 'demo_user',
                    report_id: options.reportId,
                    template_id: options.templateId
                }),
                timeout: 30000 // 30 second timeout for session start
            });
            
            if (!response.ok) {
                throw new Error(`Session start failed: ${response.status}`);
            }
            
            const data = await response.json();
            this.sessionId = data.session.session_id;
            
            console.log('✅ Voice session started:', this.sessionId);
            return { success: true, sessionId: this.sessionId };
            
        } catch (error) {
            console.error('Failed to start session:', error);
            return { success: false, error: error.message };
        }
    }
    
    async endSession() {
        if (!this.sessionId) {
            return { success: true };
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/session/end`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Session end failed: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ Voice session ended:', this.sessionId);
            
            this.sessionId = null;
            return { success: true, data };
            
        } catch (error) {
            console.error('Failed to end session:', error);
            return { success: false, error: error.message };
        }
    }
    
    async transcribeChunk(audioBlob, chunkId, sequenceNumber) {
        if (!this.isOnline) {
            return this.queueForOfflineProcessing(audioBlob, chunkId, sequenceNumber);
        }
        
        return this.processChunkWithRetry(audioBlob, chunkId, sequenceNumber);
    }
    
    async processChunkWithRetry(audioBlob, chunkId, sequenceNumber, attempt = 1) {
        try {
            const formData = new FormData();
            // Use blob.type to determine correct extension (e.g., audio/wav)
            let extension = 'webm';
            if (audioBlob && audioBlob.type) {
                if (audioBlob.type.includes('wav')) extension = 'wav';
                else if (audioBlob.type.includes('mpeg') || audioBlob.type.includes('mp3')) extension = 'mp3';
                else if (audioBlob.type.includes('webm')) extension = 'webm';
            }
            formData.append('audio', audioBlob, `chunk_${chunkId}.${extension}`);
            formData.append('session_id', this.sessionId || 'demo');
            formData.append('chunk_id', chunkId);
            formData.append('sequence_number', sequenceNumber.toString());
            
            const response = await this.fetchWithTimeout(`${this.baseUrl}/transcribe-chunk`, {
                method: 'POST',
                body: formData,
                timeout: 120000 // 2 minute timeout for chunk transcription
            });
            
            if (!response.ok) {
                throw new Error(`Transcription failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            console.log(`✅ Chunk transcribed: ${chunkId} -> "${result.transcription}"`);
            
            return {
                success: true,
                transcription: result.transcription,
                chunkId,
                sequenceNumber,
                confidence: result.confidence || 0.9,
                processingTime: result.processing_time || 0
            };
            
        } catch (error) {
            console.error(`❌ Transcription attempt ${attempt} failed:`, error);
            
            if (attempt < this.retryAttempts) {
                // Exponential backoff
                const delay = this.retryDelay * Math.pow(2, attempt - 1);
                console.log(`⏳ Retrying in ${delay}ms...`);
                
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.processChunkWithRetry(audioBlob, chunkId, sequenceNumber, attempt + 1);
            }
            
            return {
                success: false,
                error: error.message,
                chunkId,
                sequenceNumber
            };
        }
    }
    
    queueForOfflineProcessing(audioBlob, chunkId, sequenceNumber) {
        console.log(`📴 Queuing chunk for offline processing: ${chunkId}`);
        
        this.offlineQueue.push({
            audioBlob,
            chunkId,
            sequenceNumber,
            timestamp: Date.now()
        });
        
        return {
            success: true,
            transcription: '[Processing when online...]',
            chunkId,
            sequenceNumber,
            queued: true
        };
    }
    
    async processOfflineQueue() {
        if (this.offlineQueue.length === 0) {
            return;
        }
        
        console.log(`🔄 Processing ${this.offlineQueue.length} queued chunks...`);
        
        const queue = [...this.offlineQueue];
        this.offlineQueue = [];
        
        for (const item of queue) {
            try {
                const result = await this.processChunkWithRetry(
                    item.audioBlob,
                    item.chunkId,
                    item.sequenceNumber
                );
                
                if (result.success && this.onOfflineChunkProcessed) {
                    this.onOfflineChunkProcessed(result);
                }
            } catch (error) {
                console.error('Failed to process queued chunk:', error);
                // Re-queue if still failing
                this.offlineQueue.push(item);
            }
        }
    }
    
    async finalizeSession() {
        if (!this.sessionId) {
            return { success: true };
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/session/${this.sessionId}/finalize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Session finalize failed: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ Session finalized:', data);
            
            return { success: true, data };
            
        } catch (error) {
            console.error('Failed to finalize session:', error);
            return { success: false, error: error.message };
        }
    }

    async transcribeFinal(audioBlob) {
        try {
            const formData = new FormData();
            let extension = 'webm';
            if (audioBlob && audioBlob.type) {
                if (audioBlob.type.includes('wav')) extension = 'wav';
                else if (audioBlob.type.includes('mpeg') || audioBlob.type.includes('mp3')) extension = 'mp3';
                else if (audioBlob.type.includes('webm')) extension = 'webm';
            }

            formData.append('audio', audioBlob, `final_recording.${extension}`);
            // Pass session_id so backend can store audio for later playback
            if (this.sessionId) {
                formData.append('session_id', this.sessionId);
            }

            // Use the dedicated single-file endpoint with timeout
            const response = await this.fetchWithTimeout(`${this.baseUrl}/transcribe`, {
                method: 'POST',
                body: formData,
                timeout: 120000 // 2 minute timeout for transcription
            });

            if (!response.ok) {
                throw new Error(`Final transcription failed: ${response.status}`);
            }

            const data = await response.json();
            return { success: true, transcription: data.transcription || data.final_transcription || '' };
        } catch (error) {
            console.error('Failed to transcribe final recording:', error);
            return { success: false, error: error.message };
        }
    }
    
    async getSessionStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/session/status`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.status}`);
            }
            
            const data = await response.json();
            return { success: true, data };
            
        } catch (error) {
            console.error('Failed to get session status:', error);
            return { success: false, error: error.message };
        }
    }
    
    // Medical text enhancement
    enhanceMedicalText(text) {
        // South African medical terminology enhancements
        const saReplacements = {
            'bp': 'blood pressure',
            'hr': 'heart rate',
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
        enhanced = enhanced.replace(/(^|[.!?]\s+)([a-z])/g, (match, p1, p2) => {
            return p1 + p2.toUpperCase();
        });
        
        return enhanced;
    }
    
    // Event callback setters
    setCallbacks(callbacks) {
        this.onOfflineChunkProcessed = callbacks.onOfflineChunkProcessed;
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TranscriptionService;
} else {
    window.TranscriptionService = TranscriptionService;
}