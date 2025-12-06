/**
 * Voice Shortcuts Manager Module
 * Handles voice shortcuts creation, management, and matching
 */

class ShortcutsManager {
    constructor() {
        this.baseUrl = '/api/voice';
        this.shortcuts = [];
        this.userId = 'demo_user';
        this.isRecordingShortcut = false;
        this.currentShortcutData = null;
        
        // Event callbacks
        this.onShortcutMatched = null;
        this.onShortcutsUpdated = null;
        this.onError = null;
    }
    
    async loadUserShortcuts() {
        try {
            const response = await fetch(`${this.baseUrl}/shortcuts?user_id=${this.userId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load shortcuts: ${response.status}`);
            }
            
            const data = await response.json();
            this.shortcuts = data.shortcuts || [];
            
            console.log(`✅ Loaded ${this.shortcuts.length} voice shortcuts`);
            
            if (this.onShortcutsUpdated) {
                this.onShortcutsUpdated(this.shortcuts);
            }
            
            return { success: true, shortcuts: this.shortcuts };
            
        } catch (error) {
            console.error('Failed to load shortcuts:', error);
            
            // Fallback to demo shortcuts
            this.shortcuts = this.getDemoShortcuts();
            if (this.onShortcutsUpdated) {
                this.onShortcutsUpdated(this.shortcuts);
            }
            
            return { success: false, error: error.message };
        }
    }
    
    getDemoShortcuts() {
        return [
            {
                id: 'demo_1',
                name: 'Consultation Template',
                trigger_phrase: 'consultation note',
                template_id: 'consultation',
                user_id: this.userId,
                created_at: new Date().toISOString()
            },
            {
                id: 'demo_2',
                name: 'Discharge Summary',
                trigger_phrase: 'discharge summary',
                template_id: 'discharge',
                user_id: this.userId,
                created_at: new Date().toISOString()
            }
        ];
    }
    
    async createShortcut(name, triggerPhrase, templateId) {
        try {
            // Start recording for the shortcut
            this.isRecordingShortcut = true;
            this.currentShortcutData = {
                name,
                trigger_phrase: triggerPhrase,
                template_id: templateId
            };
            
            console.log(`🎤 Recording voice shortcut: "${name}"`);
            return { success: true, message: 'Start speaking the trigger phrase...' };
            
        } catch (error) {
            console.error('Failed to start shortcut creation:', error);
            return { success: false, error: error.message };
        }
    }
    
    async saveShortcutAudio(audioBlob) {
        if (!this.isRecordingShortcut || !this.currentShortcutData) {
            return { success: false, error: 'No shortcut recording in progress' };
        }
        
        try {
            const formData = new FormData();
            let ext = 'webm';
            if (audioBlob && audioBlob.type) {
                if (audioBlob.type.includes('wav')) ext = 'wav';
                else if (audioBlob.type.includes('mpeg') || audioBlob.type.includes('mp3')) ext = 'mp3';
                else if (audioBlob.type.includes('webm')) ext = 'webm';
            }
            formData.append('audio', audioBlob, `shortcut.${ext}`);
            formData.append('name', this.currentShortcutData.name);
            formData.append('trigger_phrase', this.currentShortcutData.trigger_phrase);
            formData.append('template_id', this.currentShortcutData.template_id);
            formData.append('user_id', this.userId);
            
            const response = await fetch(`${this.baseUrl}/shortcuts`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Failed to save shortcut: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Add to local shortcuts
            this.shortcuts.push(data.shortcut);
            
            console.log(`✅ Voice shortcut created: "${this.currentShortcutData.name}"`);
            
            // Reset recording state
            this.isRecordingShortcut = false;
            this.currentShortcutData = null;
            
            if (this.onShortcutsUpdated) {
                this.onShortcutsUpdated(this.shortcuts);
            }
            
            return { success: true, shortcut: data.shortcut };
            
        } catch (error) {
            console.error('Failed to save shortcut:', error);
            this.isRecordingShortcut = false;
            this.currentShortcutData = null;
            return { success: false, error: error.message };
        }
    }
    
    async matchVoiceCommand(audioBlob) {
        try {
            const formData = new FormData();
            let ext = 'webm';
            if (audioBlob && audioBlob.type) {
                if (audioBlob.type.includes('wav')) ext = 'wav';
                else if (audioBlob.type.includes('mpeg') || audioBlob.type.includes('mp3')) ext = 'mp3';
                else if (audioBlob.type.includes('webm')) ext = 'webm';
            }
            formData.append('audio', audioBlob, `command.${ext}`);
            formData.append('user_id', this.userId);
            
            const response = await fetch(`${this.baseUrl}/shortcuts/match`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                // Fallback to demo matching
                return this.matchDemoCommand(audioBlob);
            }
            
            const data = await response.json();
            
            if (data.match && data.match.matched) {
                console.log(`🎯 Voice shortcut matched: "${data.match.shortcut.name}" (${data.match.confidence})`);
                
                if (this.onShortcutMatched) {
                    this.onShortcutMatched(data.match.shortcut, data.match.confidence);
                }
                
                return { success: true, match: data.match };
            }
            
            return { success: true, match: { matched: false } };
            
        } catch (error) {
            console.error('Failed to match voice command:', error);
            return { success: false, error: error.message };
        }
    }
    
    async matchDemoCommand(audioBlob) {
        // Simple demo matching based on transcription
        try {
            // For demo, just return no match
            return {
                success: true,
                match: {
                    matched: false,
                    confidence: 0.0,
                    shortcut: null
                }
            };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async deleteShortcut(shortcutId) {
        try {
            const response = await fetch(`${this.baseUrl}/shortcuts/${shortcutId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to delete shortcut: ${response.status}`);
            }
            
            // Remove from local shortcuts
            this.shortcuts = this.shortcuts.filter(s => s.id !== shortcutId);
            
            console.log(`🗑️ Voice shortcut deleted: ${shortcutId}`);
            
            if (this.onShortcutsUpdated) {
                this.onShortcutsUpdated(this.shortcuts);
            }
            
            return { success: true };
            
        } catch (error) {
            console.error('Failed to delete shortcut:', error);
            return { success: false, error: error.message };
        }
    }
    
    async updateShortcut(shortcutId, updates) {
        try {
            const response = await fetch(`${this.baseUrl}/shortcuts/${shortcutId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ...updates,
                    user_id: this.userId
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update shortcut: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update local shortcuts
            const index = this.shortcuts.findIndex(s => s.id === shortcutId);
            if (index !== -1) {
                this.shortcuts[index] = { ...this.shortcuts[index], ...updates };
            }
            
            console.log(`✏️ Voice shortcut updated: ${shortcutId}`);
            
            if (this.onShortcutsUpdated) {
                this.onShortcutsUpdated(this.shortcuts);
            }
            
            return { success: true, shortcut: data.shortcut };
            
        } catch (error) {
            console.error('Failed to update shortcut:', error);
            return { success: false, error: error.message };
        }
    }
    
    getShortcutById(shortcutId) {
        return this.shortcuts.find(s => s.id === shortcutId);
    }
    
    getShortcutsByTemplate(templateId) {
        return this.shortcuts.filter(s => s.template_id === templateId);
    }
    
    // Check if currently recording a shortcut
    isRecording() {
        return this.isRecordingShortcut;
    }
    
    // Cancel shortcut recording
    cancelRecording() {
        this.isRecordingShortcut = false;
        this.currentShortcutData = null;
        console.log('🚫 Shortcut recording cancelled');
    }
    
    // Get available templates for shortcuts
    getAvailableTemplates() {
        return [
            {
                id: 'consultation',
                name: 'Consultation Note',
                description: 'Standard consultation template'
            },
            {
                id: 'discharge',
                name: 'Discharge Summary',
                description: 'Hospital discharge summary'
            },
            {
                id: 'referral',
                name: 'Referral Letter',
                description: 'Patient referral template'
            },
            {
                id: 'prescription',
                name: 'Prescription',
                description: 'Medication prescription template'
            }
        ];
    }
    
    // Event callback setters
    setCallbacks(callbacks) {
        this.onShortcutMatched = callbacks.onShortcutMatched;
        this.onShortcutsUpdated = callbacks.onShortcutsUpdated;
        this.onError = callbacks.onError;
    }
    
    // Set user ID
    setUserId(userId) {
        this.userId = userId;
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ShortcutsManager;
} else {
    window.ShortcutsManager = ShortcutsManager;
}