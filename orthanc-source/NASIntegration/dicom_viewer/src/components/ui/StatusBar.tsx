/**
 * 🇿🇦 South African Medical Imaging System - Status Bar
 * 
 * Bottom status bar showing system information and current state
 */

import React from 'react';
import { DicomStudy, LoadingState, LayoutConfig } from '../../types/dicom';
import { useSALocalization } from '../../hooks/useSALocalization';

interface StatusBarProps {
  loadingState: LoadingState;
  selectedStudy: DicomStudy | null;
  layoutConfig: LayoutConfig;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  loadingState,
  selectedStudy,
  layoutConfig
}) => {
  const { t } = useSALocalization();

  const getConnectionStatus = () => {
    // In a real implementation, this would check actual connection status
    return { status: 'connected', message: t('status.connected') };
  };

  const formatMemoryUsage = () => {
    // In a real implementation, this would show actual memory usage
    return '256 MB';
  };

  const getCurrentTime = () => {
    return new Date().toLocaleTimeString('en-ZA', {
      timeZone: 'Africa/Johannesburg',
      hour12: false
    });
  };

  const connection = getConnectionStatus();

  return (
    <div className="status-bar">
      <div className="status-left">
        {/* Connection Status */}
        <div className="status-item">
          <div className={`status-indicator ${connection.status}`}></div>
          <span>{connection.message}</span>
        </div>

        {/* Loading State */}
        {loadingState.isLoading && (
          <div className="status-item">
            <div className="spinner"></div>
            <span>{loadingState.message}</span>
            {loadingState.progress && (
              <span>({Math.round(loadingState.progress)}%)</span>
            )}
          </div>
        )}

        {/* Error State */}
        {loadingState.error && (
          <div className="status-item error">
            <span>❌ {loadingState.error.message}</span>
          </div>
        )}

        {/* Selected Study Info */}
        {selectedStudy && (
          <div className="status-item">
            <span>
              📁 {selectedStudy.patientInfo.patientName} - {selectedStudy.studyDescription}
            </span>
          </div>
        )}
      </div>

      <div className="status-right">
        {/* Layout Info */}
        <div className="status-item">
          <span>
            📐 {layoutConfig.rows}×{layoutConfig.columns}
          </span>
        </div>

        {/* Memory Usage */}
        <div className="status-item">
          <span>💾 {formatMemoryUsage()}</span>
        </div>

        {/* SA Time */}
        <div className="status-item">
          <span>🇿🇦 {getCurrentTime()} SAST</span>
        </div>

        {/* System Status */}
        <div className="status-item">
          <span>🏥 SA Medical Imaging v1.0</span>
        </div>
      </div>
    </div>
  );
};