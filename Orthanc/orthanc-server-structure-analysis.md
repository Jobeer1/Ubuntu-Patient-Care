# Orthanc Server - Complete Structure and Function Analysis

## Overview

Orthanc is a lightweight, open-source DICOM server written in C++. It is designed as a Vendor Neutral Archive (VNA) for medical imaging, providing DICOM storage, query/retrieve, and a powerful REST API. Orthanc is highly extensible via plugins and REST, and is now commonly used as a backend for advanced web viewers (OHIF, Stone) and reporting modules. The legacy OrthancExplorer frontend is included, but modern deployments use more capable viewers.


## Project Structure

### Root Directory
```
orthanc-server/
├── OrthancFramework/          # Core C++ framework (LGPL)
├── OrthancServer/             # Main server implementation (GPL)
├── Plugins/                   # Built-in and sample plugins
├── Resources/                 # Default config, scripts, assets
├── OrthancExplorer/           # Legacy web frontend (jQuery Mobile)
├── CMakeLists.txt             # Main build file
├── AUTHORS, COPYING, INSTALL, NEWS, README, TODO
```

## Core Architecture

### 1. OrthancFramework (LGPL)

**Location:** `OrthancFramework/`

This directory contains the core C++ library powering Orthanc. It provides:
- DICOM parsing, manipulation, and networking (DicomFormat, DicomNetworking, DicomParsing)
- File system abstraction and storage
- HTTP server implementation
- Background job engine
- Lua scripting integration for automation
- SQLite database wrapper (default DB, BSD licensed)

These components are used by the main server and plugins, and are essential for all Orthanc deployments.

### 2. OrthancServer (GPL)

**Location:** `OrthancServer/`

This is the main server implementation. Key subdirectories:

#### A. Sources/ - Core Server Logic
Location: `OrthancServer/Sources/`
- `main.cpp`: Application entry, server initialization, DICOM C-STORE/storage commitment handlers
- `ServerContext`: Orchestrates storage, database, plugins, jobs, and resource lifecycle
- `OrthancConfiguration`: JSON config, modality/peer setup, thread-safe access, env var support
- `ServerIndex`: Database ops, resource stability, quota management


##### Database Layer:
Location: `OrthancServer/Sources/Database/`
- `SQLiteDatabaseWrapper`: Default SQLite DB
- Plugins: PostgreSQL, MySQL, ODBC support for scalable deployments


##### REST API:
Location: `OrthancServer/Sources/OrthancRestApi/`
- `OrthancRestApi`: Main REST API coordinator
- Modular endpoints: system, resources, modalities, anonymization, archive, plugins


##### Server Jobs:
Location: `OrthancServer/Sources/ServerJobs/`
- DICOM forwarding, storage commitment, Lua job management


##### Search Engine:
Location: `OrthancServer/Sources/Search/`
- Query optimization and execution


##### Lua Scripting:
- Lua integration for event-driven automation (OnStoredInstance, OnStableStudy, OnHeartBeat, REST API access)

#### B. OrthancExplorer/ - Web Frontend

**Location:** `OrthancExplorer/`

##### Core Files:
- `explorer.html`, `explorer.css`, `explorer.js`, `file-upload.js`, `query-retrieve.js`

##### Frontend Architecture:
- **Technology Stack:** jQuery Mobile (legacy, not recommended for new deployments)
- **Pages:** Study/patient lookup, file upload, query/retrieve, jobs monitoring

##### Key Features:
- Basic DICOM navigation, tag-based search, drag-and-drop upload, query/retrieve, job monitoring
- Responsive for mobile, but limited compared to modern viewers

##### JavaScript Libraries:
- jQuery, jQuery Mobile, Slimbox2, date utilities

##### Modern Practice:
- For new PACS/reporting deployments, use OHIF, Stone, or custom React viewers for advanced UI, annotation, and reporting.

#### C. Plugins/ - Plugin System

**Location:** `Plugins/`

##### Plugin Engine:
- `Engine/OrthancPlugins.h/cpp`: Core plugin management
- Interfaces: HTTP handler, server listener, DICOM image decoder, storage/worklist commitment

##### Sample Plugins:
- Templates and utilities for custom plugin development

##### Practical Integration:
- Essential plugins for PACS/reporting: DICOMweb, Authorization, Database (PostgreSQL/MySQL/ODBC), OHIF/Stone/Webviewer, Transfers, Indexer, Object Storage
- Plugins are loaded/configured via `Configuration.json` and can extend REST API, storage, database, and security features

#### D. Resources/ - Configuration and Assets

**Location:** `Resources/`

##### Configuration:
- `Configuration.json`: Main config file (server, DICOM, storage, plugins, Lua, jobs, HTTP, WebDAV, TLS/SSL)
- Plugins and scripts are loaded/configured here

##### Sample Scripts:
- Lua: Autorouting, study completion, web service calls, DICOM modification
- Python: REST API client, batch anonymization, archiving, auto-routing

##### Tools and Utilities:
- Data recovery, anonymization profile generation, custom font rendering

##### Practical Deployment:
- Always review and tailor `Configuration.json` for your environment (NAS, database, plugins, security)
- Use sample scripts for automation, batch operations, and integration with external systems

## Key Functional Components
### 1. DICOM Protocol Support
C-STORE, C-FIND, C-MOVE, C-GET, Storage Commitment, Worklist Management
- **Storage Commitment**: Confirmation of successful storage
- **Worklist Management**: Modality worklist support

### 2. Storage Architecture
- **File System Storage**: Default storage backend
- **Storage Compression**: Optional DICOM compression
- **Storage Cache**: RAM-based caching layer
- **Plugin Storage**: Custom storage backend support
- **Quota Management**: Storage size and patient count limits

### 3. Database Layer
- **Default**: SQLite with full-text search
- **Plugin Support**: PostgreSQL, MySQL via plugins
- **Indexing**: DICOM tag indexing for fast queries
- **Metadata**: Custom metadata storage
- **Revisions**: Attachment and metadata versioning

### 4. REST API
- **Resource Hierarchy**: `/patients/{id}/studies/{id}/series/{id}/instances/{id}`
- **DICOM Operations**: Upload, download, modify, anonymize
- **System Management**: Configuration, statistics, logs
- **Job Management**: Background task monitoring
- **Plugin Extensions**: Custom endpoints via plugins

### 5. Security Features
- **HTTP Authentication**: Basic authentication support
- **TLS/SSL**: Secure communications
- **User Management**: Multi-user support
- **Plugin Authorization**: Advanced authorization via plugins
- **Audit Logging**: Security event tracking

### 6. Extensibility
- **Lua Scripting**: Event-driven automation
- **Plugin System**: C++ plugin architecture
- **REST API Extensions**: Custom endpoints
- **Storage Backends**: Custom storage implementations
- **Database Backends**: Custom database implementations

## Configuration System

### Main Configuration File
**Location**: `orthanc-server/OrthancServer/Resources/Configuration.json`

Key configuration sections:
- **Server Identity**: Name, ports, directories
- **Storage**: Compression, quotas, caching
- **Database**: SQLite settings, custom backends
- **DICOM Networking**: Modalities, TLS settings
- **HTTP Server**: Ports, authentication, compression
- **Plugins**: Loading paths and configuration
- **Lua Scripts**: Script paths and heartbeat settings
- **Jobs Engine**: Concurrency and threading
- **WebDAV**: File sharing configuration

### Environment Variables
- Configuration supports environment variable substitution
- Useful for containerized deployments
- Security-sensitive values can be externalized

## Build System

### CMake Configuration
**Main Build File**: `orthanc-server/OrthancServer/CMakeLists.txt`

#### Build Options:
- `STANDALONE_BUILD`: Embed all resources
- `BUILD_UNIT_TESTS`: Include unit tests
- `ENABLE_PLUGINS`: Plugin system support
- `BUILD_MODALITY_WORKLISTS`: Worklist plugin
- `BUILD_SERVE_FOLDERS`: File serving plugin

#### Dependencies:

- **Required:** CMake, Python, C++ compiler
- **Optional:** Mercurial for source updates
- **Third-party:** DCMTK, Boost, and others auto-downloaded
- **Docker:** Official Docker images available for rapid deployment, testing, and cloud use. Recommended for production and scalable environments.

### Supported Platforms:

- Linux (32/64-bit)
- Windows (32/64-bit)
- macOS (32/64-bit)
- FreeBSD, OpenBSD (community)
- Docker (official images)

## Plugin Ecosystem

## Plugin Ecosystem & Practical Integration

### Essential Plugins (for PACS/Reporting)
- **DICOMweb:** Modern web DICOM access (WADO, QIDO, STOW)
- **Authorization:** Advanced access control, multi-user, audit
- **Database:** PostgreSQL/MySQL/ODBC for scalable, reliable storage
- **OHIF/Stone/Webviewer:** Advanced web-based DICOM viewing, annotation, reporting
- **Transfers:** Fast DICOM transfers between servers
- **Indexer:** Filesystem indexing for large archives
- **Object Storage:** Cloud storage integration (S3, Azure, etc.)

### Plugin Architecture
- C API, event system, REST extensions, custom storage/database backends
- Plugins are loaded/configured via `Configuration.json` and can extend REST API, storage, database, and security features

### Practical Deployment
- For South African PACS/reporting, combine Orthanc with PostgreSQL plugin, DICOMweb, OHIF/Stone viewers, and Authorization plugin for best results
- Use Docker for easy deployment, updates, and cloud/on-premise flexibility

## Development and Maintenance

### Version Control
- Mercurial repository, tagged releases, stable/dev branches

### Testing
- Unit, integration, performance, compatibility tests
- For South African deployments, always test with real local data and workflows

### Documentation
- Orthanc Book, REST API docs, plugin SDK, sample code
- Community forums and real-world deployment guides

## Current Status (Version 1.12.9)

## Current Status & Practical Recommendations

### Recent Features (as of 2025)
- Enhanced job management, Prometheus metrics, HTTP auth callbacks, audit logging, storage/database improvements

### Performance
- SQLite and plugin DB optimizations, storage caching, DICOM parsing, memory management, concurrent jobs

### Practical Guidance for South African PACS/Reporting
- Use Orthanc as backend, with PostgreSQL plugin for reliability
- Deploy OHIF/Stone viewers for modern web UI
- Integrate Python/React modules for user management, reporting, and offline-first features
- Configure for local NAS, enable audit logging, and ensure POPIA compliance
- Use Docker for easy deployment and updates

This analysis now reflects the real structure, features, and practical deployment of Orthanc for modern PACS and reporting systems, including South African requirements.