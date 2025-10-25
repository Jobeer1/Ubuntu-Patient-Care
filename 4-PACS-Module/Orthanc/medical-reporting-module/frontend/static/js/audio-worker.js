/**
 * Web Worker for audio processing
 * Handles WebM to WAV conversion without blocking the main UI thread
 */

// Audio conversion utilities
function audioBufferToWav(buffer) {
    const length = buffer.length;
    const numberOfChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8;
    const blockAlign = numberOfChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize;
    
    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);
    
    // Convert audio data
    let offset = 44;
    for (let i = 0; i < length; i++) {
        for (let channel = 0; channel < numberOfChannels; channel++) {
            const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
            view.setInt16(offset, sample * 0x7FFF, true);
            offset += 2;
        }
    }
    
    return arrayBuffer;
}

// Message handler
self.onmessage = async function(e) {
    const { type, data, chunkId } = e.data;
    
    try {
        switch (type) {
            case 'convertWebMToWAV':
                await convertWebMToWAV(data, chunkId);
                break;
                
            case 'compressAudio':
                await compressAudio(data, chunkId);
                break;
                
            default:
                self.postMessage({
                    type: 'error',
                    chunkId,
                    error: `Unknown message type: ${type}`
                });
        }
    } catch (error) {
        self.postMessage({
            type: 'error',
            chunkId,
            error: error.message
        });
    }
};

async function convertWebMToWAV(webmBlob, chunkId) {
    try {
        // Create audio context
        const audioContext = new (self.AudioContext || self.webkitAudioContext)();
        
        // Convert blob to array buffer
        const arrayBuffer = await webmBlob.arrayBuffer();
        
        // Decode audio data
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // Convert to WAV
        const wavBuffer = audioBufferToWav(audioBuffer);
        const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });
        
        self.postMessage({
            type: 'conversionComplete',
            chunkId,
            wavBlob,
            originalSize: webmBlob.size,
            convertedSize: wavBlob.size
        });
        
    } catch (error) {
        self.postMessage({
            type: 'error',
            chunkId,
            error: `WebM to WAV conversion failed: ${error.message}`
        });
    }
}

async function compressAudio(audioBlob, chunkId) {
    try {
        // Simple compression by reducing quality (if needed)
        // For now, just pass through - real compression would require more complex algorithms
        
        self.postMessage({
            type: 'compressionComplete',
            chunkId,
            compressedBlob: audioBlob,
            originalSize: audioBlob.size,
            compressedSize: audioBlob.size,
            compressionRatio: 1.0
        });
        
    } catch (error) {
        self.postMessage({
            type: 'error',
            chunkId,
            error: `Audio compression failed: ${error.message}`
        });
    }
}