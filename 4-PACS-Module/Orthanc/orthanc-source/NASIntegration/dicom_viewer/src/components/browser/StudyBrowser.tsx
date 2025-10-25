/**
 * 🇿🇦 South African Medical Imaging System - Study Browser
 * 
 * Component for browsing and selecting DICOM studies
 * Optimized for SA medical workflows
 */


import React from 'react';
// If you have these types, import them. Otherwise, define minimal local types for safety.
// import { DicomStudy, LoadingState } from '../../types/dicom';
// import { useSALocalization } from '../../hooks/useSALocalization';

// Minimal fallback types if imports fail
interface DicomStudy {
  studyInstanceUID: string;
  studyDescription: string;
  studyDate: string;
  studyTime?: string;
  patientInfo: {
    patientID: string;
    patientName: string;
    patientAge?: string;
  patientSex?: "M" | "F" | "O";
    saIdNumber?: string;
  preferredLanguage?: "en" | "af" | "zu";
  };
  series: Array<{
    seriesInstanceUID: string;
    seriesNumber: number;
    seriesDescription: string;
    modality: string;
    numberOfImages: number;
    images: any[];
  }>;
  institution?: string;
  referringPhysician?: string;
  medicalAidScheme?: string;
  numberOfSeries: number;
}

interface LoadingState {
  isLoading: boolean;
  message?: string;
  error?: {
    message: string;
  };
}

// Simple fallback localization if hook is missing
const useSALocalization = () => {
  const t = (key: string) => {
    const dict: Record<string, string> = {
      'ui.studyBrowser': 'Study Browser',
      'ui.studies': 'studies',
      'ui.noStudies': 'No studies available',
      'ui.images': 'images',
      'ui.startReport': 'Start Report',
      'ui.retry': 'Retry',
      'status.error': 'Error',
    };
    return dict[key] || key;
  };
  return { t };
};

interface StudyBrowserProps {
  studies: DicomStudy[];
  selectedStudy: DicomStudy | null;
  onStudySelect: (study: DicomStudy) => void;
  onStartReport: (study: DicomStudy) => void;
  loadingState: LoadingState;
}

export const StudyBrowser: React.FC<StudyBrowserProps> = ({
  studies,
  selectedStudy,
  onStudySelect,
  onStartReport,
  loadingState
}) => {
  const { t } = useSALocalization();

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
    return (
      <div className="study-browser loading">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <div className="loading-message">{loadingState.message}</div>
        </div>
      </div>
    );
  }

  if (loadingState.error) {
    return (
      <div className="study-browser error">
        <div className="error-display">
          <div className="error-title">{t('status.error')}</div>
          <div className="error-message">{loadingState.error.message}</div>
          <div className="error-actions">
            <button className="btn btn-primary btn-small">
              {t('ui.retry')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="study-browser">
      <div className="study-browser-header">
        <h3>📁 {t('ui.studyBrowser')}</h3>
        <div className="study-count">
          {studies.length} {t('ui.studies')}
        </div>
      </div>

      <div className="study-list">
        {studies.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <div className="empty-message">{t('ui.noStudies')}</div>
          </div>
        ) : (
          studies.map((study) => (
            <div
              key={study.studyInstanceUID}
              className={`study-item ${
                selectedStudy?.studyInstanceUID === study.studyInstanceUID ? 'selected' : ''
              }`}
              onClick={() => onStudySelect(study)}
            >
              {/* Study Header */}
              <div className="study-header">
                <div className="study-date">
                  📅 {formatDate(study.studyDate)}
                  {study.studyTime && (
                    <span className="study-time">
                      {formatTime(study.studyTime)}
                    </span>
                  )}
                </div>
                <div className="medical-aid">
                  {getMedicalAidIcon(study.medicalAidScheme)}
                </div>
              </div>

              {/* Patient Info */}
              <div className="patient-info">
                <div className="patient-name">
                  👤 {study.patientInfo.patientName}
                </div>
                <div className="patient-details">
                  <span className="patient-id">ID: {study.patientInfo.patientID}</span>
                  {study.patientInfo.patientAge && (
                    <span className="patient-age">
                      {study.patientInfo.patientAge}
                    </span>
                  )}
                  {study.patientInfo.patientSex && (
                    <span className="patient-sex">
                      {study.patientInfo.patientSex}
                    </span>
                  )}
                </div>
                {study.patientInfo.saIdNumber && (
                  <div className="sa-id">
                    🇿🇦 {study.patientInfo.saIdNumber}
                  </div>
                )}
              </div>

              {/* Study Description */}
              <div className="study-description">
                {study.studyDescription}
              </div>

              {/* Series Info */}
              <div className="series-info">
                {study.series.map((series) => (
                  <div key={series.seriesInstanceUID} className="series-item">
                    <span className="modality-icon">
                      {getModalityIcon(series.modality)}
                    </span>
                    <span className="series-description">
                      {series.seriesDescription}
                    </span>
                    <span className="image-count">
                      ({series.numberOfImages} {t('ui.images')})
                    </span>
                  </div>
                ))}
              </div>

              {/* Institution Info */}
              {study.institution && (
                <div className="institution-info">
                  🏥 {study.institution}
                </div>
              )}

              {/* Referring Physician */}
              {study.referringPhysician && (
                <div className="referring-physician">
                  👨‍⚕️ {study.referringPhysician}
                </div>
              )}

              {/* Language Indicator */}
              {study.patientInfo.preferredLanguage && (
                <div className="language-indicator">
                  🗣️ {study.patientInfo.preferredLanguage.toUpperCase()}
                </div>
              )}

              {/* Start Report Button */}
              <div className="study-actions">
                <button 
                  className="btn btn-small btn-primary start-report-btn"
                  onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                    e.stopPropagation(); // Prevent study selection
                    onStartReport(study);
                  }}
                  title={t('ui.startReport')}
                >
                  📝 {t('ui.startReport')}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};