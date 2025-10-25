/**
 * 🇿🇦 South African Medical Imaging System - Tool Panel
 * 
 * Panel containing measurement tools, annotations, and SA-specific features
 */

import React, { useState } from 'react';
import { DicomStudy, Measurement, Annotation } from '../../types/dicom';
import { useSALocalization } from '../../hooks/useSALocalization';
import { cornerstoneTools } from '../../core/cornerstone-init';

interface ToolPanelProps {
  selectedStudy: DicomStudy | null;
  onMeasurement: (measurement: Measurement) => void;
  onAnnotation: (annotation: Annotation) => void;
}

export const ToolPanel: React.FC<ToolPanelProps> = ({
  selectedStudy,
  onMeasurement,
  onAnnotation
}) => {
  const { t } = useSALocalization();
  const [activeTab, setActiveTab] = useState<'tools' | 'measurements' | 'ai' | 'voice'>('tools');
  const [activeTool, setActiveTool] = useState<string>('Pan');

  const tools = [
    { name: 'Pan', icon: '✋', key: 'tools.pan' },
    { name: 'Zoom', icon: '🔍', key: 'tools.zoom' },
    { name: 'Wwwc', icon: '🎚️', key: 'tools.windowLevel' },
    { name: 'Length', icon: '📏', key: 'tools.measure' },
    { name: 'Angle', icon: '📐', key: 'measurement.angle' },
    { name: 'RectangleRoi', icon: '⬜', key: 'measurement.area' },
    { name: 'ArrowAnnotate', icon: '➡️', key: 'tools.annotate' },
    { name: 'TextMarker', icon: '📝', key: 'tools.annotate' },
  ];

  const handleToolSelect = (toolName: string) => {
    try {
      // Deactivate all tools first
      tools.forEach(tool => {
        cornerstoneTools.setToolPassive(tool.name);
      });

      // Activate selected tool
      if (toolName === 'Pan') {
        cornerstoneTools.setToolActive(toolName, { mouseButtonMask: 1 });
      } else if (toolName === 'Zoom') {
        cornerstoneTools.setToolActive(toolName, { mouseButtonMask: 2 });
      } else if (toolName === 'Wwwc') {
        cornerstoneTools.setToolActive(toolName, { mouseButtonMask: 1 });
      } else {
        cornerstoneTools.setToolActive(toolName, { mouseButtonMask: 1 });
      }

      setActiveTool(toolName);
    } catch (error) {
      console.error('Failed to activate tool:', error);
    }
  };

  const renderToolsTab = () => (
    <div className="tools-tab">
      <div className="tool-section">
        <h4>{t('ui.basicTools')}</h4>
        <div className="tool-grid">
          {tools.map((tool) => (
            <button
              key={tool.name}
              className={`tool-btn ${activeTool === tool.name ? 'active' : ''}`}
              onClick={() => handleToolSelect(tool.name)}
              title={t(tool.key)}
            >
              <span className="tool-icon">{tool.icon}</span>
              <span className="tool-name">{t(tool.key)}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="tool-section">
        <h4>{t('ui.saPresets')}</h4>
        <div className="preset-buttons">
          <button className="btn btn-small btn-secondary">
            {t('presets.chest')}
          </button>
          <button className="btn btn-small btn-secondary">
            {t('presets.bone')}
          </button>
          <button className="btn btn-small btn-secondary">
            {t('presets.lung')}
          </button>
          <button className="btn btn-small btn-secondary">
            {t('presets.brain')}
          </button>
        </div>
      </div>

      <div className="tool-section">
        <h4>{t('ui.actions')}</h4>
        <div className="action-buttons">
          <button className="btn btn-small btn-warning">
            {t('tools.reset')}
          </button>
          <button className="btn btn-small btn-primary">
            {t('ui.export')}
          </button>
        </div>
      </div>
    </div>
  );

  const renderMeasurementsTab = () => (
    <div className="measurements-tab">
      <div className="measurements-header">
        <h4>{t('ui.measurements')}</h4>
        <button className="btn btn-small btn-danger">
          {t('ui.clearAll')}
        </button>
      </div>
      
      <div className="measurements-list">
        {/* Measurements will be displayed here */}
        <div className="empty-measurements">
          <div className="empty-icon">📏</div>
          <div className="empty-message">{t('ui.noMeasurements')}</div>
        </div>
      </div>
    </div>
  );

  const renderAITab = () => (
    <div className="ai-tab">
      <div className="ai-header">
        <h4>🤖 {t('ui.aiDiagnosis')}</h4>
        <button className="btn btn-small btn-primary">
          {t('ui.analyze')}
        </button>
      </div>

      <div className="ai-conditions">
        <h5>{t('ui.saConditions')}</h5>
        <div className="condition-checks">
          <label className="condition-check">
            <input type="checkbox" defaultChecked />
            <span>{t('condition.tuberculosis')}</span>
          </label>
          <label className="condition-check">
            <input type="checkbox" defaultChecked />
            <span>{t('condition.fracture')}</span>
          </label>
          <label className="condition-check">
            <input type="checkbox" />
            <span>{t('condition.pneumonia')}</span>
          </label>
          <label className="condition-check">
            <input type="checkbox" />
            <span>{t('condition.stroke')}</span>
          </label>
        </div>
      </div>

      <div className="ai-results">
        <h5>{t('ui.aiResults')}</h5>
        <div className="empty-results">
          <div className="empty-icon">🤖</div>
          <div className="empty-message">{t('ui.noAiResults')}</div>
        </div>
      </div>
    </div>
  );

  const renderVoiceTab = () => (
    <div className="voice-tab">
      <div className="voice-header">
        <h4>🎤 {t('ui.voiceDictation')}</h4>
        <button className="btn btn-small btn-danger">
          ⏺️ {t('ui.record')}
        </button>
      </div>

      <div className="voice-controls">
        <div className="language-select">
          <label>{t('ui.language')}</label>
          <select className="select">
            <option value="en">English</option>
            <option value="af">Afrikaans</option>
            <option value="zu">isiZulu</option>
          </select>
        </div>

        <div className="voice-status">
          <div className="status-indicator"></div>
          <span>{t('status.ready')}</span>
        </div>
      </div>

      <div className="voice-transcript">
        <h5>{t('ui.transcript')}</h5>
        <div className="transcript-area">
          <div className="empty-transcript">
            <div className="empty-icon">🎤</div>
            <div className="empty-message">{t('ui.noTranscript')}</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="tool-panel">
      <div className="tool-panel-header">
        <div className="tool-tabs">
          <button
            className={`tab-btn ${activeTab === 'tools' ? 'active' : ''}`}
            onClick={() => setActiveTab('tools')}
          >
            🔧 {t('ui.tools')}
          </button>
          <button
            className={`tab-btn ${activeTab === 'measurements' ? 'active' : ''}`}
            onClick={() => setActiveTab('measurements')}
          >
            📏 {t('ui.measurements')}
          </button>
          <button
            className={`tab-btn ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={() => setActiveTab('ai')}
          >
            🤖 AI
          </button>
          <button
            className={`tab-btn ${activeTab === 'voice' ? 'active' : ''}`}
            onClick={() => setActiveTab('voice')}
          >
            🎤 {t('ui.voice')}
          </button>
        </div>
      </div>

      <div className="tool-panel-content">
        {activeTab === 'tools' && renderToolsTab()}
        {activeTab === 'measurements' && renderMeasurementsTab()}
        {activeTab === 'ai' && renderAITab()}
        {activeTab === 'voice' && renderVoiceTab()}
      </div>
    </div>
  );
};