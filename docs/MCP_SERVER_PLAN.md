# 🏥 MCP Server for Medical Dictation & Orthanc PACS Integration

**Model Context Protocol Server with Lightweight LLM for Medical Workflows**

---

## 🎯 Overview

This document outlines the implementation of an MCP (Model Context Protocol) server that provides:
1. **Medical Dictation Tools** - Voice-to-text with medical terminology
2. **Orthanc PACS Wrappers** - Complete DICOM operations via MCP
3. **Lightweight LLM Integration** - Offline medical AI with online fallback
4. **Smart Context Management** - Patient-aware medical assistance

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Architecture                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Kiro IDE / MCP Client                                           │
│  ├─ Medical dictation commands                                   │
│  ├─ PACS query/retrieve                                          │
│  └─ Report generation assistance                                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓ MCP Protocol
┌──────────────────────────────────────────────────────────────────┐
│  MCP Server (Python)                                             │
│  ├─ Tool Registry                                                │
│  ├─ Context Management                                           │
│  └─ Resource Providers                                           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┴─────────────────────┐
        ↓                     ↓                      ↓
┌───────────────┐   ┌──────────────────┐   ┌────────────────┐
│ Medical       │   │ Orthanc PACS     │   │ LLM Engine     │
│ Dictation     │   │ Connector        │   │ (Hybrid)       │
│               │   │                  │   │                │
│ • Whisper AI  │   │ • C-FIND         │   │ • Offline:     │
│ • Medical     │   │ • C-MOVE         │   │   Llama 3.2    │
│   Terminology │   │ • C-STORE        │   │   (3B params)  │
│ • Templates   │   │ • DICOMweb       │   │                │
│ • ICD-10      │   │ • Study Mgmt     │   │ • Online:      │
│               │   │ • Patient Search │   │   GPT-4/Claude │
└───────────────┘   └──────────────────┘   └────────────────┘
```

---

## 📋 MCP Tools Specification

### Category 1: Medical Dictation Tools

#### 1.1 `dictate_medical_report`
**Purpose:** Transcribe voice to medical report with terminology recognition

**Parameters:**
```json
{
  "audio_file": "string (path or base64)",
  "report_type": "enum (radiology, pathology, clinical_note)",
  "patient_id": "string (optional)",
  "study_id": "string (optional)",
  "template": "string (optional)",
  "language": "enum (en-ZA, af-ZA, en-US)"
}
```

**Returns:**
```json
{
  "transcription": "string",
  "medical_terms": ["array of recognized terms"],
  "icd10_suggestions": ["array of ICD-10 codes"],
  "confidence": "float (0-1)",
  "processing_time_ms": "integer"
}
```

**Implementation:**
- Uses Whisper AI (medium model for accuracy)
- Medical terminology post-processing
- ICD-10 code extraction
- South African medical context

---

#### 1.2 `enhance_medical_text`
**Purpose:** Improve medical report text with LLM assistance

**Parameters:**
```json
{
  "text": "string",
  "enhancement_type": "enum (grammar, terminology, structure, completeness)",
  "specialty": "enum (radiology, pathology, general)",
  "use_online_llm": "boolean (default: false)"
}
```

**Returns:**
```json
{
  "enhanced_text": "string",
  "changes": ["array of changes made"],
  "suggestions": ["array of additional suggestions"],
  "model_used": "string (llama-3.2-3b or gpt-4)"
}
```

---

#### 1.3 `generate_report_from_template`
**Purpose:** Generate structured report from template and findings

**Parameters:**
```json
{
  "template_name": "string",
  "findings": "object (key-value pairs)",
  "patient_context": "object (optional)",
  "study_context": "object (optional)"
}
```

**Returns:**
```json
{
  "report": "string (formatted report)",
  "sections": "object (report sections)",
  "missing_fields": ["array of required fields not provided"]
}
```

---

#### 1.4 `suggest_icd10_codes`
**Purpose:** Suggest ICD-10 codes from clinical text

**Parameters:**
```json
{
  "clinical_text": "string",
  "specialty": "string (optional)",
  "max_suggestions": "integer (default: 5)"
}
```

**Returns:**
```json
{
  "suggestions": [
    {
      "code": "string",
      "description": "string",
      "confidence": "float",
      "category": "string"
    }
  ]
}
```

---

### Category 2: Orthanc PACS Tools

#### 2.1 `pacs_find_patients`
**Purpose:** Search for patients in PACS

**Parameters:**
```json
{
  "patient_id": "string (optional)",
  "patient_name": "string (optional)",
  "date_range": "object (optional)",
  "modality": "string (optional)",
  "limit": "integer (default: 50)"
}
```

**Returns:**
```json
{
  "patients": [
    {
      "patient_id": "string",
      "patient_name": "string",
      "date_of_birth": "string",
      "sex": "string",
      "study_count": "integer"
    }
  ],
  "total_count": "integer"
}
```

---

#### 2.2 `pacs_find_studies`
**Purpose:** Search for DICOM studies

**Parameters:**
```json
{
  "patient_id": "string (optional)",
  "study_date": "string (optional)",
  "modality": "string (optional)",
  "study_description": "string (optional)",
  "accession_number": "string (optional)"
}
```

**Returns:**
```json
{
  "studies": [
    {
      "study_instance_uid": "string",
      "study_date": "string",
      "study_time": "string",
      "modality": "string",
      "study_description": "string",
      "number_of_series": "integer",
      "number_of_instances": "integer",
      "orthanc_id": "string"
    }
  ]
}
```

---

#### 2.3 `pacs_get_study_details`
**Purpose:** Get detailed information about a study

**Parameters:**
```json
{
  "study_id": "string (Orthanc ID or StudyInstanceUID)"
}
```

**Returns:**
```json
{
  "study": "object (complete DICOM metadata)",
  "series": ["array of series"],
  "patient": "object (patient info)",
  "statistics": "object (size, instance count)"
}
```

---

#### 2.4 `pacs_retrieve_images`
**Purpose:** Retrieve DICOM images for viewing

**Parameters:**
```json
{
  "study_id": "string",
  "series_id": "string (optional)",
  "format": "enum (dicom, jpeg, png)",
  "quality": "enum (preview, diagnostic)"
}
```

**Returns:**
```json
{
  "images": [
    {
      "instance_id": "string",
      "url": "string (download URL)",
      "thumbnail_url": "string",
      "metadata": "object"
    }
  ]
}
```

---

#### 2.5 `pacs_store_study`
**Purpose:** Store DICOM study to Orthanc

**Parameters:**
```json
{
  "dicom_files": "array (file paths or base64)",
  "patient_id": "string",
  "study_description": "string (optional)"
}
```

**Returns:**
```json
{
  "success": "boolean",
  "study_id": "string (Orthanc ID)",
  "instances_stored": "integer",
  "errors": ["array of errors if any"]
}
```

---

#### 2.6 `pacs_anonymize_study`
**Purpose:** Anonymize DICOM study for research/sharing

**Parameters:**
```json
{
  "study_id": "string",
  "anonymization_profile": "enum (basic, research, teaching)",
  "keep_fields": ["array of DICOM tags to preserve"]
}
```

**Returns:**
```json
{
  "anonymized_study_id": "string",
  "original_study_id": "string",
  "mapping": "object (field mappings)"
}
```

---

#### 2.7 `pacs_export_study`
**Purpose:** Export study to external destination

**Parameters:**
```json
{
  "study_id": "string",
  "destination": "enum (dicom_node, file_system, cloud)",
  "destination_config": "object",
  "format": "enum (dicom, dicomdir, zip)"
}
```

**Returns:**
```json
{
  "success": "boolean",
  "export_path": "string",
  "file_size_mb": "float"
}
```

---

### Category 3: Medical Scheme Authorization Tools (CRITICAL)

#### 3.1 `create_preauth_request`
**Purpose:** Create medical scheme pre-authorization request with validation

**Parameters:**
```json
{
  "patient_id": "string",
  "member_number": "string",
  "scheme_code": "string",
  "procedure_code": "string (NRPL code)",
  "clinical_indication": "string",
  "icd10_codes": "array of strings",
  "urgency": "enum (routine, urgent, emergency)",
  "supporting_documents": "array of file paths (optional)"
}
```

**Returns:**
```json
{
  "preauth_id": "string",
  "status": "enum (queued, submitted, approved, rejected)",
  "estimated_approval_time": "string",
  "approval_probability": "float (0-1)",
  "validation_passed": "boolean",
  "missing_info": "array of strings",
  "next_steps": "array of strings"
}
```

**Features:**
- ✅ Validates member number against offline database
- ✅ Checks if procedure requires pre-auth
- ✅ Validates ICD-10 codes
- ✅ Estimates approval probability using AI
- ✅ Queues for submission when online
- ✅ Auto-fills forms from patient context

**Permissions Required:** `create_preauth` (Receptionist, Doctor, Admin)

---

#### 3.2 `validate_preauth_requirements`
**Purpose:** Check if procedure requires pre-auth and what's needed (offline)

**Parameters:**
```json
{
  "scheme_code": "string",
  "plan_code": "string",
  "procedure_code": "string (NRPL code)"
}
```

**Returns:**
```json
{
  "requires_preauth": "boolean",
  "required_documents": "array of strings",
  "typical_turnaround": "string",
  "approval_rate": "float (0-1)",
  "alternative_procedures": [
    {
      "code": "string",
      "name": "string",
      "requires_preauth": "boolean",
      "cost_difference": "float"
    }
  ]
}
```

**Features:**
- ✅ Works completely offline
- ✅ Returns results in < 100ms
- ✅ Suggests alternatives if pre-auth required
- ✅ Shows historical approval rates

**Permissions Required:** `view_benefits` (All roles)

---

#### 3.3 `check_preauth_status`
**Purpose:** Check status of pre-authorization request

**Parameters:**
```json
{
  "preauth_id": "string"
}
```

**Returns:**
```json
{
  "preauth_id": "string",
  "status": "enum (pending, approved, rejected, expired)",
  "auth_number": "string (if approved)",
  "valid_until": "string (ISO date)",
  "rejection_reason": "string (if rejected)",
  "last_updated": "string (ISO datetime)"
}
```

**Features:**
- ✅ Real-time status check (if online)
- ✅ Shows last known status (if offline)
- ✅ Automatic notifications on status change

**Permissions Required:** `view_preauth` (Receptionist, Doctor, Admin)

---

#### 3.4 `estimate_patient_cost`
**Purpose:** Calculate patient portion for procedure (works offline)

**Parameters:**
```json
{
  "member_number": "string",
  "scheme_code": "string",
  "procedure_code": "string (NRPL code)",
  "include_utilization": "boolean (default: true)"
}
```

**Returns:**
```json
{
  "procedure_cost": "float",
  "medical_aid_portion": "float",
  "patient_portion": "float",
  "co_payment_percentage": "float",
  "annual_limit": "float",
  "used_this_year": "float",
  "remaining_benefit": "float",
  "preauth_required": "boolean",
  "confidence": "enum (high, medium, low)",
  "last_updated": "string (ISO date)"
}
```

**Features:**
- ✅ Calculates from offline benefits database
- ✅ Includes member utilization
- ✅ Shows remaining annual limits
- ✅ Indicates confidence level

**Permissions Required:** `view_costs` (Receptionist, Doctor, Admin)

---

### Category 4: Doctor Workflow Tools (EFFICIENCY)

#### 4.1 `smart_report_assistant`
**Purpose:** AI-powered report writing assistant

**Parameters:**
```json
{
  "study_id": "string (Orthanc ID)",
  "voice_input": "string (transcribed voice, optional)",
  "report_type": "enum (normal, abnormal, critical)",
  "auto_complete": "boolean (default: true)",
  "use_online_llm": "boolean (default: false)"
}
```

**Returns:**
```json
{
  "report": {
    "clinical_indication": "string",
    "technique": "string",
    "findings": "string",
    "impression": "array of strings",
    "icd10_codes": "array of strings",
    "completion_percentage": "integer (0-100)",
    "quality_score": "float (0-1)"
  },
  "suggestions": "array of strings",
  "time_saved_seconds": "integer",
  "ai_confidence": "float (0-1)"
}
```

**Features:**
- ✅ Analyzes DICOM images with AI
- ✅ Auto-completes report sections
- ✅ Validates medical terminology
- ✅ Suggests ICD-10 codes
- ✅ Works offline with Llama 3.2

**Permissions Required:** `create_report` (Doctor, Admin)

---

#### 4.2 `quick_actions`
**Purpose:** Execute common actions with one command

**Parameters:**
```json
{
  "action": "enum (normal_study, critical_finding, request_comparison, send_to_referring_doctor, schedule_followup)",
  "study_id": "string",
  "context": "object (optional)"
}
```

**Returns:**
```json
{
  "success": "boolean",
  "actions_performed": "array of strings",
  "notifications_sent": "array of objects",
  "next_steps": "array of strings"
}
```

**Features:**
- ✅ One-click common workflows
- ✅ Auto-fills all required fields
- ✅ Executes multiple steps atomically
- ✅ Notifies relevant parties

**Permissions Required:** `execute_workflow` (Doctor, Admin)

---

#### 4.3 `intelligent_worklist`
**Purpose:** AI-prioritized worklist with smart suggestions

**Parameters:**
```json
{
  "radiologist_id": "string (optional)",
  "sort_by": "enum (urgency, age, complexity, ai_priority)",
  "filter": "object (optional)"
}
```

**Returns:**
```json
{
  "worklist": [
    {
      "workflow_id": "string",
      "patient_name": "string",
      "study_description": "string",
      "priority": "string",
      "age_minutes": "integer",
      "estimated_reading_time": "integer",
      "ai_priority_score": "float",
      "has_comparison": "boolean",
      "critical_flags": "array of strings"
    }
  ],
  "summary": {
    "total_studies": "integer",
    "urgent_count": "integer",
    "estimated_total_time": "integer"
  }
}
```

**Features:**
- ✅ AI-based prioritization
- ✅ Groups similar studies
- ✅ Estimates reading time
- ✅ Flags critical findings

**Permissions Required:** `view_worklist` (Doctor, Admin)

---

#### 4.4 `voice_command_executor`
**Purpose:** Execute commands via natural language

**Parameters:**
```json
{
  "command": "string (natural language)",
  "context": "object (current study, patient, etc.)"
}
```

**Returns:**
```json
{
  "understood": "boolean",
  "action_taken": "string",
  "result": "object",
  "voice_response": "string (optional)"
}
```

**Features:**
- ✅ Natural language understanding
- ✅ Context-aware execution
- ✅ Voice feedback
- ✅ Learns doctor preferences

**Permissions Required:** Based on command (dynamic)

---

### Category 5: Workflow Integration Tools

#### 5.1 `create_radiology_workflow`
**Purpose:** Create new radiology workflow instance

**Parameters:**
```json
{
  "patient_id": "string",
  "study_type": "string",
  "priority": "enum (routine, urgent, stat)",
  "referring_physician": "string",
  "clinical_indication": "string"
}
```

**Returns:**
```json
{
  "workflow_id": "string",
  "status": "string",
  "estimated_completion": "string (ISO datetime)"
}
```

**Permissions Required:** `create_workflow` (Receptionist, Doctor, Admin)

---

#### 5.2 `link_study_to_workflow`
**Purpose:** Link DICOM study to workflow

**Parameters:**
```json
{
  "workflow_id": "string",
  "study_id": "string (Orthanc ID)"
}
```

**Permissions Required:** `modify_workflow` (Technologist, Doctor, Admin)

---

## 🤖 Lightweight LLM Integration

### Offline LLM: Llama 3.2 3B

**Why Llama 3.2 3B:**
- Small enough to run on CPU (3GB RAM)
- Fast inference (< 1 second per response)
- Good medical knowledge from training
- Can be fine-tuned on medical data
- Runs completely offline

**Use Cases:**
- Grammar correction
- Report structure suggestions
- Medical terminology validation
- Template filling
- Basic clinical reasoning

**Implementation:**
```python
from llama_cpp import Llama

class OfflineMedicalLLM:
    def __init__(self, model_path="models/llama-3.2-3b-instruct.gguf"):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,  # Context window
            n_threads=4,  # CPU threads
            n_gpu_layers=0  # CPU only
        )
        
    def enhance_medical_text(self, text, task="grammar"):
        prompt = f"""You are a medical writing assistant. 
Task: {task}
Original text: {text}

Provide improved version:"""
        
        response = self.llm(
            prompt,
            max_tokens=512,
            temperature=0.3,  # Low temperature for consistency
            stop=["</s>", "\n\n"]
        )
        
        return response['choices'][0]['text']
```

---

### Online LLM: GPT-4 / Claude (Fallback)

**When to use online:**
- Complex clinical reasoning
- Differential diagnosis
- Research literature search
- Advanced report generation
- Second opinion validation

**Implementation:**
```python
import openai
from anthropic import Anthropic

class OnlineMedicalLLM:
    def __init__(self):
        self.openai_client = openai.OpenAI()
        self.anthropic_client = Anthropic()
        
    def generate_report(self, findings, context, use_claude=False):
        prompt = f"""Generate a radiology report based on:
Findings: {findings}
Patient Context: {context}

Format as structured radiology report."""
        
        if use_claude:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        else:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
```

---

### Hybrid Strategy

```python
class HybridMedicalLLM:
    def __init__(self):
        self.offline_llm = OfflineMedicalLLM()
        self.online_llm = OnlineMedicalLLM()
        self.internet_available = self.check_internet()
        
    def process_request(self, text, task, prefer_online=False):
        # Simple tasks always use offline
        if task in ['grammar', 'spelling', 'formatting']:
            return self.offline_llm.enhance_medical_text(text, task)
        
        # Complex tasks prefer online if available
        if prefer_online and self.internet_available:
            try:
                return self.online_llm.generate_report(text, task)
            except Exception as e:
                # Fallback to offline
                return self.offline_llm.enhance_medical_text(text, task)
        
        # Default to offline
        return self.offline_llm.enhance_medical_text(text, task)
```

---

## 📦 MCP Server Implementation

### File Structure
```
mcp-medical-server/
├── server.py                 # Main MCP server
├── tools/
│   ├── dictation_tools.py    # Medical dictation tools
│   ├── pacs_tools.py         # Orthanc PACS tools
│   ├── workflow_tools.py     # Workflow integration
│   └── llm_tools.py          # LLM enhancement tools
├── services/
│   ├── whisper_service.py    # Whisper AI integration
│   ├── orthanc_client.py     # Orthanc REST API client
│   ├── offline_llm.py        # Llama 3.2 integration
│   └── online_llm.py         # GPT-4/Claude integration
├── models/
│   └── llama-3.2-3b-instruct.gguf  # Offline LLM model
├── config/
│   └── mcp_config.json       # Server configuration
├── requirements.txt
└── README.md
```

### Main Server Implementation

```python
# server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from tools.dictation_tools import DictationTools
from tools.pacs_tools import PACSTools
from tools.workflow_tools import WorkflowTools
from tools.llm_tools import LLMTools

class MedicalMCPServer:
    def __init__(self):
        self.server = Server("ubuntu-patient-care-mcp")
        self.dictation = DictationTools()
        self.pacs = PACSTools()
        self.workflow = WorkflowTools()
        self.llm = LLMTools()
        
        self.register_tools()
        
    def register_tools(self):
        # Medical Dictation Tools
        @self.server.tool()
        async def dictate_medical_report(
            audio_file: str,
            report_type: str = "radiology",
            patient_id: str = None,
            study_id: str = None
        ):
            """Transcribe voice to medical report"""
            return await self.dictation.transcribe(
                audio_file, report_type, patient_id, study_id
            )
        
        @self.server.tool()
        async def enhance_medical_text(
            text: str,
            enhancement_type: str = "grammar",
            use_online_llm: bool = False
        ):
            """Enhance medical text with LLM"""
            return await self.llm.enhance_text(
                text, enhancement_type, use_online_llm
            )
        
        # PACS Tools
        @self.server.tool()
        async def pacs_find_patients(
            patient_id: str = None,
            patient_name: str = None,
            limit: int = 50
        ):
            """Search for patients in PACS"""
            return await self.pacs.find_patients(
                patient_id, patient_name, limit
            )
        
        @self.server.tool()
        async def pacs_find_studies(
            patient_id: str = None,
            study_date: str = None,
            modality: str = None
        ):
            """Search for DICOM studies"""
            return await self.pacs.find_studies(
                patient_id, study_date, modality
            )
        
        @self.server.tool()
        async def pacs_get_study_details(study_id: str):
            """Get detailed study information"""
            return await self.pacs.get_study_details(study_id)
        
        # Workflow Tools
        @self.server.tool()
        async def get_worklist(
            radiologist_id: str = None,
            status: str = "pending"
        ):
            """Get radiologist worklist"""
            return await self.workflow.get_worklist(
                radiologist_id, status
            )
        
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

if __name__ == "__main__":
    server = MedicalMCPServer()
    asyncio.run(server.run())
```

---

## 🔧 Installation & Setup

### Prerequisites
```bash
# Python 3.10+
python --version

# Install dependencies
pip install mcp anthropic openai llama-cpp-python whisper pydicom requests

# Download Llama 3.2 3B model
wget https://huggingface.co/TheBloke/Llama-3.2-3B-Instruct-GGUF/resolve/main/llama-3.2-3b-instruct.Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct.gguf
```

### Configuration

Create `config/mcp_config.json`:
```json
{
  "server": {
    "name": "ubuntu-patient-care-mcp",
    "version": "1.0.0"
  },
  "orthanc": {
    "url": "http://localhost:8042",
    "username": "orthanc",
    "password": "orthanc"
  },
  "llm": {
    "offline_model": "models/llama-3.2-3b-instruct.gguf",
    "online_provider": "openai",
    "fallback_to_offline": true
  },
  "whisper": {
    "model": "medium",
    "language": "en",
    "device": "cpu"
  },
  "database": {
    "url": "mysql://localhost:3306/sa_ris_db"
  }
}
```

### Kiro MCP Configuration

Add to `.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "ubuntu-patient-care": {
      "command": "python",
      "args": ["C:/path/to/mcp-medical-server/server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here",
        "ANTHROPIC_API_KEY": "your-key-here"
      },
      "disabled": false,
      "autoApprove": [
        "pacs_find_patients",
        "pacs_find_studies",
        "get_worklist"
      ]
    }
  }
}
```

---

## 🚀 Usage Examples

### Example 1: Medical Dictation
```python
# In Kiro IDE
result = await mcp.call_tool(
    "ubuntu-patient-care",
    "dictate_medical_report",
    {
        "audio_file": "recording.wav",
        "report_type": "radiology",
        "patient_id": "12345"
    }
)

print(result["transcription"])
# "CT scan of the head shows no acute intracranial abnormality..."
```

### Example 2: PACS Query
```python
# Find patient studies
studies = await mcp.call_tool(
    "ubuntu-patient-care",
    "pacs_find_studies",
    {
        "patient_id": "8001015009087",
        "modality": "CT"
    }
)

for study in studies["studies"]:
    print(f"{study['study_date']}: {study['study_description']}")
```

### Example 3: Report Enhancement
```python
# Enhance report with LLM
enhanced = await mcp.call_tool(
    "ubuntu-patient-care",
    "enhance_medical_text",
    {
        "text": "brain looks ok no problems",
        "enhancement_type": "structure",
        "use_online_llm": False  # Use offline Llama
    }
)

print(enhanced["enhanced_text"])
# "FINDINGS: The brain parenchyma demonstrates normal attenuation..."
```

---

## 📊 Performance Metrics

### Offline LLM (Llama 3.2 3B)
- Model size: 2.5 GB
- RAM usage: 3-4 GB
- Inference time: 500-1000ms per response
- Context window: 4096 tokens
- Runs on: CPU (no GPU needed)

### Whisper AI
- Model: medium (769M params)
- Transcription speed: 2x realtime
- Accuracy: 95%+ on medical terms
- Languages: English, Afrikaans

### PACS Operations
- Patient search: < 100ms
- Study retrieval: < 500ms
- Image download: Depends on size

---

## 🔒 Security & Privacy

### MCP Security Architecture

MCP provides **built-in security** that cannot be bypassed:

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Security Layers                                         │
└─────────────────────────────────────────────────────────────┘

Layer 1: Authentication
├─ User must authenticate before using MCP
├─ Session tokens with expiration (15 min timeout)
├─ Biometric authentication support (Windows Hello)
└─ 2FA required for sensitive operations

Layer 2: Authorization (RBAC)
├─ Each tool has required permissions
├─ User roles define allowed tools
├─ Fine-grained permissions per tool
└─ Cannot bypass permission checks (enforced at MCP level)

Layer 3: Audit Logging
├─ Every tool call logged (tamper-proof)
├─ Includes user, timestamp, parameters, result
├─ Real-time security monitoring
└─ Alerts on suspicious activity

Layer 4: Input Validation
├─ All inputs validated against JSON schema
├─ SQL injection prevention
├─ XSS prevention
└─ Path traversal prevention

Layer 5: Output Filtering
├─ Sensitive data redacted based on role
├─ PII protection (POPI Act compliant)
├─ Role-based data access
└─ Encryption in transit (TLS 1.3)

Layer 6: Rate Limiting
├─ Prevents bulk data exfiltration
├─ Detects suspicious patterns
├─ Automatic blocking of abuse
└─ Alerts security team
```

### Role-Based Access Control (RBAC)

```json
{
  "roles": {
    "radiologist": {
      "allowed_tools": [
        "pacs_find_studies",
        "pacs_get_study_details",
        "pacs_retrieve_images",
        "smart_report_assistant",
        "quick_actions",
        "voice_command_executor",
        "create_preauth_request",
        "check_preauth_status",
        "intelligent_worklist"
      ],
      "denied_tools": [
        "pacs_delete_study",
        "export_patient_data",
        "modify_audit_logs",
        "change_permissions"
      ],
      "rate_limits": {
        "pacs_retrieve_images": "100/hour",
        "export_patient_data": "0/day"
      }
    },
    "receptionist": {
      "allowed_tools": [
        "create_patient",
        "search_patient",
        "validate_medical_aid",
        "estimate_patient_cost",
        "create_preauth_request",
        "check_preauth_status"
      ],
      "denied_tools": [
        "pacs_*",
        "view_reports",
        "finalize_reports",
        "export_patient_data"
      ],
      "data_redaction": [
        "clinical_notes",
        "report_findings"
      ]
    },
    "technologist": {
      "allowed_tools": [
        "pacs_store_study",
        "pacs_find_studies",
        "link_study_to_workflow",
        "update_workflow_status"
      ],
      "denied_tools": [
        "view_reports",
        "finalize_reports",
        "export_patient_data",
        "pacs_delete_study"
      ]
    },
    "admin": {
      "allowed_tools": ["*"],
      "requires_2fa": true,
      "audit_level": "verbose",
      "session_timeout": "5 minutes"
    }
  }
}
```

### Audit Logging

Every MCP tool call generates an audit log entry:

```json
{
  "audit_log_entry": {
    "id": "LOG-2025-001234",
    "timestamp": "2025-01-15T10:30:45.123Z",
    "user": {
      "id": "DR-001",
      "name": "Dr. John Smith",
      "role": "radiologist",
      "workstation": "WS-RADIOLOGY-01",
      "ip_address": "192.168.1.21"
    },
    "tool": {
      "name": "pacs_get_study_details",
      "parameters": {
        "study_id": "CT-2025-001234"
      },
      "result": "success",
      "execution_time_ms": 45
    },
    "patient": {
      "id": "12345",
      "id_number_hash": "sha256:abc123..." // Encrypted
    },
    "security": {
      "permission_check": "passed",
      "authentication_method": "biometric",
      "session_id": "SESSION-ABC123",
      "2fa_verified": false
    },
    "context": {
      "workflow_id": "WF-2025-001234",
      "referring_doctor": "DR-JONES",
      "clinical_indication": "Headache"
    }
  }
}
```

### Preventing Jailbreaking

**MCP prevents jailbreaking through:**

1. **Tool-Level Permission Enforcement**
```python
@mcp_server.tool()
@require_permission("export_patient_data")
@require_2fa()
@audit_log(level="critical")
async def export_patient_data(patient_id: str, format: str):
    """Export patient data - RESTRICTED"""
    
    # Permission check happens BEFORE function executes
    # If user doesn't have permission, function never runs
    # No way to bypass this check
    
    # Additional validation
    if not validate_export_reason():
        raise PermissionError("Export reason required")
    
    # Log export
    log_data_export(patient_id, current_user, reason)
    
    # Watermark exported data
    data = get_patient_data(patient_id)
    watermarked = add_watermark(data, current_user)
    
    return watermarked
```

2. **Input Validation (Prevents Injection)**
```python
@mcp_server.tool()
async def pacs_find_patients(patient_id: str = None):
    """Search for patients"""
    
    # MCP validates input against JSON schema
    # Prevents SQL injection, XSS, etc.
    
    # Additional validation
    if patient_id:
        if not validate_patient_id_format(patient_id):
            raise ValueError("Invalid patient ID format")
    
    # Safe query execution (parameterized)
    return await db.query_safe(
        "SELECT * FROM patients WHERE id = ?",
        [patient_id]
    )
```

3. **Rate Limiting (Prevents Abuse)**
```python
@mcp_server.tool()
@rate_limit(max_calls=100, per_minutes=60)
async def pacs_retrieve_images(study_id: str):
    """Retrieve DICOM images"""
    
    # Rate limiting prevents:
    # - Bulk data exfiltration
    # - DoS attacks
    # - Suspicious activity
    
    # Alert on suspicious patterns
    if detect_suspicious_pattern(current_user):
        alert_security_team(current_user, "Suspicious activity")
        raise SecurityError("Rate limit exceeded")
```

4. **Data Redaction (Protects PII)**
```python
@mcp_server.tool()
async def get_patient_summary(patient_id: str):
    """Get patient summary"""
    
    patient = await db.get_patient(patient_id)
    
    # Redact based on user role
    if current_user.role == "receptionist":
        patient = redact_sensitive_fields(patient, [
            "clinical_notes",
            "report_findings",
            "diagnosis"
        ])
    
    if current_user.role != "doctor":
        patient = redact_sensitive_fields(patient, [
            "id_number",
            "medical_aid_number",
            "address",
            "phone_number"
        ])
    
    return patient
```

### Security Monitoring

Real-time security dashboard tracks:
- Unauthorized access attempts
- Rate limit violations
- Suspicious activity patterns
- Failed permission checks
- Data export attempts
- Bulk query operations

**Automatic Alerts:**
- Email/SMS on critical security events
- Slack/Teams integration
- Escalation to security team
- Automatic account lockout on repeated violations

### Data Protection
- All patient data encrypted at rest (AES-256)
- TLS 1.3 for network communication
- No patient data sent to online LLMs without explicit consent
- Audit logging for all operations (tamper-proof)
- Automatic data retention policy enforcement
- Secure key management (HSM support)

### POPI Act Compliance
- Patient consent required for AI processing
- Data retention policies enforced (7 years)
- Right to deletion supported
- Audit trail maintained (10 years)
- Data minimization (only collect what's needed)
- Purpose limitation (data used only for stated purpose)
- Breach notification (within 72 hours)

---

## 🎯 Next Steps

1. **Week 1:** Implement core MCP server structure
2. **Week 2:** Add medical dictation tools
3. **Week 3:** Integrate Orthanc PACS tools
4. **Week 4:** Add offline LLM (Llama 3.2)
5. **Week 5:** Testing and optimization
6. **Week 6:** Documentation and deployment

---

## 📚 References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Orthanc REST API Documentation](https://book.orthanc-server.com/users/rest.html)
- [Llama 3.2 Model Card](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)
- [Whisper AI Documentation](https://github.com/openai/whisper)

---

**Document Version:** 1.0  
**Created:** January 2025  
**Status:** Planning Phase
