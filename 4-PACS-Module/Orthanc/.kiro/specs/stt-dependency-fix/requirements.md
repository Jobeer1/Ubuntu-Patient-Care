# Requirements Document

## Introduction

The Speech-to-Text (STT) system is completely non-functional because the client is sending WebM audio files that Whisper cannot process, and the server lacks proper audio conversion capabilities. The backend must only receive WAV files that Whisper can directly process. This requires implementing client-side audio conversion to WAV format before sending to the server, and ensuring the server has all necessary dependencies to process WAV files immediately.

## Requirements

### Requirement 1

**User Story:** As a developer, I want the client to convert all audio to WAV format before sending to the server, so that the backend only receives audio files that Whisper can process directly.

#### Acceptance Criteria

1. WHEN the user clicks record THEN the client SHALL capture audio in WAV format only
2. WHEN audio is recorded THEN it SHALL be converted to 16kHz WAV format before transmission
3. WHEN audio chunks are sent THEN they SHALL be in WAV format with proper headers
4. WHEN the server receives audio THEN it SHALL be ready for immediate Whisper processing
5. WHEN audio conversion fails on client THEN a clear error message SHALL be displayed

### Requirement 2

**User Story:** As a system administrator, I want the server to have all required dependencies for WAV audio processing, so that Whisper can transcribe audio without format conversion errors.

#### Acceptance Criteria

1. WHEN the server starts THEN it SHALL verify FFmpeg is installed and accessible
2. WHEN WAV files are received THEN they SHALL be processed directly by Whisper without conversion
3. WHEN FFmpeg is missing THEN the system SHALL provide automated installation
4. WHEN audio processing occurs THEN no format conversion SHALL be needed on the server
5. WHEN dependencies are satisfied THEN Whisper SHALL process audio immediately

### Requirement 3

**User Story:** As a doctor using the system, I want real-time transcription that works immediately when I speak, so that I can see my words appear as I dictate without delays or errors.

#### Acceptance Criteria

1. WHEN I click the record button THEN audio SHALL be captured in WAV format and sent in real-time chunks
2. WHEN I speak THEN my words SHALL appear as text within 2 seconds
3. WHEN audio is processed THEN Whisper SHALL receive properly formatted WAV files
4. WHEN transcription occurs THEN text SHALL appear continuously as I speak
5. WHEN I stop speaking THEN the final transcription SHALL be complete and accurate

### Requirement 4

**User Story:** As a developer, I want robust client-side audio processing using Web Audio API, so that audio conversion to WAV happens reliably in the browser before server transmission.

#### Acceptance Criteria

1. WHEN recording starts THEN Web Audio API SHALL capture audio at 16kHz sample rate
2. WHEN audio chunks are created THEN they SHALL be converted to WAV format with proper headers
3. WHEN conversion occurs THEN it SHALL use JavaScript/Web Audio API without external dependencies
4. WHEN WAV files are generated THEN they SHALL be compatible with Whisper's requirements
5. WHEN audio processing fails THEN fallback methods SHALL be attempted