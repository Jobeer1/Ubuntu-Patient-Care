/**
 * 🇿🇦 South African Medical Imaging System - DICOM Viewer Layout
 * 
 * Main layout component with header, sidebar controls, and responsive design
 */

import React from 'react';
import { useSALocalization } from '../../hooks/useSALocalization';

interface DicomViewerLayoutProps {
  children: React.ReactNode;
  sidebarOpen: boolean;
  toolPanelOpen: boolean;
  onToggleSidebar: () => void;
  onToggleToolPanel: () => void;
  currentLanguage: string;
  onLanguageChange: (language: 'en' | 'af' | 'zu') => void;
}

export const DicomViewerLayout: React.FC<DicomViewerLayoutProps> = ({
  children,
  sidebarOpen,
  toolPanelOpen,
  onToggleSidebar,
  onToggleToolPanel,
  currentLanguage,
  onLanguageChange,
}) => {
  const { t } = useSALocalization();

  const handleLayoutChange = (rows: number, columns: number) => {
    // This will be passed down to viewport grid
    console.log(`Layout changed to ${rows}x${columns}`);
  };

  return (
    <div className="dicom-viewer-layout">
      {/* Header */}
      <div className="viewer-header">
        <div className="header-left">
          {/* Logo */}
          <div className="logo">
            <span className="logo-icon">🏥</span>
            <span>🇿🇦 SA DICOM Viewer</span>
          </div>

          {/* Sidebar toggle */}
          <button
            className={`btn btn-icon ${sidebarOpen ? 'active' : ''}`}
            onClick={onToggleSidebar}
            title={t('ui.toggleStudyBrowser')}
          >
            📁
          </button>
        </div>

        <div className="header-center">
          {/* Layout controls */}
          <div className="layout-controls">
            <button
              className="layout-btn active"
              onClick={() => handleLayoutChange(1, 1)}
              title={t('layout.single')}
            >
              ⬜
            </button>
            <button
              className="layout-btn"
              onClick={() => handleLayoutChange(1, 2)}
              title={t('layout.sideBySide')}
            >
              ⬜⬜
            </button>
            <button
              className="layout-btn"
              onClick={() => handleLayoutChange(2, 2)}
              title={t('layout.grid2x2')}
            >
              ⬜⬜<br/>⬜⬜
            </button>
          </div>

          {/* Window presets */}
          <select className="select" title={t('ui.windowPresets')}>
            <option value="chest">{t('presets.chest')}</option>
            <option value="bone">{t('presets.bone')}</option>
            <option value="softTissue">{t('presets.softTissue')}</option>
            <option value="lung">{t('presets.lung')}</option>
            <option value="brain">{t('presets.brain')}</option>
            <option value="abdomen">{t('presets.abdomen')}</option>
          </select>
        </div>

        <div className="header-right">
          {/* Language selector */}
          <div className="language-selector">
            <span className="flag-icon">🇿🇦</span>
            <select
              className="select"
              value={currentLanguage}
              onChange={(e) => onLanguageChange(e.target.value as 'en' | 'af' | 'zu')}
            >
              <option value="en">English</option>
              <option value="af">Afrikaans</option>
              <option value="zu">isiZulu</option>
            </select>
          </div>

          {/* Tool panel toggle */}
          <button
            className={`btn btn-icon ${toolPanelOpen ? 'active' : ''}`}
            onClick={onToggleToolPanel}
            title={t('ui.toggleToolPanel')}
          >
            🔧
          </button>

          {/* Settings */}
          <button
            className="btn btn-icon"
            title={t('ui.settings')}
          >
            ⚙️
          </button>

          {/* Help */}
          <button
            className="btn btn-icon"
            title={t('ui.help')}
          >
            ❓
          </button>
        </div>
      </div>

      {/* Main content area */}
      <div className="dicom-viewer-layout">
        {children}
      </div>
    </div>
  );
};