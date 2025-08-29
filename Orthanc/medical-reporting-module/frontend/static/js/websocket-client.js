/**
 * WebSocket Client for Real-time Features
 * Handles voice transcription, report collaboration, and sync status
 */

class MedicalReportingWebSocket {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.currentReportId = null;
        this.currentVoiceSession = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        
        // Event handlers
        this.eventHandlers = {
            'connection_confirmed': [],
            'transcription_update': [],
            'voice_session_complete': [],
            'report_updated': [],
            'sync_status_update': [],
            'system_message': [],
            'error': []
        };
        
        this.init();
    }
    
    init() {
        try {
            // Initialize Socket.IO connection
            this.socket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true
            });
            
            this.setupEventHandlers();
            this.setupReconnection();
            
        } catch (error) {
            console.error('WebSocket initialization failed:', error);
            this.showError('Failed to initialize real-time connection');
        }
    }
    
    setupEventHandlers() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to Medical Reporting WebSocket');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from WebSocket:', reason);
            this.isConnected = false;
            this.updateConnectionStatus(false);
            
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, try to reconnect
                this.attemptReconnect();
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        });
        
        // System events
        this.socket.on('connection_confirmed', (data) => {
            console.log('Connection confirmed:', data);
            this.triggerEvent('connection_confirmed', data);
            this.showSuccess('Real-time features connected');
        });
        
        this.socket.on('system_message', (data) => {
            console.log('System message:', data);
            this.triggerEvent('system_message', data);
            this.showSystemMessage(data.message, data.type);
        });
        
        this.socket.on('error', (data) => {
            console.error('WebSocket error:', data);
            this.triggerEvent('error', data);
            this.showError(data.message || 'WebSocket error occurred');
        });
        
        // Voice transcription events
        this.socket.on('voice_session_ready', (data) => {
            console.log('Voice session ready:', data);
            this.currentVoiceSession = data.voice_session_id;
            this.updateVoiceStatus('ready');
        });
        
        this.socket.on('transcription_update', (data) => {
            console.log('Transcription update:', data);
            this.triggerEvent('transcription_update', data);
            this.updateTranscriptionDisplay(data.text, data.is_final);
        });
        
        this.socket.on('voice_session_complete', (data) => {
            console.log('Voice session complete:', data);
            this.triggerEvent('voice_session_complete', data);
            this.currentVoiceSession = null;
            this.updateVoiceStatus('complete');
            this.finalizeTranscription(data.final_transcription);
        });
        
        // Report collaboration events
        this.socket.on('user_joined_report', (data) => {
            console.log('User joined report:', data);
            this.showInfo(`${data.user_id} joined the report`);
            this.updateCollaboratorsList();
        });
        
        this.socket.on('user_left_report', (data) => {
            console.log('User left report:', data);
            this.showInfo(`${data.user_id} left the report`);
            this.updateCollaboratorsList();
        });
        
        this.socket.on('report_updated', (data) => {
            console.log('Report updated:', data);
            this.triggerEvent('report_updated', data);
            this.handleReportUpdate(data);
        });
        
        this.socket.on('report_transcription_update', (data) => {
            console.log('Report transcription from other user:', data);
            this.showCollaboratorTranscription(data);
        });
        
        // Sync status events
        this.socket.on('sync_status_update', (data) => {
            console.log('Sync status update:', data);
            this.triggerEvent('sync_status_update', data);
            this.updateSyncStatus(data);
        });
    }
    
    setupReconnection() {
        this.socket.on('disconnect', () => {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.attemptReconnect();
                }, this.reconnectDelay);
            }
        });
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.showError('Failed to reconnect. Please refresh the page.');
            return;
        }
        
        this.reconnectAttempts++;
        this.reconnectDelay *= 2; // Exponential backoff
        
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
        this.showInfo(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        this.socket.connect();
    }
    
    // Public API methods
    joinReport(reportId) {
        if (!this.isConnected) {
            this.showError('Not connected to real-time service');
            return false;
        }
        
        this.currentReportId = reportId;
        this.socket.emit('join_report', { report_id: reportId });
        return true;
    }
    
    leaveReport() {
        if (this.currentReportId && this.isConnected) {
            this.socket.emit('leave_report', { report_id: this.currentReportId });
            this.currentReportId = null;
        }
    }
    
    startVoiceSession(reportId = null) {
        if (!this.isConnected) {
            this.showError('Not connected to real-time service');
            return false;
        }
        
        this.socket.emit('start_voice_session', { report_id: reportId || this.currentReportId });
        this.updateVoiceStatus('starting');
        return true;
    }
    
    sendAudioChunk(audioData, chunkIndex) {
        if (!this.currentVoiceSession || !this.isConnected) {
            console.warn('No active voice session or not connected');
            return false;
        }
        
        this.socket.emit('voice_audio_chunk', {
            voice_session_id: this.currentVoiceSession,
            audio_data: audioData,
            chunk_index: chunkIndex
        });
        
        return true;
    }
    
    endVoiceSession() {
        if (!this.currentVoiceSession || !this.isConnected) {
            return false;
        }
        
        this.socket.emit('end_voice_session', {
            voice_session_id: this.currentVoiceSession
        });
        
        this.updateVoiceStatus('ending');
        return true;
    }
    
    updateReport(reportId, updateType, data) {
        if (!this.isConnected) {
            return false;
        }
        
        this.socket.emit('report_update', {
            report_id: reportId || this.currentReportId,
            type: updateType,
            data: data
        });
        
        return true;
    }
    
    requestSyncStatus() {
        if (!this.isConnected) {
            return false;
        }
        
        this.socket.emit('sync_status_request');
        return true;
    }
    
    // Event handler registration
    on(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].push(handler);
        }
    }
    
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }
    
    triggerEvent(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    // UI update methods
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = connected ? 'status-connected' : 'status-disconnected';
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        }
        
        // Update real-time features availability
        const voiceButton = document.getElementById('voice-dictation-btn');
        if (voiceButton) {
            voiceButton.disabled = !connected;
        }
    }
    
    updateVoiceStatus(status) {
        const statusElement = document.getElementById('voice-status');
        if (statusElement) {
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusElement.className = `voice-status-${status}`;
        }
        
        // Update voice button state
        const voiceButton = document.getElementById('voice-dictation-btn');
        if (voiceButton) {
            switch (status) {
                case 'ready':
                    voiceButton.textContent = 'Start Dictation';
                    voiceButton.disabled = false;
                    break;
                case 'starting':
                    voiceButton.textContent = 'Starting...';
                    voiceButton.disabled = true;
                    break;
                case 'active':
                    voiceButton.textContent = 'Stop Dictation';
                    voiceButton.disabled = false;
                    break;
                case 'ending':
                    voiceButton.textContent = 'Stopping...';
                    voiceButton.disabled = true;
                    break;
                case 'complete':
                    voiceButton.textContent = 'Start Dictation';
                    voiceButton.disabled = false;
                    break;
            }
        }
    }
    
    updateTranscriptionDisplay(text, isFinal) {
        const transcriptionElement = document.getElementById('live-transcription');
        if (transcriptionElement) {
            if (isFinal) {
                // Add to final transcription
                const finalElement = document.getElementById('final-transcription');
                if (finalElement) {
                    finalElement.value += text + ' ';
                }
                transcriptionElement.textContent = '';
            } else {
                // Show as live transcription
                transcriptionElement.textContent = text;
            }
        }
    }
    
    finalizeTranscription(finalText) {
        const finalElement = document.getElementById('final-transcription');
        if (finalElement) {
            finalElement.value = finalText;
        }
        
        const liveElement = document.getElementById('live-transcription');
        if (liveElement) {
            liveElement.textContent = '';
        }
    }
    
    updateSyncStatus(status) {
        const syncElement = document.getElementById('sync-status');
        if (syncElement) {
            const statusText = status.online ? 'Online' : 'Offline';
            const pendingText = status.pending_uploads > 0 ? ` (${status.pending_uploads} pending)` : '';
            syncElement.textContent = statusText + pendingText;
            syncElement.className = status.online ? 'sync-online' : 'sync-offline';
        }
    }
    
    updateCollaboratorsList() {
        // Placeholder for updating collaborators list
        // Would integrate with actual UI component
    }
    
    handleReportUpdate(data) {
        // Handle different types of report updates
        switch (data.type) {
            case 'content':
                this.showInfo(`Report content updated by ${data.user_id}`);
                break;
            case 'status':
                this.showInfo(`Report status changed to ${data.data.status} by ${data.user_id}`);
                break;
            case 'template':
                this.showInfo(`Report template changed by ${data.user_id}`);
                break;
        }
    }
    
    showCollaboratorTranscription(data) {
        const collaboratorElement = document.getElementById('collaborator-activity');
        if (collaboratorElement) {
            const activity = document.createElement('div');
            activity.className = 'collaborator-transcription';
            activity.innerHTML = `
                <span class="user">${data.user_id}:</span>
                <span class="text">${data.text}</span>
                <span class="time">${new Date(data.timestamp).toLocaleTimeString()}</span>
            `;
            collaboratorElement.appendChild(activity);
            
            // Auto-scroll to bottom
            collaboratorElement.scrollTop = collaboratorElement.scrollHeight;
        }
    }
    
    // Notification methods
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showInfo(message) {
        this.showNotification(message, 'info');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSystemMessage(message, type) {
        this.showNotification(message, type);
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to notification container
        let container = document.getElementById('notifications');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications';
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // Cleanup
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}

// Global WebSocket instance
let medicalWebSocket = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    medicalWebSocket = new MedicalReportingWebSocket();
    
    // Make it globally available
    window.medicalWebSocket = medicalWebSocket;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MedicalReportingWebSocket;
}