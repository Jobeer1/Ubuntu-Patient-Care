# SA Medical Reporting Module - Design Document

## Overview

The SA Medical Reporting Module is a comprehensive, offline-first reporting system specifically designed for South African radiology practices. It integrates seamlessly with the existing Ubuntu Patient Care ecosystem (OpenEMR, Orthanc PACS, SA RIS Backend) while supporting the unique South African medical workflow: doctor dictation → transcriptionist review → doctor authorization → medical aid billing.

The system prioritizes user experience, offline functionality, POPI Act compliance, and seamless integration with South African medical aid schemes.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SA Medical Reporting Module                   │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React)           │  Backend (Node.js/PHP)            │
│  ├─ Voice Dictation UI      │  ├─ STT Microservice              │
│  ├─ Transcription Interface │  ├─ Report Management API         │
│  ├─ Doctor Authorization    │  ├─ Workflow Engine               │
│  ├─ DICOM Viewer Integration│  ├─ Audio Storage Service         │
│  └─ Multi-panel Layout      │  └─ Notification Service          │
├─────────────────────────────────────────────────────────────────┤
│                    Integration Layer                            │
│  ├─ OpenEMR API            │  ├─ Orthanc DICOM API             │
│  ├─ SA RIS Workflow        │  ├─ SA Billing Engine             │
│  └─ Medical Aid APIs       │  └─ POPI Compliance Logger        │
├─────────────────────────────────────────────────────────────────┤
│                    Data Layer                                   │
│  ├─ PostgreSQL (Reports)   │  ├─ File System (Audio)           │
│  ├─ Redis (Cache/Queue)    │  └─ Orthanc (DICOM Images)        │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- React 18 with TypeScript
- Ant Design for UI components
- Cornerstone.js for DICOM viewing
- Web Audio API for voice recording
- Socket.io for real-time updates
- React Query for data management

**Backend:**
- Node.js with Express (new reporting services)
- PHP integration with existing SA RIS Backend
- Vosk/Whisper.cpp for offline STT
- PostgreSQL for report storage
- Redis for caching and job queues
- Docker containers for deployment

**Integration:**
- OpenEMR REST API
- Orthanc REST API
- SA RIS Workflow Engine
- SA Billing Engine

## Components and Interfaces

### 1. Voice Dictation Component

**Purpose:** Enable radiologists to dictate reports using offline speech-to-text

**Key Features:**
- Offline STT using Vosk with medical vocabulary
- Real-time transcription with confidence scoring
- Audio recording with secure encrypted storage
- Support for South African accents and medical terminology
- Pause/resume/restart functionality

**Interface:**
```typescript
interface VoiceDictationService {
  startDictation(reportId: string): Promise<DictationSession>
  pauseDictation(sessionId: string): Promise<void>
  resumeDictation(sessionId: string): Promise<void>
  stopDictation(sessionId: string): Promise<TranscriptionResult>
  getTranscriptionProgress(sessionId: string): Promise<TranscriptionProgress>
}

interface TranscriptionResult {
  sessionId: string
  audioFileUrl: string
  transcribedText: string
  confidence: number
  medicalTermsDetected: string[]
  duration: number
  timestamp: Date
}
```

### 2. Transcriptionist Workflow Component

**Purpose:** Enable three-person transcriptionist team to review and correct dictated reports

**Key Features:**
- Queue-based work distribution
- Audio playback with text synchronization
- Collaborative editing with conflict resolution
- Medical terminology validation
- Quality scoring and feedback

**Interface:**
```typescript
interface TranscriptionWorkflowService {
  getNextReportForReview(transcriptionistId: string): Promise<ReportForReview>
  submitTranscriptionReview(reviewData: TranscriptionReview): Promise<void>
  getTranscriptionQueue(): Promise<QueueStatus>
  assignReportToTranscriptionist(reportId: string, transcriptionistId: string): Promise<void>
}

interface ReportForReview {
  reportId: string
  originalAudio: string
  transcribedText: string
  patientInfo: PatientInfo
  studyInfo: StudyInfo
  priority: 'stat' | 'urgent' | 'routine'
  estimatedReviewTime: number
}
```

### 3. Doctor Authorization Component

**Purpose:** Enable doctors to review transcriptionist changes and digitally authorize reports

**Key Features:**
- Change tracking and highlighting
- Digital signature with MFA
- Report comparison (original vs. corrected)
- Batch authorization for routine reports
- Amendment and re-dictation capabilities

**Interface:**
```typescript
interface DoctorAuthorizationService {
  getReportsForAuthorization(doctorId: string): Promise<ReportForAuthorization[]>
  reviewTranscriptionChanges(reportId: string): Promise<ChangesSummary>
  authorizeReport(reportId: string, signature: DigitalSignature): Promise<AuthorizationResult>
  requestAmendment(reportId: string, amendments: Amendment[]): Promise<void>
  batchAuthorize(reportIds: string[], signature: DigitalSignature): Promise<BatchResult>
}

interface ChangesSummary {
  totalChanges: number
  medicalTermChanges: MedicalTermChange[]
  structuralChanges: StructuralChange[]
  confidenceImprovements: ConfidenceImprovement[]
  transcriptionistNotes: string[]
}
```

### 4. DICOM Integration Component

**Purpose:** Seamlessly integrate with Orthanc PACS for image viewing and report attachment

**Key Features:**
- Multi-panel DICOM viewer
- Drag-and-drop study assignment
- Synchronized navigation across panels
- Key image capture and annotation
- Report-to-study linking

**Interface:**
```typescript
interface DICOMIntegrationService {
  getStudyForReporting(studyInstanceUID: string): Promise<StudyData>
  getSeriesForComparison(seriesInstanceUIDs: string[]): Promise<SeriesData[]>
  attachReportToStudy(reportId: string, studyInstanceUID: string): Promise<void>
  captureKeyImages(studyInstanceUID: string, imageReferences: ImageReference[]): Promise<KeyImageSet>
  getPatientPriorStudies(patientId: string, modality?: string): Promise<StudyData[]>
}
```

### 5. Medical Aid Billing Integration

**Purpose:** Automatically generate billing information and submit claims to SA medical aids

**Key Features:**
- Integration with existing SA Billing Engine
- Automatic procedure code extraction
- Real-time medical aid verification
- Electronic claim submission
- Payment tracking and reconciliation

**Interface:**
```typescript
interface MedicalAidBillingService {
  generateBillingFromReport(reportId: string): Promise<BillingData>
  verifyMedicalAidBenefits(memberNumber: string, procedures: string[]): Promise<BenefitVerification>
  submitClaim(claimData: ClaimData): Promise<ClaimSubmissionResult>
  trackClaimStatus(claimNumber: string): Promise<ClaimStatus>
  generateInvoice(reportId: string): Promise<InvoiceData>
}
```

## Data Models

### Report Data Model

```typescript
interface RadiologyReport {
  id: string
  patientId: string
  studyInstanceUID: string
  reportingDoctorId: string
  
  // Workflow state
  status: 'dictated' | 'transcription_review' | 'doctor_review' | 'authorized' | 'delivered'
  priority: 'stat' | 'urgent' | 'routine'
  
  // Content
  clinicalHistory: string
  technique: string
  findings: string
  impression: string
  recommendations: string
  
  // Dictation data
  originalAudioUrl?: string
  dictationSessionId?: string
  dictationTimestamp?: Date
  
  // Transcription data
  transcriptionReviews: TranscriptionReview[]
  transcriptionCompletedAt?: Date
  
  // Authorization data
  authorizedBy?: string
  authorizedAt?: Date
  digitalSignature?: string
  
  // Billing data
  billingCodes: BillingCode[]
  claimNumber?: string
  
  // Metadata
  createdAt: Date
  updatedAt: Date
  version: number
}

interface TranscriptionReview {
  transcriptionistId: string
  reviewedAt: Date
  changes: TextChange[]
  qualityScore: number
  notes: string
  timeSpent: number
}

interface TextChange {
  position: number
  originalText: string
  correctedText: string
  changeType: 'medical_term' | 'grammar' | 'punctuation' | 'structure'
  confidence: number
}
```

### Audio Session Data Model

```typescript
interface AudioSession {
  id: string
  reportId: string
  doctorId: string
  audioFileUrl: string
  duration: number
  fileSize: number
  format: 'wav' | 'mp3'
  sampleRate: number
  channels: number
  
  // STT Results
  transcriptionText: string
  confidence: number
  medicalTermsDetected: MedicalTerm[]
  
  // Security
  encrypted: boolean
  encryptionKey: string
  
  createdAt: Date
  expiresAt: Date
}
```

### Workflow State Model

```typescript
interface ReportWorkflowState {
  reportId: string
  currentState: WorkflowState
  stateHistory: StateTransition[]
  assignedUsers: UserAssignment[]
  
  // Timing
  dictationStarted?: Date
  dictationCompleted?: Date
  transcriptionStarted?: Date
  transcriptionCompleted?: Date
  authorizationStarted?: Date
  authorizationCompleted?: Date
  
  // Performance metrics
  totalProcessingTime?: number
  dictationDuration?: number
  transcriptionDuration?: number
  authorizationDuration?: number
}

type WorkflowState = 
  | 'awaiting_dictation'
  | 'dictation_in_progress'
  | 'awaiting_transcription'
  | 'transcription_in_progress'
  | 'awaiting_authorization'
  | 'authorization_in_progress'
  | 'authorized'
  | 'delivered'
  | 'amended'
```

## Error Handling

### Error Categories

1. **STT Errors**
   - Audio quality issues
   - Microphone access denied
   - STT service unavailable
   - Low confidence transcription

2. **Workflow Errors**
   - Invalid state transitions
   - User permission errors
   - Concurrent editing conflicts
   - Missing required data

3. **Integration Errors**
   - PACS connection failures
   - OpenEMR API errors
   - Medical aid API failures
   - Billing system errors

4. **Data Errors**
   - Report corruption
   - Audio file corruption
   - Database connection issues
   - Sync conflicts

### Error Handling Strategy

```typescript
interface ErrorHandler {
  handleSTTError(error: STTError): Promise<ErrorResolution>
  handleWorkflowError(error: WorkflowError): Promise<ErrorResolution>
  handleIntegrationError(error: IntegrationError): Promise<ErrorResolution>
  handleDataError(error: DataError): Promise<ErrorResolution>
}

interface ErrorResolution {
  resolved: boolean
  fallbackAction?: string
  userMessage: string
  retryable: boolean
  logLevel: 'info' | 'warn' | 'error' | 'critical'
}
```

### Offline Error Handling

- Queue failed operations for retry when online
- Provide clear offline status indicators
- Enable manual sync triggers
- Store error logs locally for later analysis

## Testing Strategy

### Unit Testing
- Component-level testing for all React components
- Service-level testing for all backend services
- Mock external dependencies (OpenEMR, Orthanc, Medical Aids)
- Test error handling and edge cases

### Integration Testing
- End-to-end workflow testing
- PACS integration testing
- Medical aid API integration testing
- Audio recording and STT pipeline testing

### User Acceptance Testing
- Radiologist workflow testing
- Transcriptionist workflow testing
- Performance testing under load
- Offline functionality testing
- South African medical terminology accuracy testing

### Performance Testing
- STT processing speed benchmarks
- Large report handling
- Concurrent user load testing
- Audio file processing optimization
- Database query performance

### Security Testing
- Audio encryption verification
- POPI Act compliance validation
- User authentication and authorization
- Data transmission security
- Audit trail completeness

## Deployment Architecture

### Production Environment

```yaml
services:
  reporting-frontend:
    image: sa-ris/reporting-frontend:latest
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=https://api.sa-ris.local
      - REACT_APP_ORTHANC_URL=https://pacs.sa-ris.local
    
  reporting-backend:
    image: sa-ris/reporting-backend:latest
    ports:
      - "3001:3001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/sa_ris
      - REDIS_URL=redis://redis:6379
      - STT_SERVICE_URL=http://stt-service:8080
    
  stt-service:
    image: sa-ris/stt-service:latest
    ports:
      - "8080:8080"
    volumes:
      - ./models:/app/models
      - ./audio_storage:/app/audio
    environment:
      - MODEL_PATH=/app/models/vosk-model-en-za-0.22
      - AUDIO_STORAGE_PATH=/app/audio
    
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=sa_ris
      - POSTGRES_USER=sa_ris_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

### Security Configuration

- TLS 1.3 for all communications
- AES-256 encryption for audio files
- JWT tokens with short expiration
- Role-based access control
- Audit logging for all actions
- Regular security updates

### Monitoring and Logging

- Application performance monitoring
- STT processing metrics
- Workflow completion times
- Error rate tracking
- User activity logging
- System resource monitoring

This design provides a comprehensive foundation for building a world-class medical reporting system specifically tailored for South African radiology practices, ensuring it integrates seamlessly with existing infrastructure while providing an exceptional user experience.