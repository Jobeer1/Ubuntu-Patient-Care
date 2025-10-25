# Developer 2: PACS & RIS Integration

**Role:** Healthcare Systems Integration Specialist  
**Primary Focus:** Orthanc PACS adapter, RIS adapter, DICOM workflows, medical databases  
**Estimated Effort:** 12 weeks (full-time)

---

## Phase 1: Foundation (Weeks 1-4)

### Week 1-2: PACS Adapter Development

#### Task 2.1: Environment Setup & Orthanc Familiarization
**Estimated Time:** 6 hours  
**Priority:** Critical

- [ ] Setup local Orthanc instance:
  ```bash
  docker run -p 8042:8042 jodogne/orthanc-plugins
  # Default credentials: orthanc / orthanc
  ```

- [ ] Test Orthanc REST API:
  ```bash
  # List patients
  curl -u orthanc:orthanc http://localhost:8042/patients
  
  # Upload DICOM file
  curl -X POST http://localhost:8042/instances -u orthanc:orthanc \
    --data-binary @sample.dcm
  ```

- [ ] Study DICOMweb endpoints:
  - [ ] QIDO-RS (Query): `/dicom-web/studies`
  - [ ] WADO-RS (Retrieve): `/dicom-web/studies/{uid}/series`
  - [ ] STOW-RS (Store): `/dicom-web/studies`

- [ ] Download test DICOM datasets:
  - [ ] Get sample CT/MR/XR images from https://www.dicomlibrary.com/
  - [ ] Upload to local Orthanc for testing

- [ ] Document Orthanc setup in `docs/ORTHANC_SETUP.md`

**Deliverables:** Working Orthanc instance with test data

---

#### Task 2.2: PACS Adapter Core Implementation
**Estimated Time:** 16 hours  
**Priority:** Critical  
**Dependencies:** Dev 1 provides adapter interface (Task 1.6)

- [ ] Create `adapters/pacs_adapter.py`:
  ```python
  from adapters.base_adapter import ModuleAdapter
  import httpx
  from typing import Dict, List, Optional
  from datetime import datetime
  
  class OrthancPACSAdapter(ModuleAdapter):
      """Adapter for Orthanc PACS server"""
      
      def __init__(self, config: Dict):
          super().__init__(config)
          self.base_url = config["orthanc_url"]
          self.username = config.get("username", "orthanc")
          self.password = config.get("password", "orthanc")
          self.client: Optional[httpx.AsyncClient] = None
      
      async def initialize(self):
          """Initialize HTTP client with authentication"""
          self.client = httpx.AsyncClient(
              base_url=self.base_url,
              auth=(self.username, self.password),
              timeout=30.0
          )
          # Test connection
          response = await self.client.get("/system")
          if response.status_code != 200:
              raise ConnectionError(f"Failed to connect to Orthanc: {response.text}")
      
      async def health_check(self) -> bool:
          """Check Orthanc server health"""
          try:
              response = await self.client.get("/system")
              return response.status_code == 200
          except Exception:
              return False
      
      async def invoke_tool(self, tool_name: str, params: Dict) -> Dict:
          """Route tool invocations"""
          tool_map = {
              "pacs_search_studies": self._search_studies,
              "pacs_retrieve_study": self._retrieve_study,
              "pacs_upload_study": self._upload_study,
              "pacs_get_patient_history": self._get_patient_history,
          }
          
          if tool_name not in tool_map:
              raise ValueError(f"Unknown PACS tool: {tool_name}")
          
          handler = tool_map[tool_name]
          return await handler(**params)
      
      async def shutdown(self):
          """Close HTTP client"""
          if self.client:
              await self.client.aclose()
  ```

- [ ] Implement tool methods (see next tasks)

**Deliverables:** PACS adapter skeleton with initialization

---

#### Task 2.3: Implement `pacs_search_studies` Tool
**Estimated Time:** 10 hours  
**Priority:** Critical

- [ ] Implement DICOMweb QIDO-RS search:
  ```python
  async def _search_studies(
      self,
      patient_id: Optional[str] = None,
      patient_name: Optional[str] = None,
      study_date: Optional[str] = None,
      modality: Optional[str] = None,
      accession_number: Optional[str] = None
  ) -> Dict:
      """
      Search for DICOM studies using DICOMweb QIDO-RS
      
      Args:
          patient_id: Patient identifier (MRN)
          patient_name: Patient name in DICOM format (Last^First)
          study_date: Date or range (YYYYMMDD or YYYYMMDD-YYYYMMDD)
          modality: Imaging modality (CT, MR, XR, etc.)
          accession_number: Unique study accession number
      
      Returns:
          Dict with 'studies' list containing study metadata
      """
      # Build QIDO-RS query parameters
      query_params = {}
      
      if patient_id:
          query_params["PatientID"] = patient_id
      if patient_name:
          query_params["PatientName"] = patient_name
      if study_date:
          query_params["StudyDate"] = study_date
      if modality:
          query_params["ModalitiesInStudy"] = modality
      if accession_number:
          query_params["AccessionNumber"] = accession_number
      
      # Query Orthanc DICOMweb endpoint
      response = await self.client.get(
          "/dicom-web/studies",
          params=query_params,
          headers={"Accept": "application/json"}
      )
      
      if response.status_code != 200:
          raise Exception(f"QIDO-RS query failed: {response.text}")
      
      # Parse DICOM JSON response
      dicom_studies = response.json()
      
      # Convert to simplified format
      studies = []
      for study in dicom_studies:
          studies.append({
              "study_instance_uid": self._extract_value(study, "0020000D"),
              "patient_id": self._extract_value(study, "00100020"),
              "patient_name": self._extract_value(study, "00100010"),
              "study_date": self._extract_value(study, "00080020"),
              "study_time": self._extract_value(study, "00080030"),
              "modality": self._extract_value(study, "00080060"),
              "study_description": self._extract_value(study, "00081030"),
              "accession_number": self._extract_value(study, "00080050"),
              "number_of_series": self._extract_value(study, "00201206", 0),
              "number_of_instances": self._extract_value(study, "00201208", 0)
          })
      
      return {"studies": studies, "count": len(studies)}
  
  def _extract_value(self, dicom_obj: Dict, tag: str, default=None):
      """Extract value from DICOM JSON object"""
      if tag not in dicom_obj:
          return default
      
      vr = dicom_obj[tag].get("vr")
      
      # Handle different Value Representations
      if vr in ["PN", "LO", "SH", "CS", "UI", "DA", "TM"]:
          values = dicom_obj[tag].get("Value", [])
          return values[0] if values else default
      elif vr in ["IS", "DS"]:
          values = dicom_obj[tag].get("Value", [])
          return int(values[0]) if values else default
      else:
          return default
  ```

- [ ] Add validation for date formats:
  ```python
  def _validate_date_format(self, date_str: str) -> bool:
      """Validate DICOM date format (YYYYMMDD or range)"""
      import re
      pattern = r'^\d{8}(-\d{8})?$'
      return bool(re.match(pattern, date_str))
  ```

- [ ] Write unit tests in `tests/unit/test_pacs_adapter.py`:
  ```python
  @pytest.mark.asyncio
  async def test_search_studies_by_patient_id(mock_orthanc):
      adapter = OrthancPACSAdapter({"orthanc_url": "http://mock"})
      await adapter.initialize()
      
      result = await adapter.invoke_tool(
          "pacs_search_studies",
          {"patient_id": "P12345"}
      )
      
      assert "studies" in result
      assert result["count"] >= 0
  ```

**Deliverables:** Working QIDO-RS search with tests

---

#### Task 2.4: Implement `pacs_retrieve_study` Tool
**Estimated Time:** 8 hours  
**Priority:** High

- [ ] Implement WADO-RS retrieval:
  ```python
  async def _retrieve_study(
      self,
      study_instance_uid: str,
      include_images: bool = False
  ) -> Dict:
      """
      Retrieve study metadata and optionally image URLs
      
      Args:
          study_instance_uid: Unique study identifier
          include_images: If True, return WADO-RS URLs for all instances
      
      Returns:
          Study details with series/instance information
      """
      # Get study details from Orthanc REST API
      response = await self.client.get(f"/studies/{study_instance_uid}")
      
      if response.status_code == 404:
          raise ValueError(f"Study {study_instance_uid} not found")
      elif response.status_code != 200:
          raise Exception(f"Failed to retrieve study: {response.text}")
      
      study_data = response.json()
      
      # Extract series information
      series_list = []
      for series_id in study_data.get("Series", []):
          series_response = await self.client.get(f"/series/{series_id}")
          series_data = series_response.json()
          
          series_info = {
              "series_instance_uid": series_data.get("MainDicomTags", {}).get("SeriesInstanceUID"),
              "series_number": series_data.get("MainDicomTags", {}).get("SeriesNumber"),
              "modality": series_data.get("MainDicomTags", {}).get("Modality"),
              "series_description": series_data.get("MainDicomTags", {}).get("SeriesDescription"),
              "number_of_instances": len(series_data.get("Instances", []))
          }
          
          if include_images:
              # Generate WADO-RS URLs for instances
              series_info["instances"] = [
                  {
                      "instance_uid": inst_id,
                      "wado_url": f"{self.base_url}/dicom-web/studies/{study_instance_uid}/series/{series_info['series_instance_uid']}/instances/{inst_id}"
                  }
                  for inst_id in series_data.get("Instances", [])
              ]
          
          series_list.append(series_info)
      
      return {
          "study_instance_uid": study_instance_uid,
          "patient_id": study_data.get("PatientMainDicomTags", {}).get("PatientID"),
          "study_date": study_data.get("MainDicomTags", {}).get("StudyDate"),
          "study_description": study_data.get("MainDicomTags", {}).get("StudyDescription"),
          "series": series_list,
          "total_instances": sum(s["number_of_instances"] for s in series_list)
      }
  ```

- [ ] Add thumbnail generation helper:
  ```python
  async def _get_study_thumbnail(self, study_instance_uid: str) -> bytes:
      """Get preview thumbnail for first instance"""
      response = await self.client.get(
          f"/studies/{study_instance_uid}/preview",
          headers={"Accept": "image/jpeg"}
      )
      return response.content
  ```

**Deliverables:** Study retrieval with WADO-RS URLs

---

### Week 3: RIS Database & Adapter

#### Task 2.5: RIS Database Schema Design
**Estimated Time:** 8 hours  
**Priority:** Critical

- [ ] Design PostgreSQL schema in `database/ris_schema.sql`:
  ```sql
  -- Patients table
  CREATE TABLE IF NOT EXISTS patients (
      patient_id VARCHAR(50) PRIMARY KEY,
      mrn VARCHAR(50) UNIQUE NOT NULL,
      first_name VARCHAR(100) NOT NULL,
      last_name VARCHAR(100) NOT NULL,
      date_of_birth DATE NOT NULL,
      gender CHAR(1),
      phone VARCHAR(20),
      email VARCHAR(100),
      address TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Referring physicians
  CREATE TABLE IF NOT EXISTS physicians (
      physician_id SERIAL PRIMARY KEY,
      npi VARCHAR(10) UNIQUE,
      first_name VARCHAR(100) NOT NULL,
      last_name VARCHAR(100) NOT NULL,
      specialty VARCHAR(100),
      phone VARCHAR(20),
      email VARCHAR(100),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Imaging modalities
  CREATE TABLE IF NOT EXISTS modalities (
      modality_code VARCHAR(10) PRIMARY KEY,
      modality_name VARCHAR(100) NOT NULL,
      description TEXT,
      active BOOLEAN DEFAULT TRUE
  );
  
  -- Insert standard modalities
  INSERT INTO modalities (modality_code, modality_name) VALUES
      ('CT', 'Computed Tomography'),
      ('MR', 'Magnetic Resonance'),
      ('XR', 'X-Ray'),
      ('US', 'Ultrasound'),
      ('NM', 'Nuclear Medicine'),
      ('PT', 'Positron Emission Tomography'),
      ('MG', 'Mammography')
  ON CONFLICT DO NOTHING;
  
  -- Appointments/Orders
  CREATE TABLE IF NOT EXISTS appointments (
      appointment_id SERIAL PRIMARY KEY,
      accession_number VARCHAR(50) UNIQUE NOT NULL,
      patient_id VARCHAR(50) REFERENCES patients(patient_id),
      referring_physician_id INT REFERENCES physicians(physician_id),
      modality VARCHAR(10) REFERENCES modalities(modality_code),
      study_description TEXT,
      scheduled_datetime TIMESTAMP NOT NULL,
      scheduled_duration_minutes INT DEFAULT 30,
      room VARCHAR(20),
      technologist_id INT,
      status VARCHAR(20) DEFAULT 'scheduled',
      priority VARCHAR(20) DEFAULT 'routine',
      clinical_indication TEXT,
      special_instructions TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT status_check CHECK (status IN ('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show'))
  );
  
  -- Modality Worklist
  CREATE TABLE IF NOT EXISTS modality_worklist (
      worklist_id SERIAL PRIMARY KEY,
      appointment_id INT REFERENCES appointments(appointment_id),
      scheduled_station_ae_title VARCHAR(16),
      scheduled_procedure_step_id VARCHAR(50),
      requested_procedure_id VARCHAR(50),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Indexes for performance
  CREATE INDEX idx_appointments_patient ON appointments(patient_id);
  CREATE INDEX idx_appointments_scheduled ON appointments(scheduled_datetime);
  CREATE INDEX idx_appointments_status ON appointments(status);
  CREATE INDEX idx_appointments_modality ON appointments(modality);
  ```

- [ ] Create database migration script `database/migrate.py`:
  ```python
  import asyncpg
  import asyncio
  
  async def run_migrations(db_url: str):
      conn = await asyncpg.connect(db_url)
      
      with open('database/ris_schema.sql', 'r') as f:
          schema_sql = f.read()
      
      await conn.execute(schema_sql)
      print("RIS database schema created successfully")
      
      await conn.close()
  
  if __name__ == "__main__":
      asyncio.run(run_migrations("postgresql://ris:ris@localhost/ris"))
  ```

- [ ] Create test data seeding script `database/seed_test_data.py`:
  ```python
  async def seed_test_data(db_url: str):
      conn = await asyncpg.connect(db_url)
      
      # Insert test patients
      for i in range(1, 101):
          await conn.execute("""
              INSERT INTO patients (patient_id, mrn, first_name, last_name, date_of_birth, gender)
              VALUES ($1, $2, $3, $4, $5, $6)
              ON CONFLICT DO NOTHING
          """, f"P{i:05d}", f"MRN{i:05d}", f"Test{i}", f"Patient{i}",
               "1980-01-01", "M" if i % 2 == 0 else "F")
      
      # Insert test physicians
      await conn.execute("""
          INSERT INTO physicians (npi, first_name, last_name, specialty)
          VALUES ('1234567890', 'John', 'Smith', 'Radiology')
          ON CONFLICT DO NOTHING
      """)
      
      await conn.close()
      print("Test data seeded successfully")
  ```

**Deliverables:** RIS database schema, migration scripts

---

#### Task 2.6: RIS Adapter Implementation
**Estimated Time:** 14 hours  
**Priority:** Critical  
**Dependencies:** Task 2.5

- [ ] Create `adapters/ris_adapter.py`:
  ```python
  from adapters.base_adapter import ModuleAdapter
  import asyncpg
  from typing import Dict, List, Optional
  from datetime import datetime, timedelta
  
  class RISAdapter(ModuleAdapter):
      """Adapter for Radiology Information System (PostgreSQL)"""
      
      def __init__(self, config: Dict):
          super().__init__(config)
          self.db_url = config["ris_db_url"]
          self.pool: Optional[asyncpg.Pool] = None
      
      async def initialize(self):
          """Create database connection pool"""
          self.pool = await asyncpg.create_pool(
              self.db_url,
              min_size=5,
              max_size=20
          )
          
          # Test connection
          async with self.pool.acquire() as conn:
              await conn.fetchval("SELECT 1")
      
      async def health_check(self) -> bool:
          """Check database connectivity"""
          try:
              async with self.pool.acquire() as conn:
                  await conn.fetchval("SELECT 1")
              return True
          except Exception:
              return False
      
      async def invoke_tool(self, tool_name: str, params: Dict) -> Dict:
          """Route tool invocations"""
          tool_map = {
              "ris_schedule_appointment": self._schedule_appointment,
              "ris_get_worklist": self._get_worklist,
              "ris_update_study_status": self._update_study_status,
              "ris_get_referring_physician": self._get_referring_physician,
              "ris_search_patients": self._search_patients,
          }
          
          if tool_name not in tool_map:
              raise ValueError(f"Unknown RIS tool: {tool_name}")
          
          handler = tool_map[tool_name]
          return await handler(**params)
      
      async def shutdown(self):
          """Close database pool"""
          if self.pool:
              await self.pool.close()
  ```

- [ ] Implement scheduling tool:
  ```python
  async def _schedule_appointment(
      self,
      patient_id: str,
      modality: str,
      requested_date: str,  # ISO format: 2025-10-15T09:00:00
      priority: str = "routine",
      study_description: Optional[str] = None,
      referring_physician_id: Optional[int] = None,
      clinical_indication: Optional[str] = None
  ) -> Dict:
      """
      Schedule a radiology appointment
      
      Returns:
          appointment_id, accession_number, scheduled_time, room
      """
      async with self.pool.acquire() as conn:
          # Validate patient exists
          patient = await conn.fetchrow(
              "SELECT * FROM patients WHERE patient_id = $1",
              patient_id
          )
          if not patient:
              raise ValueError(f"Patient {patient_id} not found")
          
          # Find available time slot (simplified logic)
          requested_datetime = datetime.fromisoformat(requested_date)
          available_slot = await self._find_available_slot(
              conn, modality, requested_datetime
          )
          
          # Generate accession number
          accession_number = f"ACC{datetime.now().strftime('%Y%m%d%H%M%S')}"
          
          # Insert appointment
          appointment_id = await conn.fetchval("""
              INSERT INTO appointments (
                  accession_number, patient_id, referring_physician_id,
                  modality, study_description, scheduled_datetime,
                  status, priority, clinical_indication, room
              )
              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
              RETURNING appointment_id
          """, accession_number, patient_id, referring_physician_id,
               modality, study_description or f"{modality} Study",
               available_slot, "scheduled", priority, clinical_indication,
               f"{modality}-ROOM-1")
          
          return {
              "appointment_id": appointment_id,
              "accession_number": accession_number,
              "scheduled_time": available_slot.isoformat(),
              "room": f"{modality}-ROOM-1",
              "status": "scheduled"
          }
  
  async def _find_available_slot(
      self,
      conn: asyncpg.Connection,
      modality: str,
      requested_time: datetime
  ) -> datetime:
      """Find next available slot for modality (simplified)"""
      # Check if requested time is available
      existing = await conn.fetchval("""
          SELECT COUNT(*) FROM appointments
          WHERE modality = $1
          AND scheduled_datetime = $2
          AND status NOT IN ('cancelled', 'no_show')
      """, modality, requested_time)
      
      if existing == 0:
          return requested_time
      
      # Find next slot (30-minute increments)
      slot = requested_time
      for _ in range(20):  # Try next 10 hours
          slot += timedelta(minutes=30)
          existing = await conn.fetchval("""
              SELECT COUNT(*) FROM appointments
              WHERE modality = $1 AND scheduled_datetime = $2
          """, modality, slot)
          if existing == 0:
              return slot
      
      raise Exception(f"No available slots found for {modality}")
  ```

- [ ] Implement worklist retrieval:
  ```python
  async def _get_worklist(
      self,
      date: Optional[str] = None,
      modality: Optional[str] = None,
      status: str = "scheduled"
  ) -> Dict:
      """Get modality worklist for a date/modality"""
      async with self.pool.acquire() as conn:
          query = """
              SELECT
                  a.appointment_id,
                  a.accession_number,
                  a.patient_id,
                  p.first_name || ' ' || p.last_name AS patient_name,
                  p.date_of_birth,
                  a.modality,
                  a.study_description,
                  a.scheduled_datetime,
                  a.room,
                  a.status,
                  a.priority
              FROM appointments a
              JOIN patients p ON a.patient_id = p.patient_id
              WHERE a.status = $1
          """
          params = [status]
          
          if date:
              query += " AND DATE(a.scheduled_datetime) = $2"
              params.append(date)
          
          if modality:
              query += f" AND a.modality = ${len(params) + 1}"
              params.append(modality)
          
          query += " ORDER BY a.scheduled_datetime"
          
          rows = await conn.fetch(query, *params)
          
          worklist = [dict(row) for row in rows]
          
          return {"worklist": worklist, "count": len(worklist)}
  ```

**Deliverables:** Working RIS adapter with scheduling and worklist tools

---

### Week 4: Integration & Testing

#### Task 2.7: Register Tools with MCP Server
**Estimated Time:** 6 hours  
**Priority:** High  
**Collaboration:** Work with Dev 1

- [ ] Create tool definitions in `adapters/pacs_tools.json`:
  ```json
  [
    {
      "name": "pacs_search_studies",
      "description": "Search for DICOM studies in PACS by patient ID, name, date, or modality",
      "parameters": {
        "type": "object",
        "properties": {
          "patient_id": {"type": "string"},
          "patient_name": {"type": "string"},
          "study_date": {"type": "string"},
          "modality": {"type": "string", "enum": ["CT", "MR", "XR", "US", "NM", "PT", "MG"]},
          "accession_number": {"type": "string"}
        }
      }
    }
  ]
  ```

- [ ] Create registration script in `adapters/register_adapters.py`:
  ```python
  from server.tool_registry import registry
  from adapters.pacs_adapter import OrthancPACSAdapter
  from adapters.ris_adapter import RISAdapter
  import json
  
  async def register_pacs_adapter(config):
      adapter = OrthancPACSAdapter(config)
      await adapter.initialize()
      
      with open('adapters/pacs_tools.json') as f:
          tools = json.load(f)
      
      for tool in tools:
          registry.register_tool(
              ToolDefinition(**tool),
              lambda **params: adapter.invoke_tool(tool["name"], params)
          )
  
  async def register_ris_adapter(config):
      # Similar for RIS
      pass
  ```

- [ ] Test tool invocation through MCP server:
  ```bash
  curl -X POST http://localhost:8000/mcp/v1/invoke \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "tool": "pacs_search_studies",
      "parameters": {"patient_id": "P00001", "modality": "CT"}
    }'
  ```

**Deliverables:** PACS and RIS tools registered with MCP server

---

#### Task 2.8: Integration Testing
**Estimated Time:** 10 hours  
**Priority:** High

- [ ] Create integration tests in `tests/integration/test_pacs_integration.py`:
  ```python
  @pytest.mark.asyncio
  async def test_end_to_end_pacs_search(test_client, auth_headers):
      # Upload test DICOM first
      # ... upload logic
      
      # Search via MCP API
      response = await test_client.post(
          "/mcp/v1/invoke",
          json={
              "tool": "pacs_search_studies",
              "parameters": {"patient_id": "TEST001"}
          },
          headers=auth_headers
      )
      
      assert response.status_code == 200
      data = response.json()
      assert data["success"] is True
      assert len(data["result"]["studies"]) > 0
  ```

- [ ] Create RIS integration tests:
  - [ ] Test appointment scheduling
  - [ ] Test worklist retrieval
  - [ ] Test status updates

- [ ] Test cross-module workflow:
  ```python
  @pytest.mark.asyncio
  async def test_schedule_then_retrieve_study():
      # 1. Schedule appointment via RIS
      appointment = await ris_adapter.invoke_tool(
          "ris_schedule_appointment",
          {"patient_id": "P00001", "modality": "CT", ...}
      )
      
      # 2. Simulate study performed (upload DICOM with accession number)
      # ...
      
      # 3. Search PACS by accession number
      studies = await pacs_adapter.invoke_tool(
          "pacs_search_studies",
          {"accession_number": appointment["accession_number"]}
      )
      
      assert len(studies["studies"]) == 1
  ```

**Deliverables:** Comprehensive integration test suite

---

## Phase 2: Enhancement & Optimization (Weeks 5-8)

### Week 5-6: Advanced PACS Features

#### Task 2.9: Implement DICOM Upload (STOW-RS)
**Estimated Time:** 10 hours  
**Priority:** Medium

- [ ] Implement `pacs_upload_study` tool:
  ```python
  async def _upload_study(
      self,
      dicom_files: List[bytes],
      patient_id: str,
      study_description: Optional[str] = None
  ) -> Dict:
      """
      Upload DICOM files to PACS using STOW-RS
      
      Args:
          dicom_files: List of DICOM file contents
          patient_id: Patient identifier
          study_description: Optional study description
      
      Returns:
          Created StudyInstanceUID and instance count
      """
      # Prepare multipart/related request
      boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
      
      parts = []
      for i, dicom_data in enumerate(dicom_files):
          parts.append(
              f"--{boundary}\r\n"
              f"Content-Type: application/dicom\r\n"
              f"Content-Length: {len(dicom_data)}\r\n\r\n"
          )
          parts.append(dicom_data.decode('latin1'))  # Binary data
          parts.append("\r\n")
      
      parts.append(f"--{boundary}--\r\n")
      
      body = "".join(parts).encode('latin1')
      
      response = await self.client.post(
          "/dicom-web/studies",
          content=body,
          headers={
              "Content-Type": f"multipart/related; type=application/dicom; boundary={boundary}",
              "Accept": "application/json"
          }
      )
      
      if response.status_code not in [200, 201]:
          raise Exception(f"STOW-RS upload failed: {response.text}")
      
      result = response.json()
      # Parse STOW-RS response to extract StudyInstanceUID
      study_uid = result.get("00081199", {}).get("Value", [{}])[0].get("00081150", {}).get("Value", [None])[0]
      
      return {
          "study_instance_uid": study_uid,
          "instances_uploaded": len(dicom_files),
          "status": "success"
      }
  ```

- [ ] Test DICOM upload with pydicom:
  ```python
  import pydicom
  from pydicom.dataset import Dataset, FileDataset
  
  def create_test_dicom():
      file_meta = Dataset()
      file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
      file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
      file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
      
      ds = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
      ds.PatientName = "Test^Patient"
      ds.PatientID = "TEST001"
      ds.Modality = "CT"
      # ... more tags
      
      ds.save_as("test.dcm")
      
      with open("test.dcm", "rb") as f:
          return f.read()
  ```

**Deliverables:** DICOM upload capability via STOW-RS

---

#### Task 2.10: Patient History Aggregation
**Estimated Time:** 8 hours  
**Priority:** Medium

- [ ] Implement `pacs_get_patient_history`:
  ```python
  async def _get_patient_history(self, patient_id: str) -> Dict:
      """Get complete imaging history for a patient"""
      # Search all studies for patient
      studies_result = await self._search_studies(patient_id=patient_id)
      
      # Organize by modality and date
      history = {
          "patient_id": patient_id,
          "total_studies": studies_result["count"],
          "by_modality": {},
          "timeline": []
      }
      
      for study in studies_result["studies"]:
          modality = study["modality"]
          if modality not in history["by_modality"]:
              history["by_modality"][modality] = []
          
          history["by_modality"][modality].append({
              "study_date": study["study_date"],
              "study_description": study["study_description"],
              "study_uid": study["study_instance_uid"]
          })
      
      # Sort timeline
      history["timeline"] = sorted(
          studies_result["studies"],
          key=lambda x: x["study_date"],
          reverse=True
      )
      
      return history
  ```

**Deliverables:** Patient imaging history tool

---

### Week 7-8: Performance & Documentation

#### Task 2.11: Query Optimization
**Estimated Time:** 8 hours  
**Priority:** Medium

- [ ] Add database indexes:
  ```sql
  CREATE INDEX CONCURRENTLY idx_appointments_patient_date 
  ON appointments(patient_id, scheduled_datetime DESC);
  
  CREATE INDEX CONCURRENTLY idx_appointments_modality_date 
  ON appointments(modality, scheduled_datetime);
  ```

- [ ] Optimize PACS queries with caching:
  ```python
  from functools import lru_cache
  import hashlib
  
  class PACSQueryCache:
      def __init__(self, ttl_seconds: int = 300):
          self.cache = {}
          self.ttl = ttl_seconds
      
      def get_cache_key(self, params: Dict) -> str:
          return hashlib.md5(str(sorted(params.items())).encode()).hexdigest()
      
      async def cached_search(self, adapter, params):
          key = self.get_cache_key(params)
          
          if key in self.cache:
              cached_data, timestamp = self.cache[key]
              if time.time() - timestamp < self.ttl:
                  return cached_data
          
          # Cache miss or expired
          result = await adapter._search_studies(**params)
          self.cache[key] = (result, time.time())
          return result
  ```

**Deliverables:** Optimized queries, caching layer

---

#### Task 2.12: Documentation & Examples
**Estimated Time:** 6 hours  
**Priority:** High

- [ ] Create `docs/PACS_ADAPTER_GUIDE.md`:
  - [ ] Architecture overview
  - [ ] Tool descriptions and parameters
  - [ ] Code examples for each tool
  - [ ] Troubleshooting guide

- [ ] Create `docs/RIS_ADAPTER_GUIDE.md`:
  - [ ] Database schema explanation
  - [ ] Workflow diagrams (scheduling, worklist)
  - [ ] API examples

- [ ] Create example scripts in `examples/`:
  - [ ] `search_studies.py`
  - [ ] `schedule_appointment.py`
  - [ ] `upload_dicom.py`

**Deliverables:** Complete adapter documentation

---

## Phase 3: Production Readiness (Weeks 9-12)

### Week 9-10: HL7/FHIR Integration (Optional)

#### Task 2.13: HL7 Message Handling
**Estimated Time:** 12 hours  
**Priority:** Low (if time permits)

- [ ] Add HL7 library:
  ```bash
  pip install hl7
  ```

- [ ] Create HL7 parser for ORM (Order) messages:
  ```python
  import hl7
  
  def parse_hl7_order(hl7_message: str) -> Dict:
      """Parse HL7 ORM^O01 message"""
      msg = hl7.parse(hl7_message)
      
      pid_segment = msg.segment('PID')
      orc_segment = msg.segment('ORC')
      obr_segment = msg.segment('OBR')
      
      return {
          "patient_id": str(pid_segment[3]),
          "patient_name": str(pid_segment[5]),
          "accession_number": str(obr_segment[18]),
          "modality": str(obr_segment[24]),
          "study_description": str(obr_segment[4])
      }
  ```

**Deliverables:** Basic HL7 integration (if time allows)

---

### Week 11-12: Clinical Validation & Testing

#### Task 2.14: Clinical Workflow Validation
**Estimated Time:** 10 hours  
**Priority:** Critical  
**Collaboration:** Work with clinicians/users

- [ ] Create realistic test scenarios:
  - [ ] Emergency CT scan scheduling
  - [ ] Routine MRI booking 2 weeks out
  - [ ] Stat X-ray with immediate reading
  - [ ] Multi-series study retrieval

- [ ] Test with real DICOM data (anonymized)

- [ ] Document edge cases and limitations

**Deliverables:** Validated clinical workflows

---

## Success Metrics

### Functional
- ✅ PACS adapter can search/retrieve studies with <500ms latency
- ✅ RIS adapter can schedule appointments and generate worklists
- ✅ All DICOM modalities supported (CT, MR, XR, US, NM, PT, MG)
- ✅ 100% uptime for adapter health checks

### Code Quality
- ✅ 85%+ unit test coverage
- ✅ All integration tests passing
- ✅ Zero SQL injection vulnerabilities
- ✅ Proper error handling for network failures

---

## Tools & Technologies

- **DICOM:** pydicom, DICOMweb (QIDO/WADO/STOW-RS)
- **Database:** PostgreSQL, asyncpg
- **HTTP:** httpx
- **Testing:** pytest, pytest-asyncio
- **HL7 (optional):** python-hl7

---

**Good luck, Developer 2! You're the bridge between medical imaging and the MCP system. 🏥**
