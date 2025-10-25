# Requirements Document

## Introduction

The Orthanc PACS NAS integration system currently has several critical issues preventing efficient image retrieval from Network Attached Storage (NAS) devices. The system needs to be fixed to provide fast, reliable access to DICOM images stored on NAS shares, with proper indexing, search capabilities, and secure sharing functionality.

## Requirements

### Requirement 1: Fast NAS File Enumeration

**User Story:** As a radiologist, I want the system to quickly discover DICOM files on the NAS so that I can access patient images without long wait times.

#### Acceptance Criteria

1. WHEN the system enumerates files on a NAS share THEN it SHALL complete enumeration of 10,000 files within 2 minutes over a LAN connection
2. WHEN using PowerShell enumeration THEN the system SHALL use robocopy or Get-ChildItem with optimized parameters for SMB performance
3. WHEN enumeration fails THEN the system SHALL provide clear error messages indicating network, permission, or configuration issues
4. WHEN the NAS is unreachable THEN the system SHALL timeout gracefully within 30 seconds and suggest local mounting alternatives

### Requirement 2: Concurrent Header-Only DICOM Indexing

**User Story:** As a system administrator, I want the indexing process to read DICOM headers efficiently so that the system can build a searchable index without copying large image files.

#### Acceptance Criteria

1. WHEN indexing DICOM files THEN the system SHALL use pydicom with stop_before_pixels=True to read only metadata
2. WHEN processing files concurrently THEN the system SHALL use ThreadPoolExecutor with configurable worker count (default 8-16)
3. WHEN indexing encounters errors THEN the system SHALL continue processing other files and report error statistics
4. WHEN indexing is in progress THEN the system SHALL write incremental status updates every 50 processed files
5. WHEN indexing completes THEN the system SHALL group files by SeriesInstanceUID with fallback to StudyUID+SeriesNumber

### Requirement 3: Real-Time Progress Monitoring

**User Story:** As a user, I want to see live progress updates during indexing so that I know the system is working and can estimate completion time.

#### Acceptance Criteria

1. WHEN indexing starts THEN the system SHALL create an index_status.json file with enumerated_files, files_processed, series_count, errors, and running status
2. WHEN the frontend polls for status THEN the API SHALL return current progress within 500ms
3. WHEN indexing is complete THEN the system SHALL update the status file with running=false and final statistics
4. WHEN errors occur during indexing THEN the system SHALL increment error count and continue processing

### Requirement 4: Efficient Search and Filtering

**User Story:** As a radiologist, I want to search for patient studies by name, ID, or study description so that I can quickly find relevant images.

#### Acceptance Criteria

1. WHEN searching the index THEN the system SHALL support case-insensitive search across PatientName, PatientID, StudyDescription, and SeriesDescription
2. WHEN search results are returned THEN they SHALL include patient demographics, study details, series information, and file count
3. WHEN no results are found THEN the system SHALL return an empty array with appropriate HTTP status
4. WHEN the index file is missing THEN the system SHALL return a 404 error with instructions to run indexing

### Requirement 5: Secure Share Link Creation

**User Story:** As a radiologist, I want to create secure, time-limited links to share specific DICOM series with colleagues so that I can collaborate on cases while maintaining security.

#### Acceptance Criteria

1. WHEN creating a share link THEN the system SHALL generate a unique token and store it in shares.db with expiration time
2. WHEN a share link is accessed THEN the system SHALL validate the token and check expiration before allowing access
3. WHEN streaming shared files THEN the system SHALL create a zip stream on-the-fly without storing temporary files
4. WHEN share links expire THEN the system SHALL automatically deny access and log the attempt
5. WHEN share links are created THEN they SHALL be valid for 24 hours by default with configurable expiration

### Requirement 6: NAS Configuration Management

**User Story:** As a system administrator, I want to configure NAS connection settings through a web interface so that I can easily set up and test NAS connectivity.

#### Acceptance Criteria

1. WHEN configuring NAS settings THEN the system SHALL validate required fields (host, share, username, password)
2. WHEN testing NAS connection THEN the system SHALL attempt to connect and list root directory contents
3. WHEN NAS configuration is saved THEN the system SHALL enable the NAS connector and attempt reconnection
4. WHEN NAS connection fails THEN the system SHALL provide specific error messages for network, authentication, or permission issues

### Requirement 7: Error Handling and Recovery

**User Story:** As a system administrator, I want the system to handle network errors gracefully so that temporary connectivity issues don't crash the indexing process.

#### Acceptance Criteria

1. WHEN network errors occur during enumeration THEN the system SHALL retry up to 3 times with exponential backoff
2. WHEN SMB authentication fails THEN the system SHALL suggest mounting the NAS locally and provide instructions
3. WHEN individual file reads fail THEN the system SHALL log the error and continue with other files
4. WHEN the indexing process is interrupted THEN the system SHALL allow resuming from the last saved state

### Requirement 8: Performance Optimization

**User Story:** As a user, I want the system to perform well over various network conditions so that I can use it effectively in different hospital environments.

#### Acceptance Criteria

1. WHEN running over SMB networks THEN the system SHALL use native Windows tools (robocopy/PowerShell) for optimal performance
2. WHEN the NAS has high latency THEN the system SHALL automatically adjust worker thread count to prevent timeouts
3. WHEN processing large directories THEN the system SHALL use streaming enumeration to avoid memory issues
4. WHEN the system detects poor SMB performance THEN it SHALL suggest local mounting as an alternative