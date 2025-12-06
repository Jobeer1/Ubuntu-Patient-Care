/**
 * Audio Processing Module
 * Handles audio recording, processing, and conversion
 */

class AudioProcessor {
    constructor() {
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isProcessing = false;
        this.recordingStartTime = null;
        
        // Audio settings
        this.sampleRate = 16000;
        this.chunkDuration = 2000; // 2 seconds
        this.maxConcurrentRequests = 3;
        this.activeRequests = 0;
        
        // Event callbacks
        this.onChunkReady = null;
        this.onRecordingStart = null;
        this.onRecordingStop = null;
        this.onError = null;
    }
    
    async initializeAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.setupAudioContext(stream);
            this.setupMediaRecorder(stream);
            
            return { success: true };
        } catch (error) {
            console.error('Failed to initialize audio:', error);
            if (this.onError) {
                this.onError('microphone_access_denied', error.message);
            }
            return { success: false, error: error.message };
        }
    }
    
    setupAudioContext(stream) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.microphone = this.audioContext.createMediaStreamSource(stream);
        this.analyser = this.audioContext.createAnalyser();
        
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;
        
        this.microphone.connect(this.analyser);
    }
    
    setupMediaRecorder(stream) {
        // Try different MIME types for better compatibility
        const mimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/mp4',
            'audio/wav'
        ];
        
        let selectedMimeType = null;
        for (const mimeType of mimeTypes) {
            if (MediaRecorder.isTypeSupported(mimeType)) {
                selectedMimeType = mimeType;
                break;
            }
        }
        
        if (!selectedMimeType) {
            throw new Error('No supported audio format found');
        }
        
        this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: selectedMimeType,
            audioBitsPerSecond: 128000
        });
        
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.handleAudioChunk(event.data);
            }
        };
        
        this.mediaRecorder.onstop = () => {
            if (this.onRecordingStop) {
                this.onRecordingStop();
            }
        };
        
        this.mediaRecorder.onerror = (error) => {
            console.error('MediaRecorder error:', error);
            if (this.onError) {
                this.onError('recording_error', error.message);
            }
        };
    }
    
    startRecording() {
        if (!this.mediaRecorder || this.isRecording) {
            return false;
        }
        
        try {
            this.audioChunks = [];
            this.recordingStartTime = Date.now();
            this.isRecording = true;
            
            // Start recording with time slicing for real-time chunks
            this.mediaRecorder.start(this.chunkDuration);
            
            if (this.onRecordingStart) {
                this.onRecordingStart();
            }
            
            console.log('🎤 Recording started with chunk duration:', this.chunkDuration);
            return true;
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.isRecording = false;
            if (this.onError) {
                this.onError('recording_start_failed', error.message);
            }
            return false;
        }
    }
    
    stopRecording() {
        if (!this.mediaRecorder || !this.isRecording) {
            return false;
        }
        
        try {
            this.isRecording = false;
            this.mediaRecorder.stop();
            
            console.log('🛑 Recording stopped');
            return true;
        } catch (error) {
            console.error('Failed to stop recording:', error);
            if (this.onError) {
                this.onError('recording_stop_failed', error.message);
            }
            return false;
        }
    }
    
    handleAudioChunk(audioBlob) {
        if (!this.isRecording) {
            return; // Ignore chunks after recording stopped
        }

        const chunkId = `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const sequenceNumber = this.audioChunks.length;

        console.log(`🎵 Audio chunk ready (stored locally): ${chunkId} (${audioBlob.size} bytes)`);

        // Store chunk locally only. We intentionally avoid sending chunks to the
        // server while recording to prevent FFmpeg/WebM partial-chunk errors.
        this.audioChunks.push({
            id: chunkId,
            blob: audioBlob,
            sequence: sequenceNumber,
            timestamp: Date.now()
        });

        // Continue recording if still active
        if (this.isRecording && this.mediaRecorder.state === 'inactive') {
            try {
                this.mediaRecorder.start(this.chunkDuration);
            } catch (error) {
                console.error('Failed to restart recording:', error);
                if (this.onError) {
                    this.onError('recording_restart_failed', error.message);
                }
            }
        }
    }

    // Return a single Blob that concatenates recorded chunks (final recording)
    getRecordedBlob() {
        if (!this.audioChunks || this.audioChunks.length === 0) return null;
        const blobs = this.audioChunks.map(c => c.blob);
        // Use the first blob's type as the final mime type
        const type = blobs[0] && blobs[0].type ? blobs[0].type : 'audio/webm';
        return new Blob(blobs, { type });
    }

    clearRecordedChunks() {
        this.audioChunks = [];
    }
    
    getAudioLevel() {
        if (!this.analyser) {
            return 0;
        }
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
        }
        
        return sum / bufferLength / 255; // Normalize to 0-1
    }
    
    async convertToWAV(audioBlob) {
        try {
            const arrayBuffer = await audioBlob.arrayBuffer();
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            
            // Convert to WAV format
            const wavBuffer = this.audioBufferToWav(audioBuffer);
            return new Blob([wavBuffer], { type: 'audio/wav' });
        } catch (error) {
            console.error('Failed to convert to WAV:', error);
            throw error;
        }
    }
    
    audioBufferToWav(buffer) {
        const length = buffer.length;
        const sampleRate = buffer.sampleRate;
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);
        
        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * 2, true);
        
        // Convert audio data
        const channelData = buffer.getChannelData(0);
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, channelData[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
        
        return arrayBuffer;
    }
    
    cleanup() {
        if (this.mediaRecorder && this.mediaRecorder.stream) {
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }
        
        this.mediaRecorder = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isProcessing = false;
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioProcessor;
} else {
    window.AudioProcessor = AudioProcessor;
}