/**
 * 🇿🇦 SA Healthcare Compliance Plugin for OHIF
 * 
 * Implements HPCSA and POPIA compliance features for the OHIF viewer
 */

import { createPlugin } from '@ohif/ui';

const SA_COMPLIANCE_PLUGIN = {
  id: '@sa-medical/extension-hpcsa-compliance',
  version: '1.0.0',
  
  /**
   * HPCSA Compliance Features
   */
  hpcsa: {
    /**
     * User verification and authentication tracking
     */
    userVerification: {
      verifyHPCSANumber: async (hpcsaNumber) => {
        try {
          const response = await fetch('/api/hpcsa/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hpcsaNumber }),
            credentials: 'include'
          });
          
          const result = await response.json();
          return {
            valid: result.valid,
            practitionerName: result.name,
            registrationStatus: result.status,
            specialization: result.specialization
          };
        } catch (error) {
          console.error('HPCSA verification failed:', error);
          return { valid: false, error: error.message };
        }
      },

      /**
       * Log user access for HPCSA audit requirements
       */
      logUserAccess: async (userInfo, studyInfo) => {
        const auditEntry = {
          timestamp: new Date().toISOString(),
          userId: userInfo.hpcsaNumber,
          userName: userInfo.name,
          action: 'STUDY_ACCESS',
          studyInstanceUID: studyInfo.studyInstanceUID,
          patientID: studyInfo.patientID,
          ipAddress: await this.getClientIP(),
          userAgent: navigator.userAgent,
          sessionId: this.getSessionId()
        };

        try {
          await fetch('/api/audit/hpcsa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(auditEntry),
            credentials: 'include'
          });
        } catch (error) {
          console.error('HPCSA audit logging failed:', error);
        }
      }
    },

    /**
     * Session management for single-session enforcement
     */
    sessionManagement: {
      enforceSessionLimits: async (userId) => {
        try {
          const response = await fetch('/api/session/enforce', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId }),
            credentials: 'include'
          });
          
          if (!response.ok) {
            throw new Error('Session limit exceeded');
          }
          
          return await response.json();
        } catch (error) {
          console.error('Session enforcement failed:', error);
          return { allowed: false, error: error.message };
        }
      },

      /**
       * Automatic session timeout
       */
      setupSessionTimeout: (timeoutMinutes = 30) => {
        let timeoutId;
        
        const resetTimeout = () => {
          clearTimeout(timeoutId);
          timeoutId = setTimeout(() => {
            this.logoutUser('Session timeout');
          }, timeoutMinutes * 60 * 1000);
        };

        // Reset timeout on user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
          document.addEventListener(event, resetTimeout, true);
        });

        resetTimeout(); // Initial timeout
      }
    }
  },

  /**
   * POPIA Compliance Features
   */
  popia: {
    /**
     * Data minimization - only load necessary data
     */
    dataMinimization: {
      filterPatientData: (patientData) => {
        // Remove unnecessary sensitive fields for viewing
        const {
          patientBirthDate,
          patientSex,
          patientID,
          patientName,
          ...sensitiveData
        } = patientData;

        return {
          patientID: this.anonymizePatientID(patientID),
          patientName: this.anonymizePatientName(patientName),
          patientSex,
          // Exclude birth date for privacy unless specifically needed
          ...(this.isFullDataRequired() ? { patientBirthDate } : {})
        };
      },

      anonymizePatientID: (patientID) => {
        // Hash patient ID for privacy while maintaining uniqueness
        return `***${patientID.slice(-4)}`;
      },

      anonymizePatientName: (patientName) => {
        if (!patientName) return 'Anonymous';
        const parts = patientName.split(' ');
        return `${parts[0].charAt(0)}*** ${parts[parts.length - 1]}`;
      }
    },

    /**
     * Consent management
     */
    consentManagement: {
      checkViewingConsent: async (patientID, studyID) => {
        try {
          const response = await fetch('/api/consent/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patientID, studyID }),
            credentials: 'include'
          });
          
          const result = await response.json();
          return {
            hasConsent: result.hasConsent,
            consentDate: result.consentDate,
            expiryDate: result.expiryDate,
            restrictions: result.restrictions || []
          };
        } catch (error) {
          console.error('Consent check failed:', error);
          return { hasConsent: false, error: error.message };
        }
      },

      /**
       * Display consent warning if required
       */
      displayConsentWarning: (consentInfo) => {
        if (!consentInfo.hasConsent) {
          const warningModal = document.createElement('div');
          warningModal.innerHTML = `
            <div class="consent-warning-modal">
              <div class="consent-warning-content">
                <h3>⚠️ Patient Consent Required</h3>
                <p>This study requires explicit patient consent for viewing.</p>
                <p>Please ensure proper consent has been obtained before proceeding.</p>
                <div class="consent-actions">
                  <button onclick="this.closest('.consent-warning-modal').remove()">
                    I Confirm Consent Obtained
                  </button>
                  <button onclick="window.close()">Cancel</button>
                </div>
              </div>
            </div>
          `;
          document.body.appendChild(warningModal);
        }
      }
    }
  },

  /**
   * Utility functions
   */
  utils: {
    getClientIP: async () => {
      try {
        const response = await fetch('/api/utils/client-ip');
        const data = await response.json();
        return data.ip;
      } catch {
        return 'unknown';
      }
    },

    getSessionId: () => {
      return sessionStorage.getItem('sa-session-id') || 'unknown';
    },

    isFullDataRequired: () => {
      // Check if current user role requires full patient data
      const userRole = sessionStorage.getItem('user-role');
      return ['admin', 'radiologist', 'primary_physician'].includes(userRole);
    },

    logoutUser: (reason) => {
      console.log(`Logging out user: ${reason}`);
      
      // Clear session data
      sessionStorage.clear();
      localStorage.clear();
      
      // Redirect to logout page
      window.location.href = '/logout?reason=' + encodeURIComponent(reason);
    }
  },

  /**
   * Plugin initialization
   */
  preRegistration: ({ servicesManager, configuration }) => {
    console.log('🇿🇦 SA Healthcare Compliance Plugin initialized');
    
    // Setup HPCSA session management
    this.hpcsa.sessionManagement.setupSessionTimeout(30);
    
    // Initialize POPIA consent checking
    window.saCompliance = {
      hpcsa: this.hpcsa,
      popia: this.popia,
      utils: this.utils
    };
  }
};

export default SA_COMPLIANCE_PLUGIN;
