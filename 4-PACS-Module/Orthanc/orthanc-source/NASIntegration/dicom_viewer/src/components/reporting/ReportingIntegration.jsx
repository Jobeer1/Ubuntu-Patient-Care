import React, { useState, useEffect } from 'react';
import { 
  Mic, 
  MicOff, 
  FileText, 
  Save, 
  Send, 
  Play, 
  Pause, 
  Square,
  Volume2,
  Edit3,
  CheckCircle
} from 'lucide-react';

const ReportingIntegration = ({ 
  studyId, 
  imageIds = [], 
  measurements = [], 
  onReportComplete 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [reportSession, setReportSession] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [reportDraft, setReportDraft] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize reporting session
  useEffect(() => {
    if (studyId && !reportSession) {
      initializeReportingSession();
    }
  }, [studyId]);

  const initializeReportingSession = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/reporting/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          study_id: studyId,
          image_ids: imageIds,
          language: 'en-ZA',
          measurements: measurements
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create reporting session: ${response.status}`);
      }

      const data = await response.json();
      setReportSession(data.session);
      
      // Pre-populate with measurements if available
      if (measurements.length > 0) {
        const measurementText = formatMeasurements(measurements);
        setReportDraft(measurementText);
      }
      
    } catch (err) {
      console.error('Error initializing reporting session:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
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
    text += '\nFINDINGS:\n';
    return text;
  };

  const startRecording = async () => {
    if (!reportSession) {
      setError('No reporting session available');
      return;
    }

    try {
      setIsRecording(true);
      setError(null);

      // Start voice recording
      const response = await fetch(`/api/reporting/sessions/${reportSession.id}/record`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to start recording');
      }

    } catch (err) {
      console.error('Error starting recording:', err);
      setError(err.message);
      setIsRecording(false);
    }
  };

  const stopRecording = async () => {
    if (!reportSession) return;

    try {
      setIsRecording(false);

      // Stop recording and get transcription
      const response = await fetch(`/api/reporting/sessions/${reportSession.id}/stop`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to stop recording');
      }

      const data = await response.json();
      if (data.transcript) {
        setTranscript(data.transcript);
        // Append to existing draft
        setReportDraft(prev => prev + '\n' + data.transcript);
      }

    } catch (err) {
      console.error('Error stopping recording:', err);
      setError(err.message);
    }
  };

  const playRecording = async () => {
    if (!reportSession) return;

    try {
      setIsPlaying(true);
      // Implementation for audio playback would go here
      // For now, just simulate playback
      setTimeout(() => setIsPlaying(false), 3000);
    } catch (err) {
      console.error('Error playing recording:', err);
      setError(err.message);
      setIsPlaying(false);
    }
  };

  const saveReport = async () => {
    if (!reportSession) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/api/reporting/sessions/${reportSession.id}/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          report_text: reportDraft,
          measurements: measurements
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save report');
      }

      // Show success message
      setError(null);
      
    } catch (err) {
      console.error('Error saving report:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const sendToTypist = async () => {
    if (!reportSession) return;

    setIsLoading(true);
    try {
      const response = await fetch(`/api/reporting/sessions/${reportSession.id}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          report_text: reportDraft,
          measurements: measurements,
          status: 'pending_review'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send to typist');
      }

      // Notify parent component
      if (onReportComplete) {
        onReportComplete(reportSession.id);
      }
      
    } catch (err) {
      console.error('Error sending to typist:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !reportSession) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Initializing reporting session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="h-6 w-6 text-blue-600 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Medical Report</h3>
              <p className="text-sm text-gray-600">
                Study: {studyId} | Images: {imageIds.length} | Measurements: {measurements.length}
              </p>
            </div>
          </div>
          
          {reportSession && (
            <div className="flex items-center text-sm text-green-600">
              <CheckCircle className="h-4 w-4 mr-1" />
              Session Active
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 m-6">
          <div className="text-red-800 text-sm">{error}</div>
        </div>
      )}

      {/* Voice Recording Controls */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Voice Dictation</h4>
        
        <div className="flex items-center space-x-4">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={!reportSession || isLoading}
            className={`flex items-center px-4 py-2 rounded-lg font-medium ${
              isRecording 
                ? 'bg-red-600 text-white hover:bg-red-700' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isRecording ? (
              <>
                <Square className="h-4 w-4 mr-2" />
                Stop Recording
              </>
            ) : (
              <>
                <Mic className="h-4 w-4 mr-2" />
                Start Recording
              </>
            )}
          </button>

          <button
            onClick={playRecording}
            disabled={!reportSession || isRecording || isLoading}
            className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPlaying ? (
              <>
                <Pause className="h-4 w-4 mr-2" />
                Playing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Play Back
              </>
            )}
          </button>

          {isRecording && (
            <div className="flex items-center text-red-600">
              <div className="animate-pulse h-3 w-3 bg-red-600 rounded-full mr-2"></div>
              Recording...
            </div>
          )}
        </div>

        {/* Live Transcript */}
        {transcript && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <div className="text-sm font-medium text-blue-900 mb-1">Latest Transcription:</div>
            <div className="text-sm text-blue-800">{transcript}</div>
          </div>
        )}
      </div>

      {/* Report Draft */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-gray-900">Report Draft</h4>
          <div className="text-xs text-gray-500">
            {reportDraft.length} characters
          </div>
        </div>
        
        <textarea
          value={reportDraft}
          onChange={(e) => setReportDraft(e.target.value)}
          placeholder="Report content will appear here as you dictate, or you can type directly..."
          className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
          disabled={isLoading}
        />
      </div>

      {/* Action Buttons */}
      <div className="border-t border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {measurements.length > 0 && (
              <span>{measurements.length} measurements included</span>
            )}
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={saveReport}
              disabled={!reportSession || isLoading || !reportDraft.trim()}
              className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Draft
            </button>
            
            <button
              onClick={sendToTypist}
              disabled={!reportSession || isLoading || !reportDraft.trim()}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4 mr-2" />
              Send to Typist
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportingIntegration;