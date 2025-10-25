# Real-Time Speech-to-Text Design Document

## Overview

This design implements a real-time speech-to-text system that processes audio in small chunks while recording continues, providing immediate feedback to doctors during dictation. The solution uses a dual-stream approach: continuous recording with parallel chunk processing and real-time display updates.

## Architecture

### Client-Side Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MediaRecorder │───▶│  Chunk Processor │───▶│ Display Manager │
│   (Continuous)  │    │   (Parallel)     │    │  (Real-time)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Audio Buffer   │    │  Queue Manager   │    │   Text Area     │
│   (2-3 sec)     │    │  (Retry Logic)   │    │ (Auto-scroll)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Server-Side Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Audio Endpoint │───▶│ Whisper Processor│───▶│ Response Cache  │
│   (/transcribe) │    │   (Optimized)    │    │  (Session)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Temp File Mgmt  │    │ Medical Term     │    │ Context Manager │
│  (Cleanup)      │    │ Enhancement      │    │ (Chunk History) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Components and Interfaces

### 1. Real-Time Audio Processor (Client)

**Purpose:** Manages continuous recording and chunk-based processing

**Key Methods:**
- `startRealTimeRecording()`: Initiates continuous recording with chunk processing
- `processAudioChunk(chunk, chunkId)`: Sends audio chunk for transcription
- `handleChunkResult(result, chunkId)`: Processes transcription results
- `manageAudioQueue()`: Handles chunk queuing and retry logic

**Configuration:**
- Chunk duration: 2-3 seconds
- Overlap: 0.5 seconds between chunks for context
- Max concurrent requests: 3
- Retry attempts: 3 per chunk

### 2. Display Manager (Client)

**Purpose:** Handles real-time text display and user feedback

**Key Methods:**
- `appendTranscriptionChunk(text, chunkId)`: Adds new text with highlighting
- `updateProcessingStatus(status)`: Shows processing indicators
- `autoScrollToLatest()`: Maintains scroll position at latest text
- `highlightNewText(text)`: Briefly highlights newly added text

**Visual Indicators:**
- Pulsing microphone icon during recording
- Subtle spinner for processing chunks
- Brief highlight animation for new text
- Status messages for errors/connectivity

### 3. Enhanced Voice API (Server)

**Purpose:** Optimized transcription endpoint for real-time processing

**Enhancements:**
- Faster model loading (keep model in memory)
- Chunk-aware processing with session context
- Medical terminology post-processing
- Error handling for malformed audio

**New Endpoints:**
- `POST /api/voice/transcribe-chunk`: Real-time chunk processing
- `GET /api/voice/session/{id}/context`: Get session transcription context

### 4. Queue Manager (Client)

**Purpose:** Handles network issues and retry logic

**Features:**
- Local chunk storage during network issues
- Intelligent retry with exponential backoff
- Chunk ordering and deduplication
- Offline mode detection

## Data Models

### Audio Chunk Model
```javascript
{
  chunkId: string,           // Unique identifier
  sessionId: string,         // Voice session ID
  sequenceNumber: number,    // Order in recording
  audioBlob: Blob,          // Audio data
  timestamp: Date,          // Creation time
  status: 'pending' | 'processing' | 'completed' | 'failed',
  retryCount: number,       // Number of retry attempts
  transcription?: string    // Result text
}
```

### Transcription Result Model
```javascript
{
  success: boolean,
  chunkId: string,
  transcription: string,
  confidence: number,
  processingTime: number,
  medicalTermsEnhanced: boolean,
  timestamp: string
}
```

### Session Context Model
```javascript
{
  sessionId: string,
  chunks: ChunkResult[],
  fullTranscription: string,
  medicalContext: string[],  // Detected medical terms for context
  lastProcessedChunk: number
}
```

## Error Handling

### Client-Side Error Handling

1. **Network Errors:**
   - Queue chunks locally
   - Show "Processing offline" indicator
   - Retry when connection restored
   - Maintain recording continuity

2. **Audio Processing Errors:**
   - Skip failed chunks
   - Continue with next chunk
   - Log errors for debugging
   - Show user-friendly messages

3. **Browser Compatibility:**
   - Fallback for older MediaRecorder APIs
   - Alternative audio formats
   - Graceful degradation

### Server-Side Error Handling

1. **Whisper Processing Errors:**
   - Return partial results if available
   - Log detailed error information
   - Maintain session state
   - Quick error responses

2. **File Processing Errors:**
   - Validate audio format before processing
   - Handle corrupted audio gracefully
   - Clean up temp files reliably
   - Return meaningful error messages

## Testing Strategy

### Unit Tests

1. **Audio Chunk Processing:**
   - Test chunk creation and queuing
   - Verify retry logic
   - Test chunk ordering
   - Validate audio format handling

2. **Display Management:**
   - Test real-time text updates
   - Verify scroll behavior
   - Test highlighting animations
   - Validate status indicators

3. **API Endpoints:**
   - Test chunk transcription
   - Verify session context
   - Test error responses
   - Validate medical term enhancement

### Integration Tests

1. **End-to-End Real-Time Flow:**
   - Record audio and verify real-time transcription
   - Test with various speech patterns
   - Verify medical terminology accuracy
   - Test network interruption scenarios

2. **Performance Tests:**
   - Measure transcription latency
   - Test concurrent chunk processing
   - Verify memory usage during long sessions
   - Test with poor network conditions

### User Acceptance Tests

1. **Doctor Workflow Tests:**
   - Test typical medical dictation scenarios
   - Verify South African medical terminology
   - Test long report dictation
   - Validate error recovery

2. **Browser Compatibility:**
   - Test across major browsers
   - Verify mobile device support
   - Test with different microphone setups
   - Validate HTTPS requirements

## Performance Optimizations

### Client-Side Optimizations

1. **Audio Processing:**
   - Use Web Workers for audio processing
   - Implement efficient chunk buffering
   - Optimize MediaRecorder settings
   - Minimize memory usage

2. **Network Efficiency:**
   - Compress audio chunks
   - Implement request batching
   - Use connection pooling
   - Cache session data

### Server-Side Optimizations

1. **Whisper Model Management:**
   - Keep model loaded in memory
   - Use GPU acceleration if available
   - Implement model warming
   - Optimize batch processing

2. **Response Optimization:**
   - Stream responses for large chunks
   - Implement response compression
   - Use efficient JSON serialization
   - Minimize processing overhead

## Security Considerations

1. **Audio Data Protection:**
   - Encrypt audio during transmission
   - Secure temporary file handling
   - Implement session-based access control
   - Clean up audio data promptly

2. **Medical Data Compliance:**
   - Ensure HIPAA-compliant handling
   - Implement audit logging
   - Secure session management
   - Data retention policies

## Implementation Phases

### Phase 1: Core Real-Time Processing
- Implement chunk-based recording
- Create basic real-time transcription
- Add simple display updates
- Basic error handling

### Phase 2: Enhanced User Experience
- Add visual indicators and animations
- Implement queue management
- Add retry logic
- Improve error messages

### Phase 3: Optimization and Polish
- Performance optimizations
- Advanced medical terminology
- Comprehensive testing
- Documentation and deployment