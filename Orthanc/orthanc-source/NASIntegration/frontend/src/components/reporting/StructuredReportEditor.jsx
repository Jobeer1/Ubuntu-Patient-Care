import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Mic, 
  MicOff, 
  Save, 
  CheckCircle, 
  AlertCircle, 
  Globe,
  Edit3,
  Volume2,
  Flag,
  ArrowRight,
  Clock,
  User
} from 'lucide-react';

const StructuredReportEditor = ({ 
  template, 
  language = 'en', 
  measurements = [], 
  sessionId,
  onReportUpdate, 
  onSave,
  onLanguageChange 
}) => {
  const [reportData, setReportData] = useState({});
  const [currentSection, setCurrentSection] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSection, setRecordingSection] = useState(null);
  const [completionStatus, setCompletionStatus] = useState({});
  const [validationResults, setValidationResults] = useState({});
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);

  useEffect(() => {
    if (template) {
      initializeReportData();
      calculateCompletionStatus();
    }
  }, [template]);

  useEffect(() => {
    calculateCompletionStatus();
    if (onReportUpdate) {
      onReportUpdate(reportData);
    }
  }, [reportData]);

  useEffect(() => {
    // Auto-save every 30 seconds
    const autoSaveInterval = setInterval(() => {
      if (Object.keys(reportData).length > 0) {
        autoSaveReport();
      }
    }, 30000);

    return () => clearInterval(autoSaveInterval);
  }, [reportData]);

  const initializeReportData = () => {
    const initialData = {};
    
    // Pre-populate with measurements if available
    if (measurements.length > 0) {
      initialData.measurements = formatMeasurements(measurements);
    }

    // Initialize empty values for all sections
    template.structure?.sections?.forEach(section => {
      if (section.type === 'structured' && section.fields) {
        section.fields.forEach(field => {
          initialData[`${section.id}.${field.id}`] = '';
        });
      } else {
        initialData[section.id] = '';
      }
    });

    setReportData(initialData);
  };

  const formatMeasurements = (measurements) => {
    if (!measurements || measurements.length === 0) return '';
    
    let text = 'MEASUREMENTS:\n';
    measurements.forEach((measurement, index) => {
      switch (measurement.type) {
        case 'length':
          text += `${index + 1}. Linear measurement: ${measurement.value.toFixed(2)} mm\n`;
          break;
        case 'angle':
          text += `${index + 1}. Angular measurement: ${measurement.value.toFixed(1)}°\n`;
          break;
        case 'area':
          text += `${index + 1}. Area measurement: ${measurement.value.toFixed(2)} mm²\n`;
          break;
        default:
          text += `${index + 1}. ${measurement.type}: ${measurement.value}\n`;
      }
    });
    return text;
  };

  const calculateCompletionStatus = () => {
    const status = {};
    const sections = template.structure?.sections || [];
    
    sections.forEach(section => {
      if (section.type === 'structured' && section.fields) {
        const fieldValues = section.fields.map(field => 
          reportData[`${section.id}.${field.id}`] || ''
        );
        const completedFields = fieldValues.filter(value => value.trim()).length;
        const requiredFields = section.fields.filter(field => field.required).length;
        
        status[section.id] = {
          completed: completedFields,
          total: section.fields.length,
          required: requiredFields,
          isComplete: section.required ? completedFields >= requiredFields : completedFields > 0
        };
      } else {
        const value = reportData[section.id] || '';
        status[section.id] = {
          completed: value.trim() ? 1 : 0,
          total: 1,
          required: section.required ? 1 : 0,
          isComplete: section.required ? value.trim().length > 0 : true
        };
      }
    });

    setCompletionStatus(status);
  };

  const handleFieldChange = (fieldId, value) => {
    setReportData(prev => ({
      ...prev,
      [fieldId]: value
    }));

    // Get suggestions for medical terms
    if (value.length > 2) {
      getSuggestions(value, fieldId);
    }
  };

  const getSuggestions = async (term, fieldId) => {
    try {
      const response = await fetch(`/api/reporting/sa-templates/terminology/suggestions?term=${encodeURIComponent(term)}&language=${language}&limit=5`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setSuggestions(data.suggestions.map(suggestion => ({
            ...suggestion,
            fieldId
          })));
        }
      }
    } catch (error) {
      console.error('Error getting suggestions:', error);
    }
  };

  const applySuggestion = (suggestion) => {
    handleFieldChange(suggestion.fieldId, suggestion.term);
    setSuggestions([]);
  };

  const startVoiceRecording = async (sectionId) => {
    try {
      setIsRecording(true);
      setRecordingSection(sectionId);

      // Start voice recording (integrate with existing voice system)
      const response = await fetch(`/api/reporting/sessions/${sessionId}/record`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to start recording');
      }
    } catch (error) {
      console.error('Error starting recording:', error);
      setIsRecording(false);
      setRecordingSection(null);
    }
  };

  const stopVoiceRecording = async () => {
    try {
      const response = await fetch(`/api/reporting/sessions/${sessionId}/stop`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.transcript && recordingSection) {
          handleFieldChange(recordingSection, data.transcript);
        }
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
    } finally {
      setIsRecording(false);
      setRecordingSection(null);
    }
  };

  const validateReport = async () => {
    try {
      const response = await fetch(`/api/reporting/sa-templates/templates/${template.template_id}/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          report_data: reportData
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setValidationResults(data.validation);
        }
      }
    } catch (error) {
      console.error('Error validating report:', error);
    }
  };

  const autoSaveReport = async () => {
    if (autoSaving) return;
    
    setAutoSaving(true);
    try {
      // Auto-save logic here
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate save
    } catch (error) {
      console.error('Auto-save failed:', error);
    } finally {
      setAutoSaving(false);
    }
  };

  const saveReport = async () => {
    setLoading(true);
    try {
      await validateReport();
      
      if (onSave) {
        await onSave(reportData);
      }
    } catch (error) {
      console.error('Error saving report:', error);
    } finally {
      setLoading(false);
    }
  };

  const getProgressPercentage = () => {
    const sections = template.structure?.sections || [];
    const totalSections = sections.length;
    const completedSections = sections.filter(section => 
      completionStatus[section.id]?.isComplete
    ).length;
    
    return totalSections > 0 ? Math.round((completedSections / totalSections) * 100) : 0;
  };

  const getSectionTitle = (section) => {
    return section.title?.[language] || section.title?.en || section.id;
  };

  const getFieldLabel = (field) => {
    return field.label?.[language] || field.label?.en || field.id;
  };

  const getVoicePrompt = (section) => {
    return section.voice_prompts?.[language] || section.voice_prompts?.en || '';
  };

  if (!template) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">No template selected</p>
      </div>
    );
  }

  const sections = template.structure?.sections || [];
  const progress = getProgressPercentage();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <h2 className="text-2xl font-bold text-gray-900">
                {template[`name_${language}`] || template.name_en}
              </h2>
              <p className="text-gray-600">
                {template.modality} • {template.body_part} • {template.category}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Auto-save indicator */}
            {autoSaving && (
              <div className="flex items-center text-sm text-blue-600">
                <Clock className="h-4 w-4 mr-1 animate-spin" />
                Auto-saving...
              </div>
            )}

            {/* Language selector */}
            <div className="flex items-center space-x-2">
              <Globe className="h-4 w-4 text-gray-500" />
              <select
                value={language}
                onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
                className="border border-gray-300 rounded-md px-2 py-1 text-sm"
              >
                <option value="en">🇬🇧 English</option>
                <option value="af">🇿🇦 Afrikaans</option>
                <option value="zu">🇿🇦 isiZulu</option>
              </select>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm text-gray-600">{progress}% Complete</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">💡 SA Medical Term Suggestions</h4>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => applySuggestion(suggestion)}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm hover:bg-blue-200 transition-colors"
              >
                {suggestion.term}
                {suggestion.category && (
                  <span className="ml-1 text-blue-600">({suggestion.category})</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Report Sections */}
      <div className="space-y-6">
        {sections.map((section, index) => (
          <ReportSection
            key={section.id}
            section={section}
            sectionIndex={index}
            language={language}
            reportData={reportData}
            completionStatus={completionStatus[section.id]}
            isRecording={isRecording && recordingSection === section.id}
            onFieldChange={handleFieldChange}
            onStartRecording={() => startVoiceRecording(section.id)}
            onStopRecording={stopVoiceRecording}
            getSectionTitle={getSectionTitle}
            getFieldLabel={getFieldLabel}
            getVoicePrompt={getVoicePrompt}
          />
        ))}
      </div>

      {/* Validation Results */}
      {validationResults.errors && validationResults.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
            <h4 className="text-sm font-medium text-red-900">Validation Errors</h4>
          </div>
          <ul className="text-sm text-red-800 space-y-1">
            {validationResults.errors.map((error, index) => (
              <li key={index}>• {error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {measurements.length > 0 && (
              <span>{measurements.length} measurements included</span>
            )}
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={validateReport}
              className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Validate
            </button>
            
            <button
              onClick={saveReport}
              disabled={loading || progress < 80}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4 mr-2" />
              {loading ? 'Saving...' : 'Save Report'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const ReportSection = ({ 
  section, 
  sectionIndex, 
  language, 
  reportData, 
  completionStatus,
  isRecording,
  onFieldChange, 
  onStartRecording, 
  onStopRecording,
  getSectionTitle,
  getFieldLabel,
  getVoicePrompt
}) => {
  const sectionTitle = getSectionTitle(section);
  const voicePrompt = getVoicePrompt(section);
  const isComplete = completionStatus?.isComplete || false;
  const isRequired = section.required || false;

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Section Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full mr-3 ${
              isComplete ? 'bg-green-100 text-green-600' : 
              isRequired ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'
            }`}>
              {isComplete ? (
                <CheckCircle className="h-5 w-5" />
              ) : isRequired ? (
                <AlertCircle className="h-5 w-5" />
              ) : (
                <span className="text-sm font-medium">{sectionIndex + 1}</span>
              )}
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-gray-900">{sectionTitle}</h3>
              {completionStatus && (
                <p className="text-sm text-gray-600">
                  {completionStatus.completed} of {completionStatus.total} fields completed
                  {isRequired && ' (Required)'}
                </p>
              )}
            </div>
          </div>

          {/* Voice Recording Button */}
          <button
            onClick={isRecording ? onStopRecording : onStartRecording}
            className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium ${
              isRecording 
                ? 'bg-red-600 text-white hover:bg-red-700' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
            title={voicePrompt}
          >
            {isRecording ? (
              <>
                <Square className="h-4 w-4 mr-2" />
                Stop
              </>
            ) : (
              <>
                <Mic className="h-4 w-4 mr-2" />
                Dictate
              </>
            )}
          </button>
        </div>
      </div>

      {/* Section Content */}
      <div className="p-6">
        {section.type === 'structured' && section.fields ? (
          <div className="space-y-4">
            {section.fields.map((field) => (
              <StructuredField
                key={field.id}
                field={field}
                fieldId={`${section.id}.${field.id}`}
                value={reportData[`${section.id}.${field.id}`] || ''}
                onChange={onFieldChange}
                getFieldLabel={getFieldLabel}
              />
            ))}
          </div>
        ) : (
          <div>
            <textarea
              value={reportData[section.id] || ''}
              onChange={(e) => onFieldChange(section.id, e.target.value)}
              placeholder={`Enter ${sectionTitle.toLowerCase()}...`}
              className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            />
            
            {section.suggestions && (
              <div className="mt-3">
                <p className="text-sm text-gray-600 mb-2">Common phrases:</p>
                <div className="flex flex-wrap gap-2">
                  {section.suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => onFieldChange(section.id, suggestion)}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const StructuredField = ({ field, fieldId, value, onChange, getFieldLabel }) => {
  const fieldLabel = getFieldLabel(field);

  const renderField = () => {
    switch (field.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => onChange(fieldId, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select {fieldLabel}</option>
            {field.options?.map((option, index) => (
              <option key={index} value={option}>{option}</option>
            ))}
          </select>
        );
      
      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => onChange(fieldId, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            placeholder={`Enter ${fieldLabel.toLowerCase()}`}
          />
        );
      
      case 'checkbox':
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={value === 'true'}
              onChange={(e) => onChange(fieldId, e.target.checked ? 'true' : 'false')}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 text-sm text-gray-700">{fieldLabel}</label>
          </div>
        );
      
      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(fieldId, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            placeholder={`Enter ${fieldLabel.toLowerCase()}`}
          />
        );
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {fieldLabel}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {renderField()}
    </div>
  );
};

export default StructuredReportEditor;