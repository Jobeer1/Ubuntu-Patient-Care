import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Save, 
  Send, 
  AlertCircle, 
  CheckCircle, 
  FileText,
  Headphones,
  Edit3
} from 'lucide-react';
import AudioPlayer from './AudioPlayer';
import TranscriptSync from './TranscriptSync';

const CorrectionEditor = ({ sessionId, onBack, onComplete }) => {
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [correctedTranscript, setCorrectedTranscript] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchSessionData();
    }
  }, [sessionId]);

  const fetchSessionData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/reporting/typist/session/${sessionId}/correction`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch session: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setSessionData(data.session);
        setCorrectedTranscript(data.session.corrected_transcript || data.session.raw_transcript || '');
      } else {
        throw new Error(data.error || 'Failed to load session');
      }
      
    } catch (err) {
      console.error('Error fetching session data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTranscriptChange = (newTranscript) => {
    setCorrectedTranscript(newTranscript);
    setHasChanges(newTranscript !== (sessionData?.raw_transcript || ''));
  };

  const handleTimeJump = (time) => {
    setCurrentTime(time);
    // In a real implementation, this would also update the audio player
  };

  const handleSaveCorrections = async (correctionData) => {
    setSaving(true);
    
    try {
      const response = await fetch(`/api/reporting/typist/session/${sessionId}/corrections`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          corrected_text: correctionData.corrected_text,
          notes: `Flagged segments: ${correctionData.flagged_segments?.length || 0}`,
          flagged_segments: correctionData.flagged_segments
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to save corrections: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setHasChanges(false);
        // Update session data with saved corrections
        setSessionData(prev => ({
          ...prev,
          corrected_transcript: correctionData.corrected_text,
          status: 'corrected'
        }));
      } else {
        throw new Error(data.error || 'Failed to save corrections');
      }
      
    } catch (err) {
      console.error('Error saving corrections:', err);
      throw err; // Re-throw to be handled by TranscriptSync
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitForQA = async () => {
    if (hasChanges) {
      alert('Please save your corrections before submitting for QA.');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const response = await fetch(`/api/reporting/typist/session/${sessionId}/submit-qa`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          final_transcript: correctedTranscript
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to submit for QA: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        if (onComplete) {
          onComplete(sessionId);
        }
      } else {
        throw new Error(data.error || 'Failed to submit for QA');
      }
      
    } catch (err) {
      console.error('Error submitting for QA:', err);
      alert(`Error submitting for QA: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading correction editor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center mb-4">
          <AlertCircle className="h-6 w-6 text-red-600 mr-3" />
          <h3 className="text-lg font-medium text-red-900">Error Loading Session</h3>
        </div>
        <p className="text-red-800 mb-4">{error}</p>
        <div className="flex space-x-3">
          <button
            onClick={fetchSessionData}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Back to Queue
          </button>
        </div>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">No session data available</p>
      </div>
    );
  }

  const audioUrl = sessionData.audio_file_path 
    ? `/api/reporting/sessions/${sessionId}/audio` 
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={onBack}
              className="mr-4 p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            
            <div className="flex items-center">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Edit3 className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <h1 className="text-2xl font-bold text-gray-900">Correction Editor</h1>
                <p className="text-gray-600">
                  Patient: {sessionData.patient_id} | Study: {sessionData.study_id}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              sessionData.status === 'claimed' 
                ? 'bg-orange-100 text-orange-800'
                : sessionData.status === 'corrected'
                ? 'bg-green-100 text-green-800'
                : 'bg-blue-100 text-blue-800'
            }`}>
              {sessionData.status === 'claimed' ? 'In Progress' :
               sessionData.status === 'corrected' ? 'Corrected' : 
               sessionData.status}
            </div>
            
            <button
              onClick={handleSubmitForQA}
              disabled={hasChanges || submitting || !correctedTranscript.trim()}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4 mr-2" />
              {submitting ? 'Submitting...' : 'Submit for QA'}
            </button>
          </div>
        </div>
      </div>

      {/* Session Info */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Session Information</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Language</label>
            <p className="text-sm text-gray-900">{sessionData.language}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Created</label>
            <p className="text-sm text-gray-900">
              {new Date(sessionData.created_date).toLocaleString()}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Audio Duration</label>
            <p className="text-sm text-gray-900">
              {sessionData.audio_duration ? 
                `${Math.floor(sessionData.audio_duration / 60)}:${Math.floor(sessionData.audio_duration % 60).toString().padStart(2, '0')}` : 
                'N/A'
              }
            </p>
          </div>
        </div>
      </div>

      {/* Audio Player */}
      {audioUrl && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center mb-4">
            <Headphones className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Audio Playback</h3>
          </div>
          
          <AudioPlayer
            sessionId={sessionId}
            audioUrl={audioUrl}
            transcript={correctedTranscript}
            onTimeUpdate={setCurrentTime}
            onTranscriptClick={handleTimeJump}
          />
        </div>
      )}

      {/* Transcript Editor */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center mb-4">
          <FileText className="h-5 w-5 text-gray-600 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Transcript Correction</h3>
        </div>
        
        <TranscriptSync
          sessionId={sessionId}
          originalTranscript={sessionData.raw_transcript || ''}
          currentTime={currentTime}
          onTranscriptChange={handleTranscriptChange}
          onTimeJump={handleTimeJump}
          onSaveCorrections={handleSaveCorrections}
        />
      </div>

      {/* Status Messages */}
      {hasChanges && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 text-orange-600 mr-2" />
            <span className="text-orange-800">
              You have unsaved changes. Please save before submitting for QA.
            </span>
          </div>
        </div>
      )}
      
      {!hasChanges && correctedTranscript && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center">
            <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
            <span className="text-green-800">
              All changes saved. Ready to submit for QA review.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CorrectionEditor;