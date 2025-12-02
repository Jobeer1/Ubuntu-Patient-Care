/**
 * GOTG Dictation-3: Voice Input UI Component
 * 
 * Professional microphone recording interface with:
 * - Real-time waveform visualization
 * - Transcription display
 * - Injury assessment rendering
 * - Offline support with IndexedDB caching
 * - Sync status indicator
 */

import React, { useState, useEffect, useRef } from 'react';
import './VoiceInputUI.css';

const VoiceInputUI = ({ studyId, onAssessmentComplete, authToken }) => {
  // ========================================================================
  // STATE MANAGEMENT
  // ========================================================================

  const [recording, setRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [audioPath, setAudioPath] = useState(null);
  const [transcription, setTranscription] = useState('');
  const [assessment, setAssessment] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);

  // Recording state
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationIdRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5000/api';

  // ========================================================================
  // LIFECYCLE HOOKS
  // ========================================================================

  useEffect(() => {
    window.addEventListener('online', () => setIsOnline(true));
    window.addEventListener('offline', () => setIsOnline(false));

    return () => {
      window.removeEventListener('online', () => setIsOnline(true));
      window.removeEventListener('offline', () => setIsOnline(false));
    };
  }, []);

  // Get pending sync count
  useEffect(() => {
    if (isOnline) {
      fetchPendingSyncCount();
      const interval = setInterval(fetchPendingSyncCount, 5000);
      return () => clearInterval(interval);
    }
  }, [isOnline]);

  // ========================================================================
  // MICROPHONE PERMISSIONS & SETUP
  // ========================================================================

  const requestMicrophoneAccess = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create audio context for visualization
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      analyserRef.current = analyser;
      analyser.fftSize = 256;

      const microphone = audioContext.createMediaStreamSource(stream);
      microphone.connect(analyser);

      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        chunksRef.current.push(event.data);
      };

      return true;
    } catch (err) {
      setError(`Microphone access denied: ${err.message}`);
      return false;
    }
  };

  // ========================================================================
  // RECORDING FUNCTIONS
  // ========================================================================

  const startRecording = async () => {
    try {
      setError(null);

      // Check microphone access
      const hasAccess = await requestMicrophoneAccess();
      if (!hasAccess) return;

      // Start new session
      const response = await fetch(`${API_BASE}/dictation/session/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ study_id: studyId })
      });

      if (!response.ok) {
        throw new Error(`Failed to start session: ${response.statusText}`);
      }

      const data = await response.json();
      setSessionId(data.session_id);

      // Start recording
      mediaRecorderRef.current.start();
      setRecording(true);
      setRecordingTime(0);
      chunksRef.current = [];

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1);
      }, 1000);

      // Start waveform visualization
      visualizeAudio();
    } catch (err) {
      setError(err.message);
    }
  };

  const stopRecording = async () => {
    try {
      if (!mediaRecorderRef.current || !recording) return;

      mediaRecorderRef.current.stop();
      setRecording(false);
      clearInterval(timerRef.current);
      cancelAnimationFrame(animationIdRef.current);

      // Process recording
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });

        // Upload audio
        await uploadAudio(audioBlob);

        // Transcribe
        await transcribeAudio();

        // Analyze injuries
        await analyzeInjuries();
      };
    } catch (err) {
      setError(err.message);
    }
  };

  const visualizeAudio = () => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
    setAudioLevel(average);

    animationIdRef.current = requestAnimationFrame(visualizeAudio);
  };

  // ========================================================================
  // API CALLS
  // ========================================================================

  const uploadAudio = async (audioBlob) => {
    try {
      setProcessing(true);

      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.wav');

      const response = await fetch(
        `${API_BASE}/dictation/session/${sessionId}/upload-audio`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`
          },
          body: formData
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      setAudioPath(data.audio_path);
    } catch (err) {
      setError(err.message);
    }
  };

  const transcribeAudio = async () => {
    try {
      setProcessing(true);
      setError(null);

      const response = await fetch(
        `${API_BASE}/dictation/session/${sessionId}/transcribe`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            audio_path: audioPath,
            language: 'en'
          })
        }
      );

      if (!response.ok) {
        throw new Error(`Transcription failed: ${response.statusText}`);
      }

      const data = await response.json();
      setTranscription(data.transcription);
      setProcessing(false);
    } catch (err) {
      setError(err.message);
      setProcessing(false);
    }
  };

  const analyzeInjuries = async () => {
    try {
      setProcessing(true);
      setError(null);

      const response = await fetch(
        `${API_BASE}/dictation/session/${sessionId}/assess-injuries`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ language: 'en' })
        }
      );

      if (!response.ok) {
        throw new Error(`Assessment failed: ${response.statusText}`);
      }

      const data = await response.json();
      setAssessment(data.assessment);
      setProcessing(false);

      // Notify parent component
      if (onAssessmentComplete) {
        onAssessmentComplete(data.assessment);
      }

      // Save to IndexedDB for offline access
      await cacheAssessment(data.assessment);

      // Sync if online
      if (isOnline) {
        await markForSync();
      }
    } catch (err) {
      setError(err.message);
      setProcessing(false);
    }
  };

  const fetchPendingSyncCount = async () => {
    try {
      const response = await fetch(`${API_BASE}/dictation/pending-sync`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPendingSyncCount(data.pending_count);
      }
    } catch (err) {
      console.error('Failed to fetch pending sync:', err);
    }
  };

  const markForSync = async () => {
    try {
      const response = await fetch(`${API_BASE}/dictation/mark-synced`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entity_ids: [sessionId]
        })
      });

      if (response.ok) {
        fetchPendingSyncCount();
      }
    } catch (err) {
      console.error('Failed to mark synced:', err);
    }
  };

  // ========================================================================
  // INDEXEDDB CACHING
  // ========================================================================

  const cacheAssessment = async (assessmentData) => {
    try {
      const db = await openIndexedDB();
      const tx = db.transaction('assessments', 'readwrite');
      tx.objectStore('assessments').add({
        id: sessionId,
        data: assessmentData,
        timestamp: new Date().toISOString(),
        synced: false
      });
    } catch (err) {
      console.error('Failed to cache assessment:', err);
    }
  };

  const openIndexedDB = () => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('DictationDB', 1);

      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains('assessments')) {
          db.createObjectStore('assessments', { keyPath: 'id' });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  };

  // ========================================================================
  // RENDER FUNCTIONS
  // ========================================================================

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#d32f2f';
      case 'severe': return '#f57c00';
      case 'moderate': return '#fbc02d';
      case 'minor': return '#0288d1';
      default: return '#4caf50';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical': return '🚨';
      case 'severe': return '⚠️';
      case 'moderate': return '⚠️';
      case 'minor': return 'ℹ️';
      default: return '✅';
    }
  };

  // ========================================================================
  // JSX RENDER
  // ========================================================================

  return (
    <div className="voice-input-container">
      {/* Header */}
      <div className="header">
        <h2>🎙️ Emergency Voice Dictation</h2>
        <div className="status-bar">
          <span className={`online-status ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? '🟢 Online' : '🔴 Offline'}
          </span>
          {pendingSyncCount > 0 && (
            <span className="pending-sync">
              ⏳ {pendingSyncCount} pending sync
            </span>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          ❌ {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Recording Controls */}
      <div className="recording-section">
        <div className="waveform-display">
          <div
            className="waveform-bar"
            style={{
              height: `${(audioLevel / 255) * 100}%`,
              backgroundColor: recording ? '#4caf50' : '#ccc'
            }}
          />
        </div>

        <div className="recording-info">
          <span className="recording-time">{formatTime(recordingTime)}</span>
          <span className={`recording-indicator ${recording ? 'active' : ''}`}>
            {recording ? '🔴 Recording' : '⭕ Ready'}
          </span>
        </div>

        <div className="button-group">
          <button
            className={`btn btn-primary ${recording ? 'active' : ''}`}
            onClick={recording ? stopRecording : startRecording}
            disabled={processing}
          >
            {recording ? '⏹️ Stop Recording' : '🎤 Start Recording'}
          </button>
        </div>
      </div>

      {/* Transcription Display */}
      {transcription && (
        <div className="transcription-section">
          <h3>📝 Transcription</h3>
          <div className="transcription-box">
            {transcription}
          </div>
        </div>
      )}

      {/* Processing Status */}
      {processing && (
        <div className="processing-status">
          ⏳ Processing... ({assessment ? 'Analyzing injuries' : 'Transcribing'})
          <div className="spinner"></div>
        </div>
      )}

      {/* Injury Assessment */}
      {assessment && (
        <div className="assessment-section">
          <div className="assessment-header">
            <h3>🏥 Injury Assessment</h3>
            <span className="processing-time">
              {assessment.processing_time_ms}ms
            </span>
          </div>

          {/* Severity Banner */}
          <div
            className="severity-banner"
            style={{
              backgroundColor: getSeverityColor(assessment.overall_severity),
              borderColor: getSeverityColor(assessment.overall_severity)
            }}
          >
            <span className="severity-icon">
              {getSeverityIcon(assessment.overall_severity)}
            </span>
            <span className="severity-text">
              {assessment.overall_severity.toUpperCase()}
              <span className="severity-score">
                {assessment.severity_score}/4.0
              </span>
            </span>
            <span className="human-summary">
              {assessment.human_summary}
            </span>
          </div>

          {/* Primary Injury */}
          {assessment.primary_injury && (
            <div className="primary-injury">
              <strong>Primary Injury:</strong> {assessment.primary_injury.replace(/_/g, ' ').toUpperCase()}
              <span className="category">
                ({assessment.primary_category})
              </span>
            </div>
          )}

          {/* All Injuries */}
          {assessment.all_injuries && assessment.all_injuries.length > 0 && (
            <div className="injuries-list">
              <h4>Detected Injuries ({assessment.all_injuries.length}):</h4>
              {assessment.all_injuries.map((injury, idx) => (
                <div key={idx} className="injury-item">
                  <div className="injury-type">
                    {injury.type.replace(/_/g, ' ').toUpperCase()}
                  </div>
                  <div className="injury-details">
                    <span className={`severity ${injury.severity}`}>
                      {injury.severity.toUpperCase()}
                    </span>
                    <span className="confidence">
                      Confidence: {(injury.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="mentions">
                      Mentions: {injury.mentions}
                    </span>
                    {injury.icd10 && (
                      <span className="icd10">
                        ICD-10: {injury.icd10}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Vital Signs */}
          {assessment.vital_signs && Object.keys(assessment.vital_signs).length > 0 && (
            <div className="vitals-section">
              <h4>📊 Extracted Vital Signs:</h4>
              <div className="vitals-grid">
                {Object.entries(assessment.vital_signs).map(([key, value]) => (
                  <div key={key} className="vital-item">
                    <span className="vital-label">
                      {key.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <span className="vital-value">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Clinical Observations */}
          {assessment.observations && assessment.observations.length > 0 && (
            <div className="observations-section">
              <h4>👁️ Observations:</h4>
              <div className="observations-list">
                {assessment.observations.map((obs, idx) => (
                  <span key={idx} className="observation-tag">
                    {obs}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sync Button */}
      {!isOnline && assessment && (
        <div className="offline-sync-notice">
          ✅ Assessment saved locally. Will sync when online.
        </div>
      )}
    </div>
  );
};

export default VoiceInputUI;
