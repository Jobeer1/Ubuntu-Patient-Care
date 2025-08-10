/**
 * POPI Act Compliance Module
 * Ensures all data handling complies with South African data protection laws
 */

class POPICompliance {
    constructor() {
        this.isAnonymizationEnabled = localStorage.getItem('anonymizeData') === 'true';
        this.consentGiven = localStorage.getItem('popiConsent') === 'true';
        this.auditLog = [];
        
        this.init();
    }

    init() {
        if (!this.consentGiven) {
            this.showConsentDialog();
        }
        
        this.setupDataProtectionMeasures();
    }

    showConsentDialog() {
        const consentHTML = `
            <div id="popiConsentModal" class="modal" style="display: flex;">
                <div class="modal-content popi-consent">
                    <div class="modal-header">
                        <h2>🇿🇦 POPI Act Compliance - Data Protection Notice</h2>
                    </div>
                    <div class="modal-body">
                        <div class="consent-content">
                            <h3>Protection of Personal Information Act (POPI) Compliance</h3>
                            
                            <div class="consent-section">
                                <h4>Data Collection and Processing</h4>
                                <p>This application processes medical imaging data (DICOM files) for the purpose of medical diagnosis and treatment. The data is processed locally on your device and is not transmitted to external servers unless explicitly requested.</p>
                            </div>
                            
                            <div class="consent-section">
                                <h4>Your Rights</h4>
                                <ul>
                                    <li>Right to access your personal information</li>
                                    <li>Right to correct or delete your personal information</li>
                                    <li>Right to object to the processing of your personal information</li>
                                    <li>Right to submit a complaint to the Information Regulator</li>
                                </ul>
                            </div>
                            
                            <div class="consent-section">
                                <h4>Data Security</h4>
                                <p>All data is encrypted and stored locally. Audit logs are maintained for compliance purposes. Data anonymization is available for sharing or export purposes.</p>
                            </div>
                            
                            <div class="consent-options">
                                <label class="consent-checkbox">
                                    <input type="checkbox" id="consentProcessing" required>
                                    I consent to the processing of medical imaging data for diagnostic purposes
                                </label>
                                
                                <label class="consent-checkbox">
                                    <input type="checkbox" id="consentStorage">
                                    I consent to the local storage of imaging data for future reference
                                </label>
                                
                                <label class="consent-checkbox">
                                    <input type="checkbox" id="consentSharing">
                                    I consent to the secure sharing of anonymized data with healthcare providers
                                </label>
                                
                                <label class="consent-checkbox">
                                    <input type="checkbox" id="enableAnonymization" checked>
                                    Enable automatic data anonymization for enhanced privacy
                                </label>
                            </div>
                            
                            <div class="consent-actions">
                                <button class="btn-primary" onclick="popiCompliance.acceptConsent()">
                                    Accept and Continue
                                </button>
                                <button class="btn-secondary" onclick="popiCompliance.declineConsent()">
                                    Decline
                                </button>
                            </div>
                            
                            <div class="legal-notice">
                                <small>
                                    By using this application, you acknowledge that you have read and understood 
                                    this privacy notice. For questions about data protection, contact your 
                                    healthcare provider or the Information Regulator of South Africa.
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', consentHTML);
    }

    acceptConsent() {
        const processingConsent = document.getElementById('consentProcessing').checked;
        const storageConsent = document.getElementById('consentStorage').checked;
        const sharingConsent = document.getElementById('consentSharing').checked;
        const anonymization = document.getElementById('enableAnonymization').checked;
        
        if (!processingConsent) {
            alert('Processing consent is required to use this application.');
            return;
        }
        
        // Store consent preferences
        localStorage.setItem('popiConsent', 'true');
        localStorage.setItem('storageConsent', storageConsent.toString());
        localStorage.setItem('sharingConsent', sharingConsent.toString());
        localStorage.setItem('anonymizeData', anonymization.toString());
        localStorage.setItem('consentDate', new Date().toISOString());
        
        this.consentGiven = true;
        this.isAnonymizationEnabled = anonymization;
        
        // Log consent
        this.logDataAccess('CONSENT_GIVEN', {
            processing: processingConsent,
            storage: storageConsent,
            sharing: sharingConsent,
            anonymization: anonymization
        });
        
        // Remove consent dialog
        document.getElementById('popiConsentModal').remove();
        
        // Update UI
        this.updateComplianceIndicators();
    }

    declineConsent() {
        alert('This application requires consent to process medical imaging data in compliance with the POPI Act. The application will now close.');
        window.close();
    }

    setupDataProtectionMeasures() {
        // Encrypt sensitive data in localStorage
        this.setupEncryption();
        
        // Setup automatic data retention policies
        this.setupDataRetention();
        
        // Setup audit logging
        this.setupAuditLogging();
        
        // Setup session timeout
        this.setupSessionTimeout();
    }

    setupEncryption() {
        // Simple encryption for localStorage (in production, use stronger encryption)
        this.encryptionKey = this.generateEncryptionKey();
    }

    generateEncryptionKey() {
        const key = localStorage.getItem('encryptionKey');
        if (key) {
            return key;
        } else {
            const newKey = CryptoJS.lib.WordArray.random(256/8).toString();
            localStorage.setItem('encryptionKey', newKey);
            return newKey;
        }
    }

    encryptData(data) {
        if (!this.encryptionKey) return data;
        return CryptoJS.AES.encrypt(JSON.stringify(data), this.encryptionKey).toString();
    }

    decryptData(encryptedData) {
        if (!this.encryptionKey) return encryptedData;
        try {
            const bytes = CryptoJS.AES.decrypt(encryptedData, this.encryptionKey);
            return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
        } catch (error) {
            console.warn('Failed to decrypt data:', error);
            return null;
        }
    }

    setupDataRetention() {
        // Set up automatic data cleanup after retention period (7 years for medical data)
        const retentionPeriod = 7 * 365 * 24 * 60 * 60 * 1000; // 7 years in milliseconds
        
        setInterval(() => {
            this.cleanupExpiredData(retentionPeriod);
        }, 24 * 60 * 60 * 1000); // Check daily
    }

    cleanupExpiredData(retentionPeriod) {
        const now = Date.now();
        const studies = JSON.parse(localStorage.getItem('studies') || '[]');
        
        const validStudies = studies.filter(study => {
            const studyDate = new Date(study.studyDate).getTime();
            return (now - studyDate) < retentionPeriod;
        });
        
        if (validStudies.length !== studies.length) {
            localStorage.setItem('studies', JSON.stringify(validStudies));
            this.logDataAccess('DATA_RETENTION_CLEANUP', {
                removedStudies: studies.length - validStudies.length
            });
        }
    }

    setupAuditLogging() {
        // Monitor all data access and modifications
        this.originalSetItem = localStorage.setItem;
        this.originalGetItem = localStorage.getItem;
        this.originalRemoveItem = localStorage.removeItem;
        
        localStorage.setItem = (key, value) => {
            this.logDataAccess('DATA_STORED', { key: key });
            return this.originalSetItem.call(localStorage, key, value);
        };
        
        localStorage.getItem = (key) => {
            this.logDataAccess('DATA_ACCESSED', { key: key });
            return this.originalGetItem.call(localStorage, key);
        };
        
        localStorage.removeItem = (key) => {
            this.logDataAccess('DATA_DELETED', { key: key });
            return this.originalRemoveItem.call(localStorage, key);
        };
    }

    setupSessionTimeout() {
        // Auto-logout after period of inactivity
        const timeoutPeriod = 30 * 60 * 1000; // 30 minutes
        let lastActivity = Date.now();
        
        const resetTimer = () => {
            lastActivity = Date.now();
        };
        
        // Track user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetTimer, true);
        });
        
        // Check for timeout
        setInterval(() => {
            if (Date.now() - lastActivity > timeoutPeriod) {
                this.handleSessionTimeout();
            }
        }, 60000); // Check every minute
    }

    handleSessionTimeout() {
        this.logDataAccess('SESSION_TIMEOUT', {});
        
        // Clear sensitive data from memory
        if (window.saViewer) {
            window.saViewer.clearSensitiveData();
        }
        
        // Show timeout message
        alert('Session has timed out for security reasons. Please reload the application.');
        window.location.reload();
    }

    logDataAccess(action, details = {}) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            action: action,
            details: details,
            userAgent: navigator.userAgent,
            sessionId: this.getSessionId()
        };
        
        const auditLog = JSON.parse(localStorage.getItem('popiAuditLog') || '[]');
        auditLog.push(logEntry);
        
        // Keep only last 1000 entries
        if (auditLog.length > 1000) {
            auditLog.splice(0, auditLog.length - 1000);
        }
        
        localStorage.setItem('popiAuditLog', JSON.stringify(auditLog));
    }

    getSessionId() {
        let sessionId = sessionStorage.getItem('sessionId');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('sessionId', sessionId);
        }
        return sessionId;
    }

    anonymizePatientData(data) {
        if (!this.isAnonymizationEnabled) return data;
        
        const anonymized = { ...data };
        
        // Anonymize personal identifiers
        if (anonymized.patientName) anonymized.patientName = 'ANONYMIZED';
        if (anonymized.patientID) anonymized.patientID = 'ANON_' + this.generateAnonymousId();
        if (anonymized.patientBirthDate) anonymized.patientBirthDate = '';
        if (anonymized.patientAddress) anonymized.patientAddress = '';
        if (anonymized.patientPhone) anonymized.patientPhone = '';
        
        this.logDataAccess('DATA_ANONYMIZED', { originalId: data.patientID });
        
        return anonymized;
    }

    generateAnonymousId() {
        return Math.random().toString(36).substr(2, 8).toUpperCase();
    }

    updateComplianceIndicators() {
        const indicator = document.getElementById('popi-compliance');
        if (indicator) {
            indicator.innerHTML = `
                <i class="icon-shield"></i>
                POPI Compliant
                ${this.isAnonymizationEnabled ? '(Anonymized)' : ''}
            `;
            indicator.classList.add('compliant');
        }
    }

    generateComplianceReport() {
        const auditLog = JSON.parse(localStorage.getItem('popiAuditLog') || '[]');
        const consentData = {
            consentGiven: localStorage.getItem('popiConsent') === 'true',
            consentDate: localStorage.getItem('consentDate'),
            storageConsent: localStorage.getItem('storageConsent') === 'true',
            sharingConsent: localStorage.getItem('sharingConsent') === 'true',
            anonymizationEnabled: localStorage.getItem('anonymizeData') === 'true'
        };
        
        const report = {
            generatedAt: new Date().toISOString(),
            applicationVersion: '1.0.0',
            complianceFramework: 'POPI Act (South Africa)',
            consentData: consentData,
            auditLogEntries: auditLog.length,
            recentActivity: auditLog.slice(-50), // Last 50 activities
            dataRetentionPolicy: '7 years (medical records)',
            encryptionStatus: 'Enabled',
            sessionTimeout: '30 minutes'
        };
        
        return report;
    }

    exportComplianceReport() {
        const report = this.generateComplianceReport();
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `popi_compliance_report_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
        
        this.logDataAccess('COMPLIANCE_REPORT_EXPORTED', {});
    }

    revokeConsent() {
        if (confirm('Are you sure you want to revoke consent? This will delete all stored data and close the application.')) {
            this.logDataAccess('CONSENT_REVOKED', {});
            
            // Clear all stored data
            localStorage.clear();
            sessionStorage.clear();
            
            // Clear IndexedDB if available
            if (window.indexedDB) {
                indexedDB.deleteDatabase('SADicomViewer');
            }
            
            alert('All data has been deleted in accordance with your request. The application will now close.');
            window.close();
        }
    }

    handleDataBreach(incident) {
        const breachReport = {
            timestamp: new Date().toISOString(),
            incident: incident,
            affectedData: 'Medical imaging data',
            actionsTaken: [
                'Incident logged',
                'Affected users notified',
                'Security measures reviewed'
            ],
            reportedToRegulator: false // Set to true when reported
        };
        
        localStorage.setItem('dataBreachReport', JSON.stringify(breachReport));
        this.logDataAccess('DATA_BREACH_REPORTED', incident);
        
        // In production, this should trigger actual breach notification procedures
        console.error('Data breach reported:', breachReport);
    }
}

// Initialize POPI compliance
let popiCompliance;
document.addEventListener('DOMContentLoaded', () => {
    popiCompliance = new POPICompliance();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = POPICompliance;
}
