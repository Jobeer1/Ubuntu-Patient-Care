/**
 * 🇿🇦 South African Mconst ReportingIntegration: React.FC<ReportingIntegrationProps> = ({ 
  study,
  selectedSeries = [],
  measurements = [],
  onExportMeasurements,
  onClose
}) => { Imaging System - Reporting Integration
 * 
 * Component to handle communication between DICOM viewer and reporting system
 * Provides seamless integration for SA medical workflows
 */

import React, { useState, useEffect } from 'react';

// Local type definitions (replace with imports if available)
interface DicomSeries {
  seriesInstanceUID: string;
  seriesDescription?: string;
  modality: string;
  numberOfImages?: number;
}

interface DicomStudy {
  studyInstanceUID: string;
  studyDescription: string;
  studyDate: string;
  patientInfo: {
    patientID: string;
    patientName: string;
    preferredLanguage?: string;
  };
  series: DicomSeries[];
}

// Simple fallback localization
const useSALocalization = () => {
  const t = (key: string) => {
    const dict: Record<string, string> = {
      'loading.reportingSession': 'Initializing reporting session...',
      'error.sessionInit': 'Failed to initialize reporting session',
      'error.recordingFailed': 'Voice recording failed',
      'ui.retry': 'Retry',
      'ui.cancel': 'Cancel',
      'ui.close': 'Close',
      'ui.startReport': 'Start Report',
      'ui.stopRecording': 'Stop Recording',
      'ui.startRecording': 'Start Recording',
      'ui.exportMeasurements': 'Export Measurements',
      'ui.openFullReporting': 'Open Full Reporting',
      'ui.liveTranscript': 'Live Transcript',
      'ui.studySummary': 'Study Summary',
      'ui.patient': 'Patient',
      'ui.studyDate': 'Study Date',
      'ui.modalities': 'Modalities',
      'ui.measurements': 'Measurements',
      'status.initializing': 'Initializing',
      'status.recording': 'Recording',
      'status.processing': 'Processing',
      'status.ready': 'Ready'
    };
    return dict[key] || key;
  };
  return { t };
};

interface ReportingIntegrationProps {
  study: DicomStudy;
  selectedSeries?: DicomSeries[];
  measurements?: any[];
  onExportMeasurements?: () => any;
  onClose: () => void;
}

interface ReportingSession {
  sessionId: string;
  studyId: string;
  patientId: string;
  status: 'initializing' | 'recording' | 'processing' | 'ready';
  transcript?: string;
  measurements?: any[];
}

export const ReportingIntegration: React.FC<ReportingIntegrationProps> = ({
  study,
  selectedSeries = [],
  measurements = [],
  onExportMeasurements,
  onClose
}) => {
  const { t } = useSALocalization();
  const [session, setSession] = useState<ReportingSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  // Initialize reporting session
  useEffect(() => {
    initializeSession();
  }, [study]);

  const initializeSession = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Call reporting API to create session
      const sessionData = {
        patient_id: study.patientInfo.patientID,
        study_id: study.studyInstanceUID,
        image_ids: selectedSeries.map(s => s.seriesInstanceUID),
        language: study.patientInfo.preferredLanguage || 'en',
        measurements: measurements
      };

      // TODO: Replace with actual API call
      // const response = await fetch('/api/reporting/sessions', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(sessionData)
      // });

      // Mock response for now
      const mockSession: ReportingSession = {
        sessionId: `session_${Date.now()}`,
        studyId: study.studyInstanceUID,
        patientId: study.patientInfo.patientID,
        status: 'ready',
        measurements: measurements
      };

      setSession(mockSession);
      console.log('🏥 SA Reporting session initialized:', mockSession);
      
    } catch (err) {
      setError(t('error.sessionInit'));
      console.error('Failed to initialize reporting session:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startVoiceRecording = async () => {
    if (!session) return;

    setIsRecording(true);
    setSession({ ...session, status: 'recording' });

    try {
      // TODO: Integrate with voice recording API
      // const response = await fetch(`/api/reporting/sessions/${session.sessionId}/record`, {
      //   method: 'POST'
      // });

      console.log('🎤 Started voice recording for session:', session.sessionId);
      
      // Mock recording simulation
      setTimeout(() => {
        setIsRecording(false);
        setSession(prev => prev ? { 
          ...prev, 
          status: 'processing',
          transcript: 'Patient shows signs of... (mock transcript)' 
        } : null);
      }, 3000);
      
    } catch (err) {
      setError(t('error.recordingFailed'));
      setIsRecording(false);
    }
  };

  const stopVoiceRecording = () => {
    setIsRecording(false);
    if (session) {
      setSession({ ...session, status: 'processing' });
    }
  };

  const exportMeasurements = () => {
    if (!session) return;

    // Use the hook function if available, otherwise use internal export
    if (onExportMeasurements) {
      const hookData = onExportMeasurements();
      console.log('📊 Exporting measurements via hook:', hookData);
      
      // Send hook data to reporting API
      if (hookData) {
        sendMeasurementsToReporting(hookData);
      }
      return;
    }

    // Fallback to internal measurements export
    const exportData = {
      sessionId: session.sessionId,
      studyId: session.studyId,
      measurements: measurements,
      patientInfo: study.patientInfo,
      timestamp: new Date().toISOString()
    };

    console.log('📊 Exporting measurements to reporting system:', exportData);
    sendMeasurementsToReporting(exportData);
  };

  const sendMeasurementsToReporting = (data: any) => {
    
    // TODO: Send to reporting API
    // fetch(`/api/reporting/sessions/${session.sessionId}/measurements`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(exportData)
    // });
  };

  const openReportingInterface = () => {
    if (!session) return;

    // TODO: Open full reporting interface
    const reportingUrl = `/reporting?session=${session.sessionId}`;
    window.open(reportingUrl, '_blank', 'width=1200,height=800');
  };

  if (isLoading) {
    return (
      <div className="reporting-integration loading">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <div className="loading-message">{t('loading.reportingSession')}</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="reporting-integration error">
        <div className="error-content">
          <div className="error-icon">⚠️</div>
          <div className="error-message">{error}</div>
          <button className="btn btn-primary" onClick={initializeSession}>
            {t('ui.retry')}
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            {t('ui.cancel')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="reporting-integration">
      <div className="reporting-header">
        <div className="header-info">
          <h3>🏥 {t('ui.startReport')}</h3>
          <div className="patient-summary">
            <span className="patient-name">{study.patientInfo.patientName}</span>
            <span className="study-description">{study.studyDescription}</span>
          </div>
        </div>
        <button className="btn btn-icon" onClick={onClose} title={t('ui.close')}>
          ✕
        </button>
      </div>

      <div className="reporting-content">
        {/* Quick Actions */}
        <div className="quick-actions">
          <button 
            className={`btn btn-primary ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
            disabled={!session}
          >
            {isRecording ? (
              <>⏹️ {t('ui.stopRecording')}</>
            ) : (
              <>🎤 {t('ui.startRecording')}</>
            )}
          </button>

          <button 
            className="btn btn-secondary"
            onClick={exportMeasurements}
            disabled={measurements.length === 0}
          >
            📊 {t('ui.exportMeasurements')} ({measurements.length})
          </button>

          <button 
            className="btn btn-secondary"
            onClick={openReportingInterface}
            disabled={!session}
          >
            📝 {t('ui.openFullReporting')}
          </button>
        </div>

        {/* Session Status */}
        {session && (
          <div className="session-status">
            <div className="status-indicator">
              <span className={`status-dot ${session.status}`}></span>
              <span className="status-text">{t(`status.${session.status}`)}</span>
            </div>
            <div className="session-id">
              Session: {session.sessionId}
            </div>
          </div>
        )}

        {/* Live Transcript */}
        {session?.transcript && (
          <div className="live-transcript">
            <h4>{t('ui.liveTranscript')}</h4>
            <div className="transcript-content">
              {session.transcript}
            </div>
          </div>
        )}

        {/* Study Summary */}
        <div className="study-summary">
          <h4>{t('ui.studySummary')}</h4>
          <div className="summary-grid">
            <div className="summary-item">
              <span className="label">{t('ui.patient')}:</span>
              <span className="value">{study.patientInfo.patientName}</span>
            </div>
            <div className="summary-item">
              <span className="label">{t('ui.studyDate')}:</span>
              <span className="value">{study.studyDate}</span>
            </div>
            <div className="summary-item">
              <span className="label">{t('ui.modalities')}:</span>
              <span className="value">
                {study.series.map((s: DicomSeries) => s.modality).join(', ')}
              </span>
            </div>
            <div className="summary-item">
              <span className="label">{t('ui.measurements')}:</span>
              <span className="value">{measurements.length} items</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
