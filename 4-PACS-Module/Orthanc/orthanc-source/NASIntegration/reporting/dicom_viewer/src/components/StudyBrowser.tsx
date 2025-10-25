/**
 * 🇿🇦 South African Medical Imaging System - Study Browser (Phase 1 Integration)
 * 
 * Component for browsing and selecting DICOM studies
 * Enhanced with "Start Report" button for reporting integration
 */

import React from 'react';

// Simplified interfaces to avoid external dependencies
interface DicomStudy {
  studyInstanceUID: string;
  studyDescription: string;
  studyDate: string;
  studyTime?: string;
  patientInfo: {
    patientID: string;
    patientName: string;
    patientAge?: string;
    patientSex?: string;
    saIdNumber?: string;
    preferredLanguage?: string;
  };
  series: Array<{
    seriesInstanceUID: string;
    seriesDescription: string;
    modality: string;
    numberOfImages: number;
  }>;
  institution?: string;
  referringPhysician?: string;
  medicalAidScheme?: string;
}

interface LoadingState {
  isLoading: boolean;
  message?: string;
  error?: {
    message: string;
  };
}

interface StudyBrowserProps {
  studies: DicomStudy[];
  selectedStudy: DicomStudy | null;
  onStudySelect: (study: DicomStudy) => void;
  onStartReport: (study: DicomStudy) => void;
  loadingState: LoadingState;
}

// Simple localization helper
const useLocalization = () => {
  const t = (key: string): string => {
    const translations: Record<string, string> = {
      'ui.studyBrowser': 'Study Browser',
      'ui.studies': 'studies',
      'ui.noStudies': 'No studies available',
      'ui.images': 'images',
      'ui.startReport': 'Start Report',
      'ui.retry': 'Retry',
      'status.error': 'Error'
    };
    return translations[key] || key;
  };
  return { t };
};

export const StudyBrowser: React.FC<StudyBrowserProps> = ({
  studies,
  selectedStudy,
  onStudySelect,
  onStartReport,
  loadingState
}) => {
  const { t } = useLocalization();

  const formatDate = (dateString: string): string => {
    try {
      // DICOM date format: YYYYMMDD
      const year = dateString.substring(0, 4);
      const month = dateString.substring(4, 6);
      const day = dateString.substring(6, 8);
      return `${day}/${month}/${year}`;
    } catch {
      return dateString;
    }
  };

  const formatTime = (timeString?: string): string => {
    if (!timeString) return '';
    try {
      // DICOM time format: HHMMSS
      const hour = timeString.substring(0, 2);
      const minute = timeString.substring(2, 4);
      return `${hour}:${minute}`;
    } catch {
      return timeString;
    }
  };

  const getMedicalAidIcon = (scheme?: string): string => {
    if (!scheme) return '🏥';
    
    const lowerScheme = scheme.toLowerCase();
    if (lowerScheme.includes('discovery')) return '🔍';
    if (lowerScheme.includes('momentum')) return '⚡';
    if (lowerScheme.includes('bonitas')) return '💎';
    if (lowerScheme.includes('medihelp')) return '🩺';
    if (lowerScheme.includes('fedhealth')) return '🤝';
    return '🏥';
  };

  const getModalityIcon = (modality: string): string => {
    switch (modality.toUpperCase()) {
      case 'CR':
      case 'DX':
        return '📷';
      case 'CT':
        return '🔄';
      case 'MR':
        return '🧲';
      case 'US':
        return '📡';
      case 'NM':
        return '☢️';
      case 'PT':
        return '🔬';
      case 'MG':
        return '🎯';
      default:
        return '🏥';
    }
  };

  if (loadingState.isLoading) {
    return React.createElement('div', { className: 'study-browser loading' },
      React.createElement('div', { className: 'loading-content' },
        React.createElement('div', { className: 'loading-spinner' }),
        React.createElement('div', { className: 'loading-message' }, loadingState.message)
      )
    );
  }

  if (loadingState.error) {
    return React.createElement('div', { className: 'study-browser error' },
      React.createElement('div', { className: 'error-display' },
        React.createElement('div', { className: 'error-title' }, t('status.error')),
        React.createElement('div', { className: 'error-message' }, loadingState.error.message),
        React.createElement('div', { className: 'error-actions' },
          React.createElement('button', { className: 'btn btn-primary btn-small' }, t('ui.retry'))
        )
      )
    );
  }

  return React.createElement('div', { className: 'study-browser' },
    // Header
    React.createElement('div', { className: 'study-browser-header' },
      React.createElement('h3', {}, `📁 ${t('ui.studyBrowser')}`),
      React.createElement('div', { className: 'study-count' },
        `${studies.length} ${t('ui.studies')}`
      )
    ),

    // Study List
    React.createElement('div', { className: 'study-list' },
      studies.length === 0 
        ? React.createElement('div', { className: 'empty-state' },
            React.createElement('div', { className: 'empty-icon' }, '📂'),
            React.createElement('div', { className: 'empty-message' }, t('ui.noStudies'))
          )
        : studies.map((study) => 
            React.createElement('div', {
              key: study.studyInstanceUID,
              className: `study-item ${
                selectedStudy?.studyInstanceUID === study.studyInstanceUID ? 'selected' : ''
              }`,
              onClick: () => onStudySelect(study)
            },
              // Study Header
              React.createElement('div', { className: 'study-header' },
                React.createElement('div', { className: 'study-date' },
                  `📅 ${formatDate(study.studyDate)}`,
                  study.studyTime && React.createElement('span', { className: 'study-time' },
                    formatTime(study.studyTime)
                  )
                ),
                React.createElement('div', { className: 'medical-aid' },
                  getMedicalAidIcon(study.medicalAidScheme)
                )
              ),

              // Patient Info
              React.createElement('div', { className: 'patient-info' },
                React.createElement('div', { className: 'patient-name' },
                  `👤 ${study.patientInfo.patientName}`
                ),
                React.createElement('div', { className: 'patient-details' },
                  React.createElement('span', { className: 'patient-id' }, `ID: ${study.patientInfo.patientID}`),
                  study.patientInfo.patientAge && React.createElement('span', { className: 'patient-age' },
                    study.patientInfo.patientAge
                  ),
                  study.patientInfo.patientSex && React.createElement('span', { className: 'patient-sex' },
                    study.patientInfo.patientSex
                  )
                ),
                study.patientInfo.saIdNumber && React.createElement('div', { className: 'sa-id' },
                  `🇿🇦 ${study.patientInfo.saIdNumber}`
                )
              ),

              // Study Description
              React.createElement('div', { className: 'study-description' },
                study.studyDescription
              ),

              // Series Info
              React.createElement('div', { className: 'series-info' },
                study.series.map((series) =>
                  React.createElement('div', { 
                    key: series.seriesInstanceUID, 
                    className: 'series-item' 
                  },
                    React.createElement('span', { className: 'modality-icon' },
                      getModalityIcon(series.modality)
                    ),
                    React.createElement('span', { className: 'series-description' },
                      series.seriesDescription
                    ),
                    React.createElement('span', { className: 'image-count' },
                      `(${series.numberOfImages} ${t('ui.images')})`
                    )
                  )
                )
              ),

              // Institution Info
              study.institution && React.createElement('div', { className: 'institution-info' },
                `🏥 ${study.institution}`
              ),

              // Referring Physician
              study.referringPhysician && React.createElement('div', { className: 'referring-physician' },
                `👨‍⚕️ ${study.referringPhysician}`
              ),

              // Language Indicator
              study.patientInfo.preferredLanguage && React.createElement('div', { className: 'language-indicator' },
                `🗣️ ${study.patientInfo.preferredLanguage.toUpperCase()}`
              ),

              // Start Report Button - THE KEY PHASE 1 ENHANCEMENT
              React.createElement('div', { className: 'study-actions' },
                React.createElement('button', {
                  className: 'btn btn-small btn-primary start-report-btn',
                  onClick: (e: React.MouseEvent) => {
                    e.stopPropagation(); // Prevent study selection
                    onStartReport(study);
                  },
                  title: t('ui.startReport')
                }, `📝 ${t('ui.startReport')}`)
              )
            )
          )
    )
  );
};
