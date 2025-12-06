/**
 * Transcription Editor Module
 * Allows users to edit and correct transcriptions before saving to training data
 */

class TranscriptionEditor {
    constructor(transcriptionText, audioFile = null, sessionId = null) {
        this.originalText = transcriptionText;
        this.currentText = transcriptionText;
        this.audioFile = audioFile;
        this.sessionId = sessionId;  // Session ID for fetching audio URL
        this.isModified = false;
        this.qualityScore = 0;
        this.errorCount = 0;
        this.modalId = `editor-${Date.now()}`;
        this.audioPlayer = null;  // Reference to audio element
        
        this.medicalTerms = [
            'blood pressure', 'heart rate', 'temperature', 'tuberculosis',
            'pneumonia', 'diabetes', 'hypertension', 'ecg', 'x-ray',
            'chest', 'abdomen', 'respiratory', 'cardiovascular', 'oxygen saturation'
        ];
    }
    
    /**
     * Open editor modal for user to correct transcription
     */
    show() {
        // Inject styles if not already done
        this.injectStyles();
        
        const modal = this.createModal();
        document.body.appendChild(modal);
        
        // Focus text area
        const textArea = modal.querySelector('.transcription-edit-area');
        textArea.focus();
        textArea.select();
        
        return new Promise((resolve) => {
            this.resolvePromise = resolve;
        });
    }
    
    createModal() {
        const modal = document.createElement('div');
        modal.id = this.modalId;
        modal.className = 'transcription-editor-modal';
        
        // Build audio player HTML if we have audio
        let audioPlayerHtml = '';
        if (this.sessionId) {
            audioPlayerHtml = `
                <div class="audio-section">
                    <label>🔊 Listen to Your Recording:</label>
                    <div class="audio-player-wrapper">
                        <audio 
                            id="transcription-audio"
                            class="audio-player"
                            src="/api/training/audio/${this.sessionId}"
                            controls
                            style="width: 100%; max-width: 400px;"
                        >
                            Your browser does not support the audio element.
                        </audio>
                        <div class="audio-status" style="font-size: 12px; color: #6b7280; margin-top: 8px;">
                            💡 Listen to verify your corrections are accurate
                        </div>
                        <div class="audio-actions" style="display: flex; gap: 10px; margin-top: 10px;">
                            <button class="copy-audio-btn" title="Copy audio file URL and transcription" style="padding: 6px 12px; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
                                📋 Copy Audio & Text
                            </button>
                            <button class="download-audio-btn" title="Download audio file" style="padding: 6px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
                                ⬇️ Download Audio
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        modal.innerHTML = `
            <div class="editor-overlay">
                <div class="editor-container">
                    <div class="editor-header">
                        <h3>✏️ Edit Transcription</h3>
                        <button class="close-btn" aria-label="Close">&times;</button>
                    </div>
                    
                    <div class="editor-content">
                        ${audioPlayerHtml}
                        
                        <div class="original-section">
                            <label>Original Transcription:</label>
                            <div class="original-text">${this.escapeHtml(this.originalText)}</div>
                        </div>
                        
                        <div class="edit-section">
                            <label for="transcription-edit">Corrected Transcription:</label>
                            <textarea 
                                id="transcription-edit" 
                                class="transcription-edit-area"
                                placeholder="Correct the transcription here..."
                            >${this.escapeHtml(this.currentText)}</textarea>
                            
                            <div class="editor-toolbar">
                                <button class="medical-terms-btn" title="Show medical terms reference">
                                    📖 Medical Terms
                                </button>
                                <button class="undo-btn" title="Reset to original">
                                    ↶ Reset
                                </button>
                            </div>
                        </div>
                        
                        <div class="quality-metrics">
                            <div class="metric">
                                <span class="label">Differences:</span>
                                <span class="value error-count">0 words</span>
                            </div>
                            <div class="metric">
                                <span class="label">Quality Score:</span>
                                <span class="value quality-score">0.0</span>
                                <div class="quality-bar">
                                    <div class="quality-fill"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="notes-section">
                            <label for="correction-notes">Notes (optional):</label>
                            <textarea 
                                id="correction-notes"
                                class="correction-notes"
                                placeholder="Why was this correction needed? (e.g., 'Patient name was misheard')"
                                rows="3"
                            ></textarea>
                        </div>
                    </div>
                    
                    <div class="editor-footer">
                        <button class="btn btn-secondary cancel-btn">Cancel</button>
                        <button class="btn btn-danger discard-btn">Discard</button>
                        <button class="btn btn-primary save-btn">✅ Save & Use for Training</button>
                    </div>
                </div>
            </div>
        `;
        
        // Bind events
        const textArea = modal.querySelector('.transcription-edit-area');
        const medicalTermsBtn = modal.querySelector('.medical-terms-btn');
        const undoBtn = modal.querySelector('.undo-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');
        const discardBtn = modal.querySelector('.discard-btn');
        const saveBtn = modal.querySelector('.save-btn');
        const closeBtn = modal.querySelector('.close-btn');
        const copyAudioBtn = modal.querySelector('.copy-audio-btn');
        const downloadAudioBtn = modal.querySelector('.download-audio-btn');
        
        textArea.addEventListener('input', () => this.updateMetrics(modal));
        medicalTermsBtn.addEventListener('click', () => this.showMedicalTermsReference());
        undoBtn.addEventListener('click', () => this.resetToOriginal(modal));
        cancelBtn.addEventListener('click', () => this.handleCancel(modal));
        discardBtn.addEventListener('click', () => this.handleDiscard(modal));
        saveBtn.addEventListener('click', () => this.handleSave(modal));
        closeBtn.addEventListener('click', () => this.handleCancel(modal));
        
        // Add copy and download event listeners if buttons exist
        if (copyAudioBtn) {
            copyAudioBtn.addEventListener('click', () => this.copyAudioAndTranscription(modal));
        }
        if (downloadAudioBtn) {
            downloadAudioBtn.addEventListener('click', () => this.downloadAudio());
        }
        
        // Allow Ctrl+S to save
        modal.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                this.handleSave(modal);
            }
        });
        
        // Store audio player reference
        this.audioPlayer = modal.querySelector('audio');
        
        // Initialize metrics on creation
        setTimeout(() => this.updateMetrics(modal), 0);
        
        return modal;
    }
    
    updateMetrics(modal) {
        const textArea = modal.querySelector('.transcription-edit-area');
        this.currentText = textArea.value;
        this.isModified = this.currentText !== this.originalText;
        
        // Calculate error count (word-level differences)
        const origWords = this.originalText.toLowerCase().split(/\s+/);
        const corrWords = this.currentText.toLowerCase().split(/\s+/);
        
        let errorCount = 0;
        const maxLen = Math.max(origWords.length, corrWords.length);
        for (let i = 0; i < maxLen; i++) {
            const origWord = origWords[i] || '';
            const corrWord = corrWords[i] || '';
            if (origWord !== corrWord) {
                errorCount++;
            }
        }
        
        this.errorCount = errorCount;
        
        // Calculate quality score
        const origLength = origWords.length;
        const errorRate = origLength > 0 ? errorCount / origLength : 0;
        this.qualityScore = Math.max(0, 1.0 - errorRate);
        
        // Update UI
        modal.querySelector('.error-count').textContent = `${errorCount} word${errorCount !== 1 ? 's' : ''}`;
        modal.querySelector('.quality-score').textContent = this.qualityScore.toFixed(3);
        
        const qualityFill = modal.querySelector('.quality-fill');
        qualityFill.style.width = (this.qualityScore * 100) + '%';
        
        // Change color based on quality
        if (this.qualityScore >= 0.95) {
            qualityFill.style.backgroundColor = '#10b981'; // Green
        } else if (this.qualityScore >= 0.85) {
            qualityFill.style.backgroundColor = '#f59e0b'; // Amber
        } else {
            qualityFill.style.backgroundColor = '#ef4444'; // Red
        }
        
        // Enable/disable save button
        const saveBtn = modal.querySelector('.save-btn');
        saveBtn.disabled = !this.isModified;
    }
    
    resetToOriginal(modal) {
        const textArea = modal.querySelector('.transcription-edit-area');
        textArea.value = this.originalText;
        this.updateMetrics(modal);
    }
    
    showMedicalTermsReference() {
        alert('Common Medical Terms:\n\n' + this.medicalTerms.join('\n'));
    }
    
    handleCancel(modal) {
        if (this.isModified) {
            if (!confirm('You have unsaved changes. Discard them?')) {
                return;
            }
        }
        this.closeModal(modal);
        this.resolvePromise({ action: 'cancel', text: this.originalText });
    }
    
    handleDiscard(modal) {
        if (confirm('Discard this transcription? It will not be saved to training data.')) {
            this.closeModal(modal);
            this.resolvePromise({ action: 'discard', text: this.originalText });
        }
    }
    
    async handleSave(modal) {
        const notes = modal.querySelector('.correction-notes').value;
        
        try {
            // Prepare data for API
            const payload = {
                session_id: this.sessionId,
                original_transcription: this.originalText,
                corrected_transcription: this.currentText,
                error_count: this.errorCount,
                quality_score: this.qualityScore,
                tags: 'medical',
                notes: notes
            };
            
            console.log('💾 Saving corrected transcription to STT Training Data...', payload);
            
            // Save to training data
            const response = await fetch('/api/training/save-transcription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save training data');
            }
            
            const result = await response.json();
            
            console.log('✅ Training data saved:', result);
            alert(`✅ Saved to STT Training Data!\nQuality Score: ${this.qualityScore.toFixed(3)}\nDifferences: ${this.errorCount} words`);
            
            this.closeModal(modal);
            this.resolvePromise({ 
                action: 'save', 
                text: this.currentText,
                sampleId: result.training_sample_id,
                qualityScore: result.quality_score,
                errorCount: result.error_count
            });
            
        } catch (error) {
            console.error('❌ Error saving training data:', error);
            alert('❌ Failed to save training data. Check console for details.');
        }
    }
    
    closeModal(modal) {
        modal.remove();
    }
    
    /**
     * Copy audio file URL and transcription to clipboard
     */
    copyAudioAndTranscription(modal) {
        try {
            const audioUrl = `/api/training/audio/${this.sessionId}`;
            const transcription = modal.querySelector('.transcription-edit-area').value;
            
            // Create a formatted text with both audio URL and transcription
            const textToCopy = `Audio File: ${window.location.origin}${audioUrl}\n\nOriginal Transcription:\n${this.originalText}\n\nCorrected Transcription:\n${transcription}`;
            
            // Copy to clipboard
            navigator.clipboard.writeText(textToCopy).then(() => {
                console.log('✅ Audio URL and transcription copied to clipboard');
                
                // Show feedback
                const btn = modal.querySelector('.copy-audio-btn');
                const originalText = btn.textContent;
                btn.textContent = '✅ Copied!';
                btn.style.background = '#10b981';
                
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('❌ Failed to copy to clipboard:', err);
                alert('Failed to copy to clipboard. Please try again.');
            });
        } catch (error) {
            console.error('❌ Error copying audio and transcription:', error);
            alert('Failed to copy data');
        }
    }
    
    /**
     * Download audio file
     */
    downloadAudio() {
        try {
            console.log(`🔄 Starting audio download for session: ${this.sessionId}`);
            
            // Get the audio URL with download parameter
            const audioUrl = `/api/training/audio/${this.sessionId}?download=1`;
            const fullUrl = new URL(audioUrl, window.location.origin).href;
            
            console.log(`📥 Downloading from: ${fullUrl}`);
            
            // Fetch the audio file
            fetch(fullUrl, {
                method: 'GET',
                credentials: 'include' // Include cookies/auth
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                console.log(`✅ Audio blob received: ${blob.size} bytes`);
                
                // Create a blob URL
                const blobUrl = window.URL.createObjectURL(blob);
                
                // Create download link
                const link = document.createElement('a');
                link.href = blobUrl;
                link.download = `recording_${this.sessionId}.wav`;
                
                // Trigger download
                document.body.appendChild(link);
                link.click();
                
                // Cleanup
                setTimeout(() => {
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(blobUrl);
                    console.log('✅ Audio file download completed');
                }, 100);
            })
            .catch(error => {
                console.error('❌ Error downloading audio:', error);
                alert(`Failed to download audio: ${error.message}`);
            });
        } catch (error) {
            console.error('❌ Error in downloadAudio:', error);
            alert('Failed to download audio file');
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    injectStyles() {
        if (document.querySelector('#transcription-editor-styles')) {
            return; // Already injected
        }
        
        const style = document.createElement('style');
        style.id = 'transcription-editor-styles';
        style.textContent = `
            .transcription-editor-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .editor-overlay {
                position: absolute;
                inset: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
            }
            
            .editor-container {
                position: relative;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 800px;
                max-height: 90vh;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }
            
            .editor-header {
                padding: 20px;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .editor-header h3 {
                margin: 0;
                font-size: 18px;
                color: #1f2937;
            }
            
            .close-btn {
                background: none;
                border: none;
                font-size: 28px;
                cursor: pointer;
                color: #6b7280;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .close-btn:hover {
                color: #1f2937;
                background: #f3f4f6;
                border-radius: 6px;
            }
            
            .editor-content {
                padding: 20px;
                flex: 1;
                overflow-y: auto;
            }
            
            .audio-section {
                margin-bottom: 20px;
                padding: 16px;
                background: #f0f9ff;
                border: 2px solid #06b6d4;
                border-radius: 8px;
            }
            
            .audio-section label {
                display: block;
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                margin-bottom: 12px;
            }
            
            .audio-player-wrapper {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .audio-player {
                border-radius: 6px;
            }
            
            .audio-status {
                text-align: center;
                color: #0891b2;
                font-weight: 500;
            }
            
            .original-section {
                margin-bottom: 20px;
            }
            
            .original-section label {
                display: block;
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                margin-bottom: 8px;
            }
            
            .original-text {
                background: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                color: #1f2937;
                line-height: 1.6;
                min-height: 60px;
            }
            
            .edit-section {
                margin-bottom: 20px;
            }
            
            .edit-section label {
                display: block;
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                margin-bottom: 8px;
            }
            
            .transcription-edit-area {
                width: 100%;
                min-height: 120px;
                padding: 12px;
                border: 2px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                font-family: inherit;
                resize: vertical;
            }
            
            .transcription-edit-area:focus {
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }
            
            .editor-toolbar {
                display: flex;
                gap: 8px;
                margin-top: 12px;
            }
            
            .editor-toolbar button {
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background: white;
                cursor: pointer;
                font-size: 13px;
                color: #374151;
                transition: all 0.2s;
            }
            
            .editor-toolbar button:hover {
                background: #f3f4f6;
                border-color: #9ca3af;
            }
            
            .quality-metrics {
                display: flex;
                gap: 20px;
                padding: 16px;
                background: #f9fafb;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .metric {
                flex: 1;
            }
            
            .metric .label {
                display: block;
                font-size: 12px;
                font-weight: 600;
                color: #6b7280;
                text-transform: uppercase;
                margin-bottom: 6px;
            }
            
            .metric .value {
                display: block;
                font-size: 16px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 6px;
            }
            
            .quality-bar {
                height: 6px;
                background: #e5e7eb;
                border-radius: 3px;
                overflow: hidden;
            }
            
            .quality-fill {
                height: 100%;
                background: #10b981;
                transition: width 0.3s ease, background-color 0.3s ease;
            }
            
            .notes-section {
                margin-bottom: 20px;
            }
            
            .notes-section label {
                display: block;
                font-weight: 600;
                font-size: 14px;
                color: #374151;
                margin-bottom: 8px;
            }
            
            .correction-notes {
                width: 100%;
                padding: 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                font-family: inherit;
                resize: vertical;
            }
            
            .correction-notes:focus {
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }
            
            .editor-footer {
                padding: 16px 20px;
                border-top: 1px solid #e5e7eb;
                display: flex;
                gap: 12px;
                justify-content: flex-end;
                background: #f9fafb;
            }
            
            .btn {
                padding: 10px 16px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .btn-secondary {
                background: white;
                border: 1px solid #d1d5db;
                color: #374151;
            }
            
            .btn-secondary:hover {
                background: #f3f4f6;
                border-color: #9ca3af;
            }
            
            .btn-danger {
                background: #fee2e2;
                color: #991b1b;
            }
            
            .btn-danger:hover {
                background: #fecaca;
            }
            
            .btn-primary {
                background: #3b82f6;
                color: white;
            }
            
            .btn-primary:hover:not(:disabled) {
                background: #2563eb;
            }
            
            .btn-primary:disabled {
                background: #d1d5db;
                color: #9ca3af;
                cursor: not-allowed;
            }
        `;
        
        document.head.appendChild(style);
    }
}

// Export for global access
window.TranscriptionEditor = TranscriptionEditor;
