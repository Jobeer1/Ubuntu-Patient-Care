# MCP Server Design Plan for Ubuntu Patient Care System

**Version:** 1.0  
**Date:** October 14, 2025  
**Project:** Ubuntu Patient Care — Unified Healthcare Platform Integration  
**Purpose:** Design a Model Context Protocol (MCP) server that connects a lightweight offline LLM agent to PACS, RIS, Medical Reporting, and Billing modules.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [System Components](#3-system-components)
4. [Module Integration Strategy](#4-module-integration-strategy)
5. [Lightweight Offline LLM Selection](#5-lightweight-offline-llm-selection)
6. [MCP Server API & Tool Definitions](#6-mcp-server-api--tool-definitions)
7. [Security, Authentication & Audit](#7-security-authentication--audit)
8. [Data Flow & Sequence Diagrams](#8-data-flow--sequence-diagrams)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment & Infrastructure](#10-deployment--infrastructure)
11. [Developer Documentation & SDKs](#11-developer-documentation--sdks)
12. [POC Roadmap & Milestones](#12-poc-roadmap--milestones)
13. [Risk Assessment & Mitigation](#13-risk-assessment--mitigation)
14. [Appendices](#14-appendices)

---

## 1. Executive Summary

### 1.1 Vision

Create an **MCP (Model Context Protocol) Server** that acts as a unified orchestration layer, enabling a lightweight offline LLM to intelligently interact with:

- **PACS (Picture Archiving and Communication System)** — Orthanc-based DICOM management
- **RIS (Radiology Information System)** — Patient scheduling, study orders, reporting workflows
- **Medical Reporting Module** — Voice-to-text transcription, structured report generation
- **Medical Billing/Accounting Module** — Claims processing, invoicing, payment tracking

### 1.2 Core Objectives

1. **Offline-First AI Agent**: Deploy a local LLM (e.g., Llama 2 7B quantized, Mistral 7B, GPT4All) that can operate without external API dependencies
2. **Tool-Based Orchestration**: Use MCP protocol to expose module capabilities as discrete tools/functions the LLM can invoke
3. **HIPAA-Compliant Security**: Ensure PHI (Protected Health Information) is encrypted, access-controlled, and audited
4. **Seamless Integration**: Provide adapters for each module with standardized APIs (REST, DICOMweb, HL7 FHIR where applicable)
5. **Scalability & Maintainability**: Modular architecture allowing independent module upgrades and horizontal scaling

### 1.3 Success Criteria

- LLM can retrieve patient DICOM studies from PACS via natural language query
- LLM can schedule radiology appointments and retrieve RIS worklists
- LLM can transcribe/summarize medical reports and store them in the reporting module
- LLM can generate billing summaries and reconcile claims
- Sub-500ms latency for tool invocations (excluding LLM inference time)
- 99.9% uptime for MCP server in production

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface Layer                        │
│  (Web UI, Mobile App, Voice Assistant, CLI)                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Lightweight Offline LLM Agent                   │
│  • Llama 2 7B / Mistral 7B / GPT4All (quantized GGUF/GGML)     │
│  • Tool Calling via Function/JSON mode                           │
│  • Context Management (RAG optional)                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ MCP Protocol (JSON-RPC / REST)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MCP Server Core                            │
│  • Tool Registry & Invocation Router                             │
│  • Request Validation & Response Formatting                      │
│  • Auth/Authorization Middleware                                 │
│  • Logging, Metrics, Tracing (OpenTelemetry)                    │
└───┬─────────────┬─────────────┬─────────────┬───────────────────┘
    │             │             │             │
    ▼             ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────────┐  ┌──────────┐
│  PACS  │  │  RIS   │  │ Reporting  │  │ Billing  │
│Adapter │  │Adapter │  │  Adapter   │  │ Adapter  │
└───┬────┘  └───┬────┘  └─────┬──────┘  └────┬─────┘
    │           │             │              │
    ▼           ▼             ▼              ▼
┌────────┐  ┌────────┐  ┌────────────┐  ┌──────────┐
│Orthanc │  │  RIS   │  │  Medical   │  │ Billing  │
│ PACS   │  │Database│  │ Reporting  │  │ Database │
│ Server │  │        │  │   Module   │  │          │
└────────┘  └────────┘  └────────────┘  └──────────┘
```

### 2.2 Design Principles

1. **Separation of Concerns**: Each adapter is independent, testable, and replaceable
2. **Protocol Agnostic**: MCP server exposes REST/gRPC; adapters use native protocols (DICOMweb, HL7, SQL)
3. **Stateless MCP Server**: All session state managed by LLM runtime or external cache (Redis)
4. **Event-Driven**: Optional async operations via message queue (RabbitMQ/Kafka) for long-running tasks
5. **Defense in Depth**: Multi-layer security (network, application, data encryption)

---

## 3. System Components

### 3.1 MCP Server Core

**Technology Stack:**
- **Language:** Python 3.11+ (FastAPI) or Node.js 20+ (Express/Fastify)
- **Framework:** FastAPI with Pydantic for request validation
- **Communication:** REST API (HTTP/2) with optional WebSocket for streaming
- **Serialization:** JSON (with optional MessagePack for binary efficiency)

**Key Modules:**
- `tool_registry.py` — Dynamic tool registration and discovery
- `invocation_router.py` — Routes tool calls to appropriate adapters
- `auth_middleware.py` — JWT/OAuth2/mTLS authentication
- `audit_logger.py` — HIPAA-compliant audit trail (WHO, WHAT, WHEN, WHERE)
- `error_handler.py` — Standardized error responses with retry hints

### 3.2 Lightweight Offline LLM Agent

**Recommended Models (CPU-optimized):**

| Model | Size | Quantization | RAM | Speed | Use Case |
|-------|------|--------------|-----|-------|----------|
| **Llama 2 7B** | 7B | GGUF Q4_K_M | 6-8 GB | ~20 tok/s | General medical queries |
| **Mistral 7B Instruct** | 7B | GGUF Q5_K_M | 8-10 GB | ~18 tok/s | Tool calling, structured output |
| **GPT4All Falcon** | 7B | GGML Q4_0 | 5-7 GB | ~25 tok/s | Fast inference, lower accuracy |
| **Llama 3.1 8B** | 8B | GGUF Q4_K_S | 8-10 GB | ~15 tok/s | Latest, best instruction following |

**Inference Runtime:**
- **llama.cpp** (C++ with Python bindings via `llama-cpp-python`)
- **Ollama** (wrapper around llama.cpp with model management)
- **LM Studio** (GUI for local model deployment)
- **vLLM** (GPU-optimized, if CUDA available)

**Tool Calling Implementation:**
- Use **function calling** mode (supported by Llama 2, Mistral, GPT-4 format prompts)
- JSON schema definitions for each MCP tool
- Fallback to regex parsing if model doesn't support native function calling

### 3.3 Module Adapters

Each adapter is a microservice or library implementing a standard interface:

```python
class ModuleAdapter(ABC):
    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """Initialize connection to target module"""
        
    @abstractmethod
    async def invoke_tool(self, tool_name: str, params: dict) -> dict:
        """Execute a tool and return structured result"""
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Verify module connectivity"""
```

---

## 4. Module Integration Strategy

### 4.1 PACS Module (Orthanc)

**Protocol:** DICOMweb (WADO-RS, QIDO-RS, STOW-RS)

**Exposed Tools:**

1. **`pacs_search_studies`**
   - **Input:** `{ patient_id?, patient_name?, study_date?, modality? }`
   - **Output:** List of studies with metadata (StudyInstanceUID, AccessionNumber, etc.)
   - **Implementation:** HTTP GET to `/dicom-web/studies` with QIDO-RS query params

2. **`pacs_retrieve_study`**
   - **Input:** `{ study_instance_uid: str }`
   - **Output:** Download URLs for DICOM instances or thumbnail previews
   - **Implementation:** WADO-RS retrieval, optional conversion to JPEG via Orthanc API

3. **`pacs_upload_study`**
   - **Input:** `{ dicom_files: List[bytes] }`
   - **Output:** Created StudyInstanceUID
   - **Implementation:** STOW-RS multipart POST

4. **`pacs_get_patient_history`**
   - **Input:** `{ patient_id: str }`
   - **Output:** Timeline of all imaging studies
   - **Implementation:** Aggregate QIDO-RS results + database query to Orthanc DB

**Adapter Implementation:**
```python
# adapters/pacs_adapter.py
import httpx
from pydicom import dcmread

class OrthancPACSAdapter(ModuleAdapter):
    def __init__(self, orthanc_url: str, username: str, password: str):
        self.base_url = orthanc_url
        self.auth = (username, password)
        self.client = httpx.AsyncClient(auth=self.auth)
    
    async def invoke_tool(self, tool_name: str, params: dict):
        if tool_name == "pacs_search_studies":
            return await self._search_studies(**params)
        elif tool_name == "pacs_retrieve_study":
            return await self._retrieve_study(**params)
        # ... other tools
    
    async def _search_studies(self, patient_id=None, modality=None, ...):
        query_params = {}
        if patient_id:
            query_params["PatientID"] = patient_id
        if modality:
            query_params["ModalitiesInStudy"] = modality
        
        response = await self.client.get(
            f"{self.base_url}/dicom-web/studies",
            params=query_params
        )
        return response.json()
```

### 4.2 RIS Module

**Protocol:** REST API + HL7 FHIR (optional for interoperability)

**Exposed Tools:**

1. **`ris_schedule_appointment`**
   - **Input:** `{ patient_id, modality, requested_date, priority }`
   - **Output:** `{ appointment_id, scheduled_time, room }`

2. **`ris_get_worklist`**
   - **Input:** `{ date?, modality?, technologist_id? }`
   - **Output:** List of scheduled studies (MWL — Modality Worklist)

3. **`ris_update_study_status`**
   - **Input:** `{ study_id, status: "scheduled"|"in_progress"|"completed"|"cancelled" }`
   - **Output:** Success confirmation

4. **`ris_get_referring_physician`**
   - **Input:** `{ physician_id }`
   - **Output:** Physician details (name, NPI, contact)

**Database Schema (Example):**
```sql
-- RIS PostgreSQL schema
CREATE TABLE appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    modality VARCHAR(10),
    scheduled_time TIMESTAMP,
    status VARCHAR(20),
    room VARCHAR(10),
    technologist_id INT REFERENCES staff(staff_id)
);

CREATE TABLE modality_worklist (
    accession_number VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50),
    study_description TEXT,
    requested_procedure_id VARCHAR(50),
    scheduled_station_ae_title VARCHAR(16)
);
```

**Adapter Implementation:**
```python
# adapters/ris_adapter.py
import asyncpg

class RISAdapter(ModuleAdapter):
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
    
    async def initialize(self, config):
        self.pool = await asyncpg.create_pool(self.db_url)
    
    async def invoke_tool(self, tool_name: str, params: dict):
        if tool_name == "ris_schedule_appointment":
            return await self._schedule_appointment(**params)
        # ...
    
    async def _schedule_appointment(self, patient_id, modality, requested_date, priority):
        async with self.pool.acquire() as conn:
            # Business logic: find available slot
            slot = await self._find_available_slot(conn, modality, requested_date)
            
            appointment_id = await conn.fetchval("""
                INSERT INTO appointments (patient_id, modality, scheduled_time, status)
                VALUES ($1, $2, $3, 'scheduled')
                RETURNING appointment_id
            """, patient_id, modality, slot)
            
            return {"appointment_id": appointment_id, "scheduled_time": slot}
```

### 4.3 Medical Reporting Module

**Protocol:** Internal REST API + Database access

**Exposed Tools:**

1. **`reporting_transcribe_audio`**
   - **Input:** `{ audio_data: bytes, format: "wav"|"mp3" }`
   - **Output:** `{ transcription: str, confidence: float }`
   - **Implementation:** Call existing STT service (Whisper, Vosk, etc.)

2. **`reporting_generate_report`**
   - **Input:** `{ study_id, findings: str, impression: str, radiologist_id }`
   - **Output:** `{ report_id, pdf_url }`

3. **`reporting_get_report`**
   - **Input:** `{ report_id }`
   - **Output:** Full report with metadata

4. **`reporting_search_reports`**
   - **Input:** `{ patient_id?, date_range?, keyword? }`
   - **Output:** List of matching reports

**Adapter Implementation:**
```python
# adapters/reporting_adapter.py
class ReportingAdapter(ModuleAdapter):
    def __init__(self, reporting_api_url: str, db_path: str):
        self.api_url = reporting_api_url
        self.db = sqlite3.connect(db_path)
    
    async def invoke_tool(self, tool_name, params):
        if tool_name == "reporting_transcribe_audio":
            # Forward to existing /api/transcribe endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/transcribe",
                    files={"audio": params["audio_data"]}
                )
                return response.json()
        
        elif tool_name == "reporting_generate_report":
            # Store in medical_reporting.db
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO reports (study_id, findings, impression, radiologist_id, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (params["study_id"], params["findings"], params["impression"], params["radiologist_id"]))
            self.db.commit()
            report_id = cursor.lastrowid
            return {"report_id": report_id}
```

### 4.4 Billing/Accounting Module

**Protocol:** REST API + Database

**Exposed Tools:**

1. **`billing_create_invoice`**
   - **Input:** `{ patient_id, line_items: [{ code, description, amount }] }`
   - **Output:** `{ invoice_id, total_amount, due_date }`

2. **`billing_get_patient_balance`**
   - **Input:** `{ patient_id }`
   - **Output:** `{ outstanding_balance, last_payment_date }`

3. **`billing_submit_claim`**
   - **Input:** `{ patient_id, insurance_id, procedure_codes: [] }`
   - **Output:** `{ claim_id, status: "submitted"|"pending"|"approved"|"denied" }`

4. **`billing_reconcile_payment`**
   - **Input:** `{ invoice_id, payment_amount, payment_method }`
   - **Output:** `{ receipt_id, remaining_balance }`

**Adapter Implementation:**
```python
# adapters/billing_adapter.py
class BillingAdapter(ModuleAdapter):
    def __init__(self, billing_api_url: str):
        self.api_url = billing_api_url
    
    async def invoke_tool(self, tool_name, params):
        async with httpx.AsyncClient() as client:
            if tool_name == "billing_create_invoice":
                response = await client.post(
                    f"{self.api_url}/invoices",
                    json=params
                )
                return response.json()
            # ... other tools
```

---

## 5. Lightweight Offline LLM Selection

### 5.1 Evaluation Criteria

| Criterion | Weight | Measurement |
|-----------|--------|-------------|
| **Inference Speed** | 30% | Tokens/second on target hardware (CPU) |
| **Accuracy** | 25% | Medical NLU benchmarks (MedQA, PubMedQA) |
| **Tool Calling Support** | 20% | Native function calling vs. prompt engineering |
| **Memory Footprint** | 15% | RAM usage during inference |
| **Licensing** | 10% | Commercial use allowed, no API restrictions |

### 5.2 Recommended Model: **Mistral 7B Instruct v0.2**

**Rationale:**
- Excellent instruction-following and JSON output formatting
- Native support for function calling (when prompted correctly)
- Permissive Apache 2.0 license
- Quantized GGUF models run efficiently on CPU (10-15 tok/s on modern Intel/AMD)
- Active community and Ollama integration

**Deployment:**
```bash
# Using Ollama
ollama pull mistral:7b-instruct-q4_K_M

# Using llama.cpp
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
./llama-server -m mistral-7b-instruct-v0.2.Q4_K_M.gguf --port 8080 --ctx-size 4096
```

### 5.3 Alternative Models

1. **Llama 3.1 8B Instruct** (if more RAM available, better reasoning)
2. **Phi-3 Medium (14B)** (Microsoft, ONNX-optimized, good for Windows deployments)
3. **Gemma 2 9B** (Google, very efficient for tool use)

### 5.4 Hardware Requirements

**Minimum (CPU-only):**
- **CPU:** 8-core Intel Xeon / AMD EPYC (AVX2 support required)
- **RAM:** 16 GB (8 GB for model, 4 GB OS, 4 GB buffers)
- **Storage:** 10 GB SSD for model files
- **Inference Speed:** 10-15 tokens/second

**Recommended (GPU-accelerated):**
- **GPU:** NVIDIA RTX 4090 / A4000 (16+ GB VRAM) with CUDA 12.x
- **RAM:** 32 GB system RAM
- **Inference Speed:** 50-100 tokens/second

---

## 6. MCP Server API & Tool Definitions

### 6.1 MCP Protocol Overview

The **Model Context Protocol (MCP)** is a standardized way for LLMs to interact with external tools. It defines:
- **Tool Discovery:** List available tools with JSON schemas
- **Tool Invocation:** Execute a tool with validated parameters
- **Streaming Results:** Optional for long-running operations

### 6.2 Core API Endpoints

#### 6.2.1 `GET /mcp/v1/tools`

List all available tools across all modules.

**Response:**
```json
{
  "tools": [
    {
      "name": "pacs_search_studies",
      "description": "Search for DICOM studies in PACS by patient ID, name, date, or modality",
      "parameters": {
        "type": "object",
        "properties": {
          "patient_id": {"type": "string", "description": "Patient identifier"},
          "modality": {"type": "string", "enum": ["CT", "MR", "XR", "US"]},
          "study_date": {"type": "string", "format": "date"}
        }
      }
    },
    {
      "name": "ris_schedule_appointment",
      "description": "Schedule a radiology appointment",
      "parameters": {
        "type": "object",
        "properties": {
          "patient_id": {"type": "string"},
          "modality": {"type": "string"},
          "requested_date": {"type": "string", "format": "date-time"},
          "priority": {"type": "string", "enum": ["routine", "urgent", "stat"]}
        },
        "required": ["patient_id", "modality", "requested_date"]
      }
    }
    // ... all other tools
  ]
}
```

#### 6.2.2 `POST /mcp/v1/invoke`

Execute a specific tool.

**Request:**
```json
{
  "tool": "pacs_search_studies",
  "parameters": {
    "patient_id": "P12345",
    "modality": "CT"
  },
  "context": {
    "user_id": "radiologist_001",
    "session_id": "sess_abc123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "studies": [
      {
        "study_instance_uid": "1.2.840.113619.2.55.3...",
        "study_date": "2025-10-10",
        "modality": "CT",
        "study_description": "CT CHEST W/CONTRAST"
      }
    ]
  },
  "execution_time_ms": 145
}
```

#### 6.2.3 `POST /mcp/v1/chat` (LLM Endpoint)

Unified endpoint for natural language queries (internally routes to LLM + tool invocation).

**Request:**
```json
{
  "message": "Show me all CT scans for patient P12345 from last week",
  "user_id": "radiologist_001"
}
```

**Response:**
```json
{
  "response": "I found 2 CT studies for patient P12345:\n1. CT CHEST W/CONTRAST on 2025-10-10\n2. CT ABDOMEN/PELVIS on 2025-10-08",
  "tool_calls": [
    {
      "tool": "pacs_search_studies",
      "parameters": {"patient_id": "P12345", "modality": "CT", "study_date": "2025-10-07/2025-10-14"}
    }
  ],
  "llm_tokens": 89,
  "total_time_ms": 1250
}
```

### 6.3 Tool Schema Standard

Each tool must provide:
- **`name`**: Unique identifier (snake_case)
- **`description`**: Clear explanation for LLM to understand usage
- **`parameters`**: JSON Schema (OpenAPI 3.0 format)
- **`returns`**: Expected return type schema
- **`examples`**: Sample invocations for few-shot prompting

---

## 7. Security, Authentication & Audit

### 7.1 Threat Model

**Primary Threats:**
1. Unauthorized access to PHI (HIPAA violation)
2. SQL injection / command injection via LLM-generated queries
3. Model prompt injection (malicious user input manipulating LLM behavior)
4. Man-in-the-middle attacks on module communication
5. Insider threats (excessive data access)

### 7.2 Authentication & Authorization

**MCP Server Auth:**
- **JWT tokens** issued by central Identity Provider (Keycloak, Auth0, or custom)
- **mTLS** (mutual TLS) for service-to-service communication between MCP server and adapters
- **API keys** for legacy module integrations (rotated every 90 days)

**Role-Based Access Control (RBAC):**
```yaml
roles:
  - name: radiologist
    permissions:
      - pacs:read
      - pacs:search
      - ris:read
      - reporting:create
      - reporting:read
  
  - name: billing_clerk
    permissions:
      - billing:read
      - billing:create_invoice
      - billing:reconcile_payment
  
  - name: admin
    permissions:
      - "*"  # All tools
```

**Implementation:**
```python
# auth_middleware.py
from fastapi import Request, HTTPException
from jwt import decode, InvalidTokenError

async def verify_token(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = decode(token, SECRET_KEY, algorithms=["HS256"])
        request.state.user = payload
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def check_permission(request: Request, required_permission: str):
    user_permissions = request.state.user.get("permissions", [])
    if required_permission not in user_permissions and "*" not in user_permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
```

### 7.3 Data Protection

**Encryption:**
- **In Transit:** TLS 1.3 for all HTTP connections
- **At Rest:** AES-256 encryption for databases (SQLCipher for SQLite, TDE for PostgreSQL)
- **DICOM Files:** Optional encryption using DICOM Part 15 Security profiles

**PHI Handling:**
- **De-identification:** Automatic redaction of PII in logs (replace patient names with IDs)
- **Audit Logging:** Every tool invocation logged with:
  - User ID
  - Tool name
  - Parameters (sanitized)
  - Timestamp
  - Result status
  - IP address

**Example Audit Log Entry:**
```json
{
  "timestamp": "2025-10-14T10:23:45Z",
  "user_id": "radiologist_001",
  "action": "pacs_search_studies",
  "parameters": {"patient_id": "P12345"},
  "result_status": "success",
  "ip_address": "10.0.1.42",
  "session_id": "sess_abc123"
}
```

### 7.4 LLM Security

**Prompt Injection Prevention:**
1. **Input Sanitization:** Validate all user inputs against whitelist patterns
2. **System Prompt Isolation:** Separate user input from system instructions
3. **Output Validation:** Parse LLM tool calls with strict JSON schema validation
4. **Sandboxing:** Limit tool execution to predefined safe operations (no shell commands)

**Example Safe Prompt Template:**
```
You are a medical assistant AI. You have access to the following tools:
{tool_list}

User request: {user_input}

IMPORTANT: Only use the provided tools. Do not execute arbitrary code or access unauthorized data.

Respond with a JSON object containing the tool name and parameters.
```

---

## 8. Data Flow & Sequence Diagrams

### 8.1 Typical Query Flow

```
User: "Show me yesterday's CT scans for patient P12345"
  │
  ▼
┌────────────────────────┐
│   Web UI / CLI         │
│  (POST /mcp/v1/chat)   │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   MCP Server           │
│  • Auth check          │
│  • Parse query         │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Offline LLM Agent     │
│  • Mistral 7B          │
│  • Generate tool call  │
│    {                   │
│      "tool": "pacs_...",│
│      "params": {...}   │
│    }                   │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   MCP Server           │
│  • Validate params     │
│  • Route to adapter    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   PACS Adapter         │
│  • Query Orthanc       │
│  • DICOMweb QIDO-RS    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   Orthanc PACS         │
│  • Return study list   │
└────────┬───────────────┘
         │
         ▼ (Results bubble back up)
┌────────────────────────┐
│   LLM Agent            │
│  • Format response     │
│  "Found 3 CT studies..." │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   User                 │
│  • Display results     │
└────────────────────────┘
```

### 8.2 Multi-Tool Orchestration Example

**User:** "Schedule a CT scan for patient P12345 tomorrow and send the appointment details to Dr. Smith"

**LLM Planning:**
1. Check patient availability → `ris_get_worklist`
2. Schedule appointment → `ris_schedule_appointment`
3. Retrieve physician contact → `ris_get_referring_physician`
4. (Optional) Send notification → External email service

**Sequence:**
```
LLM → ris_get_worklist(date="2025-10-15", modality="CT")
     ← Available slots: [09:00, 14:00, 16:00]

LLM → ris_schedule_appointment(patient_id="P12345", modality="CT", requested_date="2025-10-15T09:00")
     ← {appointment_id: 987, scheduled_time: "2025-10-15T09:00", room: "CT-1"}

LLM → ris_get_referring_physician(physician_id="DOC001")
     ← {name: "Dr. Smith", email: "smith@hospital.org"}

LLM → (External) Send email notification
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Adapter Tests:**
- Mock each module's backend (Orthanc, RIS DB, etc.)
- Verify correct API calls and error handling
- Test parameter validation

**Example (pytest):**
```python
# tests/test_pacs_adapter.py
import pytest
from unittest.mock import AsyncMock
from adapters.pacs_adapter import OrthancPACSAdapter

@pytest.mark.asyncio
async def test_search_studies_success():
    adapter = OrthancPACSAdapter("http://localhost:8042", "orthanc", "orthanc")
    adapter.client.get = AsyncMock(return_value=MockResponse([
        {"StudyInstanceUID": "1.2.3", "PatientID": "P12345"}
    ]))
    
    result = await adapter.invoke_tool("pacs_search_studies", {"patient_id": "P12345"})
    assert len(result) == 1
    assert result[0]["PatientID"] == "P12345"
```

### 9.2 Integration Tests

**MCP Server → Adapter → Real Module:**
- Spin up test instances of Orthanc, PostgreSQL RIS, etc. (Docker Compose)
- Execute end-to-end tool invocations
- Verify data consistency

**Example (Docker Compose):**
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  orthanc:
    image: jodogne/orthanc-plugins:latest
    ports:
      - "8042:8042"
  
  ris-db:
    image: postgres:15
    environment:
      POSTGRES_DB: ris_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
  
  mcp-server:
    build: .
    depends_on:
      - orthanc
      - ris-db
    environment:
      ORTHANC_URL: http://orthanc:8042
      RIS_DB_URL: postgresql://test:test@ris-db/ris_test
```

### 9.3 LLM Evaluation Tests

**Tool Invocation Accuracy:**
- Provide 100 sample queries (e.g., "Find all MRI scans for patient X")
- Measure:
  - Correct tool selection rate
  - Parameter extraction accuracy
  - JSON formatting validity

**Benchmark:**
```python
# tests/test_llm_tool_calling.py
test_cases = [
    {
        "query": "Show me CT scans for patient P12345 from last week",
        "expected_tool": "pacs_search_studies",
        "expected_params": {"patient_id": "P12345", "modality": "CT", "study_date": "..."}
    },
    # ... 99 more cases
]

def test_llm_accuracy():
    correct = 0
    for case in test_cases:
        llm_output = llm_agent.invoke(case["query"])
        if llm_output["tool"] == case["expected_tool"]:
            correct += 1
    
    accuracy = correct / len(test_cases)
    assert accuracy >= 0.90  # 90% threshold
```

### 9.4 Security Testing

- **Penetration Testing:** Simulate prompt injection attacks
- **Fuzz Testing:** Random inputs to tool parameters
- **Access Control Tests:** Verify RBAC enforcement

---

## 10. Deployment & Infrastructure

### 10.1 Containerized Deployment

**Docker Image Structure:**
```
mcp-server/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── server/
│   ├── main.py
│   ├── tool_registry.py
│   └── adapters/
│       ├── pacs_adapter.py
│       ├── ris_adapter.py
│       ├── reporting_adapter.py
│       └── billing_adapter.py
└── models/
    └── mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install llama.cpp dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY models/ ./models/

# Download llama.cpp if not bundled
RUN pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./config:/app/config
    environment:
      - ORTHANC_URL=http://orthanc:8042
      - RIS_DB_URL=postgresql://user:pass@ris-db:5432/ris
      - REPORTING_API_URL=http://reporting:5000
      - BILLING_API_URL=http://billing:3000
      - MODEL_PATH=/app/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
    depends_on:
      - orthanc
      - ris-db
      - reporting
      - billing
  
  orthanc:
    image: jodogne/orthanc-plugins:latest
    ports:
      - "8042:8042"
    volumes:
      - orthanc-data:/var/lib/orthanc/db
  
  ris-db:
    image: postgres:15
    environment:
      POSTGRES_DB: ris
      POSTGRES_USER: ris_user
      POSTGRES_PASSWORD: ${RIS_DB_PASSWORD}
    volumes:
      - ris-data:/var/lib/postgresql/data
  
  reporting:
    build: ./medical-reporting-module
    ports:
      - "5000:5000"
  
  billing:
    build: ./billing-module
    ports:
      - "3000:3000"

volumes:
  orthanc-data:
  ris-data:
```

### 10.2 Kubernetes Deployment

**Key Manifests:**
- **Deployment:** MCP server with HPA (Horizontal Pod Autoscaler) based on CPU/memory
- **Service:** ClusterIP for internal communication, LoadBalancer for external access
- **ConfigMap:** Environment variables for module URLs
- **Secret:** Database credentials, API keys

**Example HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 10.3 Resource Requirements

**Per MCP Server Instance:**
- **CPU:** 4 cores (8 threads)
- **RAM:** 12 GB (8 GB for LLM, 4 GB for app)
- **Storage:** 15 GB (model + logs)
- **Network:** 1 Gbps (for DICOM transfers)

**Scaling:**
- Start with 2 replicas for HA
- Auto-scale based on request rate (target: 50 req/min per pod)
- Use dedicated GPU nodes if available (reduce replicas, increase throughput)

---

## 11. Developer Documentation & SDKs

### 11.1 Adapter Development Guide

**Creating a New Adapter:**

1. **Inherit from `ModuleAdapter`:**
```python
from abc import ABC, abstractmethod

class MyCustomAdapter(ModuleAdapter):
    async def initialize(self, config: dict):
        # Setup connection to your module
        pass
    
    async def invoke_tool(self, tool_name: str, params: dict) -> dict:
        # Route to specific tool implementation
        if tool_name == "my_tool":
            return await self._my_tool(**params)
    
    async def health_check(self) -> bool:
        # Verify module is reachable
        return True
```

2. **Register Tools:**
```python
# In tool_registry.py
from adapters.my_custom_adapter import MyCustomAdapter

registry.register_adapter(
    "my_module",
    MyCustomAdapter(config={...}),
    tools=[
        {
            "name": "my_tool",
            "description": "Does something useful",
            "parameters": {...}
        }
    ]
)
```

3. **Write Tests:**
```python
@pytest.mark.asyncio
async def test_my_tool():
    adapter = MyCustomAdapter(config=TEST_CONFIG)
    result = await adapter.invoke_tool("my_tool", {"param1": "value"})
    assert result["status"] == "success"
```

### 11.2 Python SDK for Tool Invocation

**Installation:**
```bash
pip install mcp-client-sdk
```

**Usage:**
```python
from mcp_client import MCPClient

client = MCPClient(
    base_url="http://mcp-server:8000",
    api_key="your-api-key"
)

# List available tools
tools = client.list_tools()

# Invoke a tool
result = client.invoke_tool(
    tool_name="pacs_search_studies",
    parameters={"patient_id": "P12345", "modality": "CT"}
)

print(result)
# {'studies': [{'study_instance_uid': '...', ...}]}
```

### 11.3 JavaScript/TypeScript SDK

```typescript
// npm install @mcp/client
import { MCPClient } from '@mcp/client';

const client = new MCPClient({
  baseURL: 'http://mcp-server:8000',
  apiKey: process.env.MCP_API_KEY
});

const studies = await client.invokeTool('pacs_search_studies', {
  patient_id: 'P12345',
  modality: 'CT'
});

console.log(studies);
```

---

## 12. POC Roadmap & Milestones

### Phase 1: Foundation (Weeks 1-4)

**Milestone 1.1: MCP Server Core (Week 1-2)**
- [ ] Setup FastAPI server with tool registry
- [ ] Implement authentication middleware (JWT)
- [ ] Create health check and /tools endpoint
- [ ] Write unit tests for core router
- **Success Criteria:** Server responds to /mcp/v1/tools with empty list

**Milestone 1.2: PACS Adapter (Week 3)**
- [ ] Implement `OrthancPACSAdapter`
- [ ] Add `pacs_search_studies` tool
- [ ] Integration test with local Orthanc instance
- **Success Criteria:** Can search and retrieve study metadata via API

**Milestone 1.3: LLM Integration (Week 4)**
- [ ] Setup llama.cpp with Mistral 7B
- [ ] Create prompt templates for tool calling
- [ ] Implement `/mcp/v1/chat` endpoint with basic query handling
- **Success Criteria:** LLM can correctly invoke `pacs_search_studies` from natural language

### Phase 2: Multi-Module Integration (Weeks 5-8)

**Milestone 2.1: RIS Adapter (Week 5)**
- [ ] Implement `RISAdapter` with PostgreSQL connection
- [ ] Add `ris_schedule_appointment` and `ris_get_worklist` tools
- [ ] Test appointment scheduling flow
- **Success Criteria:** LLM can schedule appointments via natural language

**Milestone 2.2: Reporting Adapter (Week 6)**
- [ ] Integrate existing medical reporting module
- [ ] Implement `reporting_transcribe_audio` and `reporting_generate_report`
- [ ] Test voice transcription → report generation pipeline
- **Success Criteria:** End-to-end voice report creation working

**Milestone 2.3: Billing Adapter (Week 7)**
- [ ] Implement `BillingAdapter`
- [ ] Add invoice creation and payment reconciliation tools
- [ ] **Success Criteria:** LLM can generate billing summaries

**Milestone 2.4: Integration Testing (Week 8)**
- [ ] Cross-module workflows (e.g., schedule → perform → report → bill)
- [ ] Load testing (100 concurrent users)
- [ ] Security audit (penetration testing)

### Phase 3: Production Readiness (Weeks 9-12)

**Milestone 3.1: Monitoring & Observability (Week 9)**
- [ ] Integrate Prometheus metrics
- [ ] Setup Grafana dashboards (request rate, latency, error rate)
- [ ] Implement distributed tracing (Jaeger/Zipkin)

**Milestone 3.2: High Availability (Week 10)**
- [ ] Kubernetes deployment with 3 replicas
- [ ] Database connection pooling and failover
- [ ] Load balancer configuration (NGINX/HAProxy)

**Milestone 3.3: Documentation & Training (Week 11)**
- [ ] User manual for radiologists/clinicians
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Video tutorials for common workflows

**Milestone 3.4: Pilot Deployment (Week 12)**
- [ ] Deploy to production environment (limited users)
- [ ] Collect feedback and iterate
- [ ] Final security and compliance review (HIPAA)

---

## 13. Risk Assessment & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **LLM hallucination leading to incorrect tool calls** | High | High | Implement strict JSON schema validation, add human-in-the-loop confirmation for critical operations (e.g., deleting studies) |
| **Model too slow for real-time use** | Medium | High | Use quantized models (Q4_K_M), optimize prompt size, consider GPU acceleration |
| **Data breach via prompt injection** | Medium | Critical | Input sanitization, output validation, sandboxed tool execution, regular security audits |
| **Module API downtime** | Medium | Medium | Implement circuit breakers (e.g., Polly, resilience4j), retry logic with exponential backoff, cache frequently accessed data |
| **HIPAA compliance failure** | Low | Critical | Engage legal/compliance team early, conduct third-party audit, implement comprehensive audit logging |
| **LLM model drift over time** | Low | Medium | Version control models, regression testing suite, monitor accuracy metrics in production |

---

## 14. Appendices

### Appendix A: Sample Tool Definitions (Full JSON Schema)

```json
{
  "name": "pacs_search_studies",
  "description": "Search for DICOM studies in the PACS (Orthanc) by various criteria",
  "parameters": {
    "type": "object",
    "properties": {
      "patient_id": {
        "type": "string",
        "description": "Patient identifier (e.g., MRN)",
        "pattern": "^[A-Z0-9]{5,10}$"
      },
      "patient_name": {
        "type": "string",
        "description": "Patient name (Last^First format)"
      },
      "study_date": {
        "type": "string",
        "description": "Study date or date range (YYYYMMDD or YYYYMMDD-YYYYMMDD)",
        "pattern": "^\\d{8}(-\\d{8})?$"
      },
      "modality": {
        "type": "string",
        "description": "Imaging modality",
        "enum": ["CT", "MR", "XR", "US", "NM", "PT", "MG"]
      },
      "accession_number": {
        "type": "string",
        "description": "Unique study accession number"
      }
    },
    "anyOf": [
      {"required": ["patient_id"]},
      {"required": ["accession_number"]}
    ]
  },
  "returns": {
    "type": "object",
    "properties": {
      "studies": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "study_instance_uid": {"type": "string"},
            "patient_id": {"type": "string"},
            "patient_name": {"type": "string"},
            "study_date": {"type": "string"},
            "modality": {"type": "string"},
            "study_description": {"type": "string"},
            "number_of_series": {"type": "integer"},
            "number_of_instances": {"type": "integer"}
          }
        }
      }
    }
  },
  "examples": [
    {
      "query": "Find all CT scans for patient P12345",
      "invocation": {
        "tool": "pacs_search_studies",
        "parameters": {"patient_id": "P12345", "modality": "CT"}
      }
    }
  ]
}
```

### Appendix B: LLM Prompt Templates

**System Prompt:**
```
You are UbuntuCare AI, a medical assistant with access to hospital information systems. You can:

1. Search for patient imaging studies (PACS)
2. Schedule radiology appointments (RIS)
3. Generate medical reports (Reporting)
4. Process billing and payments (Billing)

When a user asks a question, analyze the request and determine which tools to use. Always:
- Confirm patient identity before accessing medical records
- Use the most specific tool for the task
- Return structured data in JSON format

Available tools:
{tool_schemas}

Respond ONLY with valid JSON in this format:
{
  "reasoning": "Brief explanation of your approach",
  "tool_calls": [
    {
      "tool": "tool_name",
      "parameters": {...}
    }
  ]
}
```

**Few-Shot Examples:**
```
User: Show me CT scans for patient P12345 from last week
Assistant: {
  "reasoning": "User wants to search PACS for CT studies in a specific date range",
  "tool_calls": [
    {
      "tool": "pacs_search_studies",
      "parameters": {
        "patient_id": "P12345",
        "modality": "CT",
        "study_date": "20251007-20251014"
      }
    }
  ]
}

User: Schedule a brain MRI for patient P67890 tomorrow morning
Assistant: {
  "reasoning": "User wants to schedule an appointment, need to use RIS scheduling tool",
  "tool_calls": [
    {
      "tool": "ris_schedule_appointment",
      "parameters": {
        "patient_id": "P67890",
        "modality": "MR",
        "requested_date": "2025-10-15T09:00:00",
        "priority": "routine"
      }
    }
  ]
}
```

### Appendix C: Database Schemas

**Audit Log Table (PostgreSQL):**
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(50) NOT NULL,
    user_role VARCHAR(50),
    action VARCHAR(100) NOT NULL,  -- Tool name
    parameters JSONB,  -- Sanitized parameters
    result_status VARCHAR(20),  -- success, error, timeout
    error_message TEXT,
    ip_address INET,
    session_id VARCHAR(100),
    execution_time_ms INTEGER
);

CREATE INDEX idx_audit_user_time ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_action ON audit_log(action, timestamp DESC);
```

### Appendix D: Performance Benchmarks

**Target Latencies (99th percentile):**
- Tool invocation (no LLM): < 200ms
- LLM inference (simple query): < 2s
- LLM inference (complex multi-tool): < 5s
- PACS search: < 500ms
- RIS appointment scheduling: < 300ms
- Report generation: < 1s

**Load Testing Results (Expected):**
- **Concurrent Users:** 100
- **Requests/Second:** 50 (1 req/2s per user)
- **Success Rate:** > 99.5%
- **Mean Response Time:** 1.2s
- **CPU Usage:** 60-70% (4 cores)
- **RAM Usage:** 10 GB

---

## Next Steps

1. **Review and Approve:** Stakeholder sign-off on architecture and scope
2. **Environment Setup:** Provision dev/test servers, install dependencies
3. **Sprint Planning:** Break milestones into 2-week sprints with defined user stories
4. **Prototype Development:** Start with Phase 1 Milestone 1.1 (MCP Server Core)
5. **Weekly Demos:** Show progress to clinical stakeholders for early feedback

---

**Document Owner:** AI Systems Team  
**Last Updated:** October 14, 2025  
**Approved By:** [Pending]  
**Next Review Date:** November 1, 2025
