/**
 * 🇿🇦 South African Medical Imaging System - Reporting Integration
 * 
 * Component to handle communication between DICOM viewer and reporting system
 * Provides seamless integration for SA medical workflows
 */

import React, { useState, useEffect } from 'react';

// Simplified interfaces to avoid external dependencies
interface DicomStudy {
  studyInstanceUID: string;
  studyDescription: string;
  studyDate: string;
  patientInfo: {
    patientID: string;
    patientName: string;
    preferredLanguage?: string;
  };
  series: Array<{
    seriesInstanceUID: string;
    modality: string;
  }>;
}

interface ReportingIntegrationProps {
  study: DicomStudy;
  selectedSeries?: any[];
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

// Simple localization helper
const useLocalization = () => {
  const t = (key: string): string => {
    const translations: Record<string, string> = {
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
    return translations[key] || key;
  };
  return { t };
};

export const ReportingIntegration: React.FC<ReportingIntegrationProps> = ({
  study,
  selectedSeries = [],
  measurements = [],
  onExportMeasurements,
  onClose
}) => {
  const { t } = useLocalization();
  const [session, setSession] = useState<ReportingSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  // Initialize reporting session
  useEffect(() => {
    initializeSession();
  }, [study]);

  const initializeSession = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // Call reporting API to create session
      const sessionData = {
        patient_id: study.patientInfo.patientID,
        study_id: study.studyInstanceUID,
        image_ids: selectedSeries.map((s: any) => s.seriesInstanceUID),
        language: study.patientInfo.preferredLanguage || 'en',
        measurements: measurements
      };

      // Mock response for now - replace with actual API call
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

  const startVoiceRecording = async (): Promise<void> => {
    if (!session) return;

    setIsRecording(true);
    setSession({ ...session, status: 'recording' });

    try {
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

  const stopVoiceRecording = (): void => {
    setIsRecording(false);
    if (session) {
      setSession({ ...session, status: 'processing' });
    }
  };

  const exportMeasurements = (): void => {
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

  const sendMeasurementsToReporting = (data: any): void => {
    // TODO: Send to reporting API
    console.log('Sending measurements to reporting system:', data);
  };

  const openReportingInterface = (): void => {
    if (!session) return;

    // TODO: Open full reporting interface
    const reportingUrl = `/reporting?session=${session.sessionId}`;
    window.open(reportingUrl, '_blank', 'width=1200,height=800');
  };

  if (isLoading) {
    return React.createElement('div', { className: 'reporting-integration loading' },
      React.createElement('div', { className: 'loading-content' },
        React.createElement('div', { className: 'loading-spinner' }),
        React.createElement('div', { className: 'loading-message' }, t('loading.reportingSession'))
      )
    );
  }

  if (error) {
    return React.createElement('div', { className: 'reporting-integration error' },
      React.createElement('div', { className: 'error-content' },
        React.createElement('div', { className: 'error-icon' }, '⚠️'),
        React.createElement('div', { className: 'error-message' }, error),
        React.createElement('button', { 
          className: 'btn btn-primary', 
          onClick: initializeSession 
        }, t('ui.retry')),
        React.createElement('button', { 
          className: 'btn btn-secondary', 
          onClick: onClose 
        }, t('ui.cancel'))
      )
    );
  }

  return React.createElement('div', { className: 'reporting-integration' },
    // Header
    React.createElement('div', { className: 'reporting-header' },
      React.createElement('div', { className: 'header-info' },
        React.createElement('h3', {}, `🏥 ${t('ui.startReport')}`),
        React.createElement('div', { className: 'patient-summary' },
          React.createElement('span', { className: 'patient-name' }, study.patientInfo.patientName),
          React.createElement('span', { className: 'study-description' }, study.studyDescription)
        )
      ),
      React.createElement('button', { 
        className: 'btn btn-icon', 
        onClick: onClose, 
        title: t('ui.close') 
      }, '✕')
    ),

    // Content
    React.createElement('div', { className: 'reporting-content' },
      // Quick Actions
      React.createElement('div', { className: 'quick-actions' },
        React.createElement('button', {
          className: `btn btn-primary ${isRecording ? 'recording' : ''}`,
          onClick: isRecording ? stopVoiceRecording : startVoiceRecording,
          disabled: !session
        }, isRecording ? `⏹️ ${t('ui.stopRecording')}` : `🎤 ${t('ui.startRecording')}`),
        
        React.createElement('button', {
          className: 'btn btn-secondary',
          onClick: exportMeasurements,
          disabled: measurements.length === 0
        }, `📊 ${t('ui.exportMeasurements')} (${measurements.length})`),
        
        React.createElement('button', {
          className: 'btn btn-secondary',
          onClick: openReportingInterface,
          disabled: !session
        }, `📝 ${t('ui.openFullReporting')}`)
      ),

      // Session Status
      session && React.createElement('div', { className: 'session-status' },
        React.createElement('div', { className: 'status-indicator' },
          React.createElement('span', { className: `status-dot ${session.status}` }),
          React.createElement('span', { className: 'status-text' }, t(`status.${session.status}`))
        ),
        React.createElement('div', { className: 'session-id' }, `Session: ${session.sessionId}`)
      ),

      // Live Transcript
      session?.transcript && React.createElement('div', { className: 'live-transcript' },
        React.createElement('h4', {}, t('ui.liveTranscript')),
        React.createElement('div', { className: 'transcript-content' }, session.transcript)
      ),

      // Study Summary
      React.createElement('div', { className: 'study-summary' },
        React.createElement('h4', {}, t('ui.studySummary')),
        React.createElement('div', { className: 'summary-grid' },
          React.createElement('div', { className: 'summary-item' },
            React.createElement('span', { className: 'label' }, `${t('ui.patient')}:`),
            React.createElement('span', { className: 'value' }, study.patientInfo.patientName)
          ),
          React.createElement('div', { className: 'summary-item' },
            React.createElement('span', { className: 'label' }, `${t('ui.studyDate')}:`),
            React.createElement('span', { className: 'value' }, study.studyDate)
          ),
          React.createElement('div', { className: 'summary-item' },
            React.createElement('span', { className: 'label' }, `${t('ui.modalities')}:`),
            React.createElement('span', { className: 'value' }, study.series.map(s => s.modality).join(', '))
          ),
          React.createElement('div', { className: 'summary-item' },
            React.createElement('span', { className: 'label' }, `${t('ui.measurements')}:`),
            React.createElement('span', { className: 'value' }, `${measurements.length} items`)
          )
        )
      )
    )
  );
};
