import React, { useState, useEffect, useRef } from 'react';
import { 
  Edit3, 
  Save, 
  Undo, 
  Redo, 
  Flag, 
  CheckCircle,
  AlertTriangle,
  Volume2
} from 'lucide-react';

const TranscriptSync = ({ 
  sessionId,
  originalTranscript = '',
  currentTime = 0,
  onTranscriptChange,
  onTimeJump,
  onSaveCorrections,
  className = ''
}) => {
  const [transcript, setTranscript] = useState(originalTranscript);
  const [hasChanges, setHasChanges] = useState(false);
  const [highlightedSegment, setHighlightedSegment] = useState(null);
  const [flaggedSegments, setFlaggedSegments] = useState(new Set());
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef(null);

  // Mock transcript segments with timestamps (in real implementation, this would come from STT)
  const [transcriptSegments] = useState([
    { start: 0, end: 5, text: "The patient presents with chest pain" },
    { start: 5, end: 10, text: "and shortness of breath." },
    { start: 10, end: 15, text: "Physical examination reveals" },
    { start: 15, end: 20, text: "decreased air entry on the right side." },
    { start: 20, end: 25, text: "Chest X-ray shows consolidation" },
    { start: 25, end: 30, text: "in the right lower lobe" },
    { start: 30, end: 35, text: "consistent with pneumonia." }
  ]);

  useEffect(() => {
    setTranscript(originalTranscript);
  }, [originalTranscript]);

  useEffect(() => {
    // Find which segment is currently playing
    const currentSegment = transcriptSegments.find(
      segment => currentTime >= segment.start && currentTime < segment.end
    );
    
    if (currentSegment) {
      setHighlightedSegment(currentSegment);
    }
  }, [currentTime, transcriptSegments]);

  const handleTranscriptChange = (e) => {
    const newValue = e.target.value;
    
    // Save current state to undo stack
    if (transcript !== newValue) {
      setUndoStack(prev => [...prev, transcript]);
      setRedoStack([]); // Clear redo stack when new change is made
    }
    
    setTranscript(newValue);
    setHasChanges(newValue !== originalTranscript);
    
    if (onTranscriptChange) {
      onTranscriptChange(newValue);
    }
  };

  const handleSegmentClick = (segment) => {
    if (onTimeJump) {
      onTimeJump(segment.start);
    }
  };

  const handleUndo = () => {
    if (undoStack.length > 0) {
      const previousState = undoStack[undoStack.length - 1];
      setRedoStack(prev => [transcript, ...prev]);
      setUndoStack(prev => prev.slice(0, -1));
      setTranscript(previousState);
      setHasChanges(previousState !== originalTranscript);
    }
  };

  const handleRedo = () => {
    if (redoStack.length > 0) {
      const nextState = redoStack[0];
      setUndoStack(prev => [...prev, transcript]);
      setRedoStack(prev => prev.slice(1));
      setTranscript(nextState);
      setHasChanges(nextState !== originalTranscript);
    }
  };

  const handleFlagSegment = (segmentIndex) => {
    const newFlagged = new Set(flaggedSegments);
    if (newFlagged.has(segmentIndex)) {
      newFlagged.delete(segmentIndex);
    } else {
      newFlagged.add(segmentIndex);
    }
    setFlaggedSegments(newFlagged);
  };

  const handleSave = async () => {
    if (!hasChanges) return;
    
    setSaving(true);
    try {
      if (onSaveCorrections) {
        await onSaveCorrections({
          original_text: originalTranscript,
          corrected_text: transcript,
          flagged_segments: Array.from(flaggedSegments),
          session_id: sessionId
        });
      }
      
      setHasChanges(false);
      // Clear undo/redo stacks after successful save
      setUndoStack([]);
      setRedoStack([]);
      
    } catch (error) {
      console.error('Error saving corrections:', error);
      alert('Failed to save corrections. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const getSegmentHighlight = (segment, index) => {
    const isHighlighted = highlightedSegment && 
      segment.start === highlightedSegment.start && 
      segment.end === highlightedSegment.end;
    
    const isFlagged = flaggedSegments.has(index);
    
    if (isHighlighted && isFlagged) {
      return 'bg-red-200 border-red-400';
    } else if (isHighlighted) {
      return 'bg-blue-200 border-blue-400';
    } else if (isFlagged) {
      return 'bg-yellow-200 border-yellow-400';
    } else {
      return 'bg-gray-50 border-gray-200 hover:bg-gray-100';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
        <div className="flex items-center space-x-2">
          <button
            onClick={handleUndo}
            disabled={undoStack.length === 0}
            className="flex items-center px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Undo (Ctrl+Z)"
          >
            <Undo className="h-4 w-4 mr-1" />
            Undo
          </button>
          
          <button
            onClick={handleRedo}
            disabled={redoStack.length === 0}
            className="flex items-center px-3 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Redo (Ctrl+Y)"
          >
            <Redo className="h-4 w-4 mr-1" />
            Redo
          </button>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">
            {transcript.length} characters
          </span>
          
          {hasChanges && (
            <span className="text-sm text-orange-600 bg-orange-100 px-2 py-1 rounded">
              Unsaved changes
            </span>
          )}
          
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save Corrections'}
          </button>
        </div>
      </div>

      {/* Segmented Transcript View */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">
          Segmented Transcript (Click to jump to audio position)
        </h3>
        
        <div className="space-y-2">
          {transcriptSegments.map((segment, index) => (
            <div
              key={index}
              className={`p-3 border rounded-lg cursor-pointer transition-all ${getSegmentHighlight(segment, index)}`}
              onClick={() => handleSegmentClick(segment)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Volume2 className="h-4 w-4 text-gray-500" />
                  <span className="text-xs text-gray-500 font-mono">
                    {Math.floor(segment.start)}s - {Math.floor(segment.end)}s
                  </span>
                  {highlightedSegment === segment && (
                    <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">
                      Playing
                    </span>
                  )}
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFlagSegment(index);
                  }}
                  className={`p-1 rounded ${
                    flaggedSegments.has(index)
                      ? 'text-red-600 bg-red-100'
                      : 'text-gray-400 hover:text-red-600'
                  }`}
                  title="Flag for review"
                >
                  <Flag className="h-4 w-4" />
                </button>
              </div>
              
              <div className="mt-2 text-gray-800">
                {segment.text}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Full Transcript Editor */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">
            Full Transcript Editor
          </h3>
          
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-blue-200 border border-blue-400 rounded mr-1"></div>
              Currently playing
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-yellow-200 border border-yellow-400 rounded mr-1"></div>
              Flagged for review
            </div>
          </div>
        </div>
        
        <textarea
          ref={textareaRef}
          value={transcript}
          onChange={handleTranscriptChange}
          className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none font-mono text-sm"
          placeholder="Transcript will appear here for editing..."
        />
        
        {/* SA Medical Term Suggestions */}
        <div className="mt-3 p-3 bg-blue-50 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-2">
            SA Medical Term Suggestions
          </h4>
          <div className="flex flex-wrap gap-2">
            {['tuberculosis', 'pneumonia', 'consolidation', 'effusion', 'cardiomegaly'].map((term) => (
              <button
                key={term}
                onClick={() => {
                  const textarea = textareaRef.current;
                  if (textarea) {
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    const newText = transcript.substring(0, start) + term + transcript.substring(end);
                    setTranscript(newText);
                    setHasChanges(true);
                  }
                }}
                className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Flagged Segments Summary */}
      {flaggedSegments.size > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
            <h4 className="text-sm font-medium text-yellow-900">
              Flagged Segments ({flaggedSegments.size})
            </h4>
          </div>
          <p className="text-sm text-yellow-800">
            You have flagged {flaggedSegments.size} segment(s) for review. 
            These will be highlighted for the doctor to review.
          </p>
        </div>
      )}
    </div>
  );
};

export default TranscriptSync;