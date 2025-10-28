/**
 * UI Manager Module
 * Handles all user interface updates and interactions
 */

class UIManager {
    constructor() {
        this.elements = {};
        this.statusStates = {
            ready: 'ready',
            listening: 'listening',
            processing: 'processing',
            error: 'error'
        };
        this.currentStatus = 'ready';
        
        this.initializeElements();
        this.setupEventListeners();
    }
    
    initializeElements() {
        // Main elements
        this.elements.micButton = document.getElementById('microphone-btn') || document.getElementById('microphoneButton');
        this.elements.transcriptionArea = document.getElementById('transcription-area') || document.getElementById('transcriptionArea');
        this.elements.audioVisualizer = document.getElementById('audio-visualizer') || document.getElementById('audioVisualizer');
        
        // Status indicators
        this.elements.statusReady = document.getElementById('status-ready');
        this.elements.statusListening = document.getElementById('status-listening');
        this.elements.statusProcessing = document.getElementById('status-processing');
        this.elements.statusError = document.getElementById('status-error');
        
        // Control buttons
        this.elements.clearBtn = document.getElementById('clear-btn');
        this.elements.copyBtn = document.getElementById('copy-btn');
        this.elements.saveBtn = document.getElementById('save-btn');
        
        // Training elements
        this.elements.trainingPanel = document.getElementById('training-panel');
        this.elements.trainingTerms = document.getElementById('training-terms');
        this.elements.trainingProgress = document.getElementById('training-progress');
        
        // Shortcuts elements
        this.elements.shortcutsPanel = document.getElementById('shortcuts-panel');
        this.elements.shortcutsList = document.getElementById('shortcuts-list');
        this.elements.createShortcutBtn = document.getElementById('create-shortcut-btn');
        
        // Mode tabs
        this.elements.dictationTab = document.getElementById('dictation-tab');
        this.elements.trainingTab = document.getElementById('training-tab');
        this.elements.shortcutsTab = document.getElementById('shortcuts-tab');
    }
    
    setupEventListeners() {
        // Microphone button - CRITICAL FIX
        if (this.elements.micButton) {
            this.elements.micButton.addEventListener('click', () => {
                if (this.onToggleRecording) {
                    this.onToggleRecording();
                }
            });
        }
        
        // Control buttons
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                console.log('🔵 Edit button clicked');
                if (this.onEditTranscription) {
                    console.log('📝 Calling onEditTranscription callback...');
                    this.onEditTranscription();
                } else {
                    console.warn('⚠️ onEditTranscription callback not set');
                }
            });
        }
        
        if (this.elements.clearBtn) {
            this.elements.clearBtn.addEventListener('click', () => {
                if (this.onClearTranscription) {
                    this.onClearTranscription();
                }
            });
        }
        
        if (this.elements.copyBtn) {
            this.elements.copyBtn.addEventListener('click', () => {
                if (this.onCopyTranscription) {
                    this.onCopyTranscription();
                }
            });
        }
        
        if (this.elements.saveBtn) {
            this.elements.saveBtn.addEventListener('click', () => {
                if (this.onSaveReport) {
                    this.onSaveReport();
                }
            });
        }
        
        // Template buttons
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const template = e.currentTarget.dataset.template;
                if (this.onLoadTemplate) {
                    this.onLoadTemplate(template);
                }
            });
        });
        
        // Mode tabs
        if (this.elements.dictationTab) {
            this.elements.dictationTab.addEventListener('click', () => this.switchMode('dictation'));
        }
        if (this.elements.trainingTab) {
            this.elements.trainingTab.addEventListener('click', () => this.switchMode('training'));
        }
        if (this.elements.shortcutsTab) {
            this.elements.shortcutsTab.addEventListener('click', () => this.switchMode('shortcuts'));
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.code === 'Space') {
                e.preventDefault();
                if (this.onToggleRecording) {
                    this.onToggleRecording();
                }
            }
        });
    }
    
    setStatus(status, message = '') {
        this.currentStatus = status;
        
        // Hide all status indicators
        Object.values(this.elements).forEach(element => {
            if (element && element.id && element.id.startsWith('status-')) {
                element.classList.add('hidden');
                element.style.display = 'none';
            }
        });
        
        // Show current status
        const statusElement = this.elements[`status${status.charAt(0).toUpperCase() + status.slice(1)}`];
        if (statusElement) {
            statusElement.classList.remove('hidden');
            statusElement.style.display = 'block';
            if (message) {
                statusElement.textContent = message;
            }
        }
        
        // Update microphone button
        this.updateMicrophoneButton(status);
        
        console.log(`📊 Status: ${status}${message ? ` - ${message}` : ''}`);
    }
    
    updateMicrophoneButton(status) {
        if (!this.elements.micButton) return;
        // Remove all possible status classes to avoid stale state
        this.elements.micButton.classList.remove('recording', 'listening', 'processing', 'error', 'ready');

        // Add current status class(s)
        // Templates/styles sometimes expect 'recording' class (not 'listening'),
        // so when status is 'listening' add both for compatibility.
        if (status === 'listening') {
            this.elements.micButton.classList.add('listening');
            this.elements.micButton.classList.add('recording');
        } else {
            this.elements.micButton.classList.add(status);
        }
        
        // Update button text/icon based on status
        const buttonText = this.elements.micButton.querySelector('.btn-text');
        if (buttonText) {
            switch (status) {
                case 'listening':
                    buttonText.textContent = 'Stop Recording';
                    break;
                case 'processing':
                    buttonText.textContent = 'Processing...';
                    break;
                case 'error':
                    buttonText.textContent = 'Error - Try Again';
                    break;
                default:
                    buttonText.textContent = 'Start Recording';
            }
        }
        
        // Disable button during processing
        this.elements.micButton.disabled = (status === 'processing');

        // Inline style fallback: some templates or utility classes may override
        // stylesheet rules. Set an explicit red gradient when listening so the
        // button turns red reliably. Clear inline styles for other statuses.
        if (status === 'listening') {
            try {
                this.elements.micButton.style.background = 'linear-gradient(135deg, #f44336, #d32f2f)';
                this.elements.micButton.style.color = '#ffffff';
                this.elements.micButton.style.boxShadow = '0 8px 24px rgba(239, 68, 68, 0.25)';
            } catch (e) {
                // ignore in case element doesn't accept style changes
            }
        } else {
            // remove any inline overrides so default stylesheet applies
            try {
                this.elements.micButton.style.background = '';
                this.elements.micButton.style.color = '';
                this.elements.micButton.style.boxShadow = '';
            } catch (e) {
                // ignore
            }
        }
    }
    
    appendTranscription(text, isNewChunk = false) {
        if (!this.elements.transcriptionArea) return;
        
        // Clear placeholder content on first transcription
        if (this.elements.transcriptionArea.querySelector('.text-gray-500')) {
            this.elements.transcriptionArea.innerHTML = '';
        }
        
        if (isNewChunk) {
            // Highlight new text briefly
            const span = document.createElement('span');
            span.className = 'new-transcription';
            span.textContent = text;
            
            this.elements.transcriptionArea.appendChild(span);
            
            // Remove highlight after animation
            setTimeout(() => {
                span.classList.remove('new-transcription');
            }, 1000);
        } else {
            this.elements.transcriptionArea.textContent += text;
        }
        
        // Auto-scroll to bottom
        this.elements.transcriptionArea.scrollTop = this.elements.transcriptionArea.scrollHeight;
        
        // Enable edit button when there's transcription
        const editBtn = document.getElementById('edit-btn');
        if (editBtn && text && text.trim()) {
            editBtn.disabled = false;
            editBtn.style.opacity = '1';
            editBtn.style.cursor = 'pointer';
        }
    }
    
    setTranscription(text) {
        if (this.elements.transcriptionArea) {
            this.elements.transcriptionArea.innerHTML = '';
            this.elements.transcriptionArea.textContent = text;
        }
        
        // Enable/disable edit button based on whether there's text
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            editBtn.disabled = !text || !text.trim();
            editBtn.style.opacity = editBtn.disabled ? '0.5' : '1';
            editBtn.style.cursor = editBtn.disabled ? 'not-allowed' : 'pointer';
        }
    }
    
    getTranscription() {
        if (!this.elements.transcriptionArea) return '';
        
        // Don't return placeholder content
        if (this.elements.transcriptionArea.querySelector('.text-gray-500')) {
            return '';
        }
        
        return this.elements.transcriptionArea.textContent;
    }
    
    clearTranscription() {
        if (this.elements.transcriptionArea) {
            this.elements.transcriptionArea.textContent = '';
        }
        
        // Disable edit button when cleared
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            editBtn.disabled = true;
            editBtn.style.opacity = '0.5';
            editBtn.style.cursor = 'not-allowed';
        }
    }
    
    showError(message, type = 'error') {
        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = `alert alert-${type} alert-dismissible fade show`;
        errorDiv.innerHTML = `
            <strong>${type === 'error' ? 'Error:' : 'Warning:'}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to page
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(errorDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
        
        console.error(`UI Error: ${message}`);
    }
    
    showSuccess(message) {
        this.showError(message, 'success');
    }
    
    updateAudioVisualizer(audioLevel) {
        if (!this.elements.audioVisualizer) return;
        
        // Create bars if they don't exist
        if (!this.visualizerBars || this.visualizerBars.length === 0) {
            this.createVisualizerBars();
        }
        
        // Update bars based on audio level
        const normalizedLevel = Math.min(1, Math.max(0, audioLevel));
        const activeBarCount = Math.floor(normalizedLevel * this.visualizerBars.length);
        
        this.visualizerBars.forEach((bar, index) => {
            if (index < activeBarCount) {
                bar.classList.add('active');
                bar.style.height = `${20 + (normalizedLevel * 60)}%`;
            } else {
                bar.classList.remove('active');
                bar.style.height = '20%';
            }
        });
    }
    
    createVisualizerBars() {
        if (!this.elements.audioVisualizer) return;
        
        this.elements.audioVisualizer.innerHTML = '';
        this.visualizerBars = [];
        
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'visualizer-bar';
            bar.style.height = '20%';
            this.elements.audioVisualizer.appendChild(bar);
            this.visualizerBars.push(bar);
        }
    }
    
    switchMode(mode) {
        // Update tab states
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const activeTab = this.elements[`${mode}Tab`];
        if (activeTab) {
            activeTab.classList.add('active');
        }
        
        // Show/hide panels
        document.querySelectorAll('.mode-panel').forEach(panel => {
            panel.style.display = 'none';
        });
        
        const activePanel = this.elements[`${mode}Panel`];
        if (activePanel) {
            activePanel.style.display = 'block';
        }
        
        // Notify mode change
        if (this.onModeChange) {
            this.onModeChange(mode);
        }
        
        console.log(`🔄 Switched to ${mode} mode`);
    }
    
    updateTrainingProgress(progress) {
        if (!this.elements.trainingProgress) return;
        
        const { completed, total, accuracy } = progress;
        const percentage = total > 0 ? (completed / total) * 100 : 0;
        
        this.elements.trainingProgress.innerHTML = `
            <div class="progress mb-2">
                <div class="progress-bar" style="width: ${percentage}%"></div>
            </div>
            <small class="text-muted">
                ${completed}/${total} terms completed (${accuracy.toFixed(1)}% accuracy)
            </small>
        `;
    }
    
    updateShortcutsList(shortcuts) {
        if (!this.elements.shortcutsList) return;
        
        this.elements.shortcutsList.innerHTML = '';
        
        shortcuts.forEach(shortcut => {
            const item = document.createElement('div');
            item.className = 'shortcut-item d-flex justify-content-between align-items-center p-2 border-bottom';
            item.innerHTML = `
                <div>
                    <strong>${shortcut.name}</strong>
                    <br>
                    <small class="text-muted">"${shortcut.trigger_phrase}"</small>
                </div>
                <div>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editShortcut('${shortcut.id}')">
                        Edit
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteShortcut('${shortcut.id}')">
                        Delete
                    </button>
                </div>
            `;
            this.elements.shortcutsList.appendChild(item);
        });
    }
    
    // Event callback setters
    setCallbacks(callbacks) {
        this.onToggleRecording = callbacks.onToggleRecording;
        this.onClearTranscription = callbacks.onClearTranscription;
        this.onCopyTranscription = callbacks.onCopyTranscription;
        this.onSaveReport = callbacks.onSaveReport;
        this.onLoadTemplate = callbacks.onLoadTemplate;
        this.onModeChange = callbacks.onModeChange;
        this.onEditTranscription = callbacks.onEditTranscription;
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIManager;
} else {
    window.UIManager = UIManager;
}