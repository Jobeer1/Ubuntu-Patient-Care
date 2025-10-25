# Developer 3: Medical Reporting & Billing Integration

**Role:** Healthcare Business Systems Specialist  
**Primary Focus:** Medical reporting adapter, billing/accounting adapter, financial workflows  
**Estimated Effort:** 12 weeks (full-time)

---

## Phase 1: Foundation (Weeks 1-4)

### Week 1-2: Medical Reporting Adapter

#### Task 3.1: Survey Existing Reporting Module
**Estimated Time:** 6 hours  
**Priority:** Critical

- [ ] Explore existing medical reporting module structure:
  ```bash
  cd medical-reporting-module
  ls -la
  # Review: app.py, database schema, API endpoints
  ```

- [ ] Document current API endpoints:
  - [ ] `/api/transcribe` - Speech-to-text
  - [ ] `/api/reports` - CRUD operations
  - [ ] `/api/templates` - Report templates
  - [ ] Any other endpoints

- [ ] Review database schema in `medical_reporting.db`:
  ```sql
  .schema reports
  .schema report_templates
  .schema voice_recordings
  ```

- [ ] Test existing APIs:
  ```bash
  curl http://localhost:5000/api/reports
  curl -X POST http://localhost:5000/api/transcribe \
    -F "audio=@test_audio.wav"
  ```

- [ ] Document findings in `docs/REPORTING_MODULE_ANALYSIS.md`

**Deliverables:** Analysis document of existing reporting module

---

#### Task 3.2: Reporting Adapter Implementation
**Estimated Time:** 12 hours  
**Priority:** Critical  
**Dependencies:** Dev 1 provides adapter interface

- [ ] Create `adapters/reporting_adapter.py`:
  ```python
  from adapters.base_adapter import ModuleAdapter
  import httpx
  import sqlite3
  from typing import Dict, Optional, List
  import aiosqlite
  
  class ReportingAdapter(ModuleAdapter):
      """Adapter for Medical Reporting Module"""
      
      def __init__(self, config: Dict):
          super().__init__(config)
          self.api_url = config["reporting_api_url"]
          self.db_path = config.get("reporting_db_path", "./medical_reporting.db")
          self.client: Optional[httpx.AsyncClient] = None
          self.db: Optional[aiosqlite.Connection] = None
      
      async def initialize(self):
          """Initialize HTTP client and database connection"""
          self.client = httpx.AsyncClient(
              base_url=self.api_url,
              timeout=30.0
          )
          
          # Test API connection
          try:
              response = await self.client.get("/health")
              if response.status_code != 200:
                  raise ConnectionError(f"Reporting API unhealthy: {response.text}")
          except Exception as e:
              raise ConnectionError(f"Cannot connect to reporting API: {e}")
          
          # Open SQLite database
          self.db = await aiosqlite.connect(self.db_path)
      
      async def health_check(self) -> bool:
          """Check reporting module health"""
          try:
              response = await self.client.get("/health")
              return response.status_code == 200
          except:
              return False
      
      async def invoke_tool(self, tool_name: str, params: Dict) -> Dict:
          """Route tool invocations"""
          tool_map = {
              "reporting_transcribe_audio": self._transcribe_audio,
              "reporting_generate_report": self._generate_report,
              "reporting_get_report": self._get_report,
              "reporting_search_reports": self._search_reports,
              "reporting_update_report": self._update_report,
              "reporting_get_templates": self._get_templates,
          }
          
          if tool_name not in tool_map:
              raise ValueError(f"Unknown reporting tool: {tool_name}")
          
          handler = tool_map[tool_name]
          return await handler(**params)
      
      async def shutdown(self):
          """Close connections"""
          if self.client:
              await self.client.aclose()
          if self.db:
              await self.db.close()
  ```

**Deliverables:** Reporting adapter skeleton

---

#### Task 3.3: Implement Transcription Tool
**Estimated Time:** 10 hours  
**Priority:** High

- [ ] Implement `reporting_transcribe_audio`:
  ```python
  async def _transcribe_audio(
      self,
      audio_data: bytes,
      audio_format: str = "wav",
      language: str = "en-US"
  ) -> Dict:
      """
      Transcribe audio to text using existing STT service
      
      Args:
          audio_data: Audio file bytes
          audio_format: Audio format (wav, mp3, ogg)
          language: Language code
      
      Returns:
          Transcription text and confidence score
      """
      # Prepare multipart file upload
      files = {
          "audio": (f"recording.{audio_format}", audio_data, f"audio/{audio_format}")
      }
      
      data = {
          "language": language
      }
      
      # Call existing transcription API
      response = await self.client.post(
          "/api/transcribe",
          files=files,
          data=data,
          timeout=60.0  # Longer timeout for transcription
      )
      
      if response.status_code != 200:
          raise Exception(f"Transcription failed: {response.text}")
      
      result = response.json()
      
      return {
          "transcription": result.get("text", ""),
          "confidence": result.get("confidence", 0.0),
          "duration_seconds": result.get("duration", 0),
          "word_count": len(result.get("text", "").split())
      }
  ```

- [ ] Add support for chunked audio (long recordings):
  ```python
  async def _transcribe_long_audio(
      self,
      audio_data: bytes,
      chunk_size_seconds: int = 30
  ) -> Dict:
      """Transcribe long audio by splitting into chunks"""
      # Use pydub or similar to split audio
      from pydub import AudioSegment
      import io
      
      audio = AudioSegment.from_file(io.BytesIO(audio_data))
      chunk_length_ms = chunk_size_seconds * 1000
      
      chunks = [audio[i:i+chunk_length_ms] 
                for i in range(0, len(audio), chunk_length_ms)]
      
      transcriptions = []
      for i, chunk in enumerate(chunks):
          chunk_bytes = chunk.export(format="wav").read()
          result = await self._transcribe_audio(chunk_bytes, "wav")
          transcriptions.append(result["transcription"])
      
      full_text = " ".join(transcriptions)
      
      return {
          "transcription": full_text,
          "chunks_processed": len(chunks),
          "total_duration": len(audio) / 1000
      }
  ```

- [ ] Write tests for transcription:
  ```python
  @pytest.mark.asyncio
  async def test_transcribe_audio():
      adapter = ReportingAdapter(config)
      await adapter.initialize()
      
      # Load test audio file
      with open("tests/data/test_audio.wav", "rb") as f:
          audio_data = f.read()
      
      result = await adapter.invoke_tool(
          "reporting_transcribe_audio",
          {"audio_data": audio_data, "audio_format": "wav"}
      )
      
      assert "transcription" in result
      assert len(result["transcription"]) > 0
  ```

**Deliverables:** Working audio transcription tool

---

#### Task 3.4: Implement Report Generation Tool
**Estimated Time:** 10 hours  
**Priority:** High

- [ ] Implement `reporting_generate_report`:
  ```python
  async def _generate_report(
      self,
      study_id: str,
      patient_id: str,
      findings: str,
      impression: str,
      radiologist_id: str,
      report_type: str = "general",
      template_id: Optional[int] = None
  ) -> Dict:
      """
      Generate and store a medical report
      
      Args:
          study_id: Associated imaging study UID
          patient_id: Patient identifier
          findings: Clinical findings text
          impression: Summary/impression
          radiologist_id: Reporting radiologist ID
          report_type: Type of report (general, ct, mri, xr, etc.)
          template_id: Optional template to use
      
      Returns:
          report_id, pdf_url, created_at
      """
      import datetime
      
      # Generate report ID
      report_id = f"RPT{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
      
      # Get template if specified
      template_content = None
      if template_id:
          cursor = await self.db.execute(
              "SELECT content FROM report_templates WHERE id = ?",
              (template_id,)
          )
          row = await cursor.fetchone()
          if row:
              template_content = row[0]
      
      # Insert report into database
      created_at = datetime.datetime.now().isoformat()
      
      await self.db.execute("""
          INSERT INTO reports (
              report_id, study_id, patient_id, report_type,
              findings, impression, radiologist_id,
              template_id, status, created_at
          )
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """, (
          report_id, study_id, patient_id, report_type,
          findings, impression, radiologist_id,
          template_id, "draft", created_at
      ))
      
      await self.db.commit()
      
      # Generate PDF (call external service or use reportlab)
      pdf_url = await self._generate_pdf(
          report_id, findings, impression, template_content
      )
      
      return {
          "report_id": report_id,
          "pdf_url": pdf_url,
          "created_at": created_at,
          "status": "draft"
      }
  
  async def _generate_pdf(
      self,
      report_id: str,
      findings: str,
      impression: str,
      template: Optional[str] = None
  ) -> str:
      """Generate PDF report"""
      from reportlab.lib.pagesizes import letter
      from reportlab.pdfgen import canvas
      import io
      
      buffer = io.BytesIO()
      c = canvas.Canvas(buffer, pagesize=letter)
      
      # Header
      c.setFont("Helvetica-Bold", 16)
      c.drawString(100, 750, "Medical Report")
      c.setFont("Helvetica", 10)
      c.drawString(100, 730, f"Report ID: {report_id}")
      
      # Findings
      c.setFont("Helvetica-Bold", 12)
      c.drawString(100, 700, "Findings:")
      c.setFont("Helvetica", 10)
      
      # Wrap text
      y = 680
      for line in findings.split('\n'):
          if y < 100:  # New page if needed
              c.showPage()
              y = 750
          c.drawString(100, y, line[:80])
          y -= 15
      
      # Impression
      y -= 20
      c.setFont("Helvetica-Bold", 12)
      c.drawString(100, y, "Impression:")
      y -= 20
      c.setFont("Helvetica", 10)
      c.drawString(100, y, impression[:80])
      
      c.save()
      
      # Save PDF to file system
      pdf_path = f"reports/{report_id}.pdf"
      with open(pdf_path, "wb") as f:
          f.write(buffer.getvalue())
      
      return f"/reports/{report_id}.pdf"
  ```

- [ ] Add structured report fields:
  ```python
  async def _generate_structured_report(
      self,
      study_id: str,
      patient_id: str,
      sections: Dict[str, str],  # {"indication": "...", "technique": "...", etc.}
      radiologist_id: str
  ) -> Dict:
      """Generate report with structured sections"""
      findings = "\n\n".join([
          f"{section.upper()}:\n{content}"
          for section, content in sections.items()
      ])
      
      return await self._generate_report(
          study_id=study_id,
          patient_id=patient_id,
          findings=findings,
          impression=sections.get("impression", ""),
          radiologist_id=radiologist_id
      )
  ```

**Deliverables:** Report generation with PDF output

---

### Week 3: Billing Adapter Development

#### Task 3.5: Billing Database Schema Design
**Estimated Time:** 8 hours  
**Priority:** Critical

- [ ] Design billing schema in `database/billing_schema.sql`:
  ```sql
  -- Patients (reference from RIS or duplicate)
  CREATE TABLE IF NOT EXISTS billing_patients (
      patient_id VARCHAR(50) PRIMARY KEY,
      billing_address TEXT,
      insurance_provider VARCHAR(100),
      insurance_policy_number VARCHAR(50),
      payment_method VARCHAR(20) DEFAULT 'insurance'
  );
  
  -- CPT/Procedure codes
  CREATE TABLE IF NOT EXISTS procedure_codes (
      code_id SERIAL PRIMARY KEY,
      cpt_code VARCHAR(10) UNIQUE NOT NULL,
      description TEXT NOT NULL,
      base_price DECIMAL(10, 2) NOT NULL,
      code_category VARCHAR(50),
      active BOOLEAN DEFAULT TRUE
  );
  
  -- Insert common radiology CPT codes
  INSERT INTO procedure_codes (cpt_code, description, base_price, code_category) VALUES
      ('70450', 'CT Head without contrast', 1200.00, 'CT'),
      ('70460', 'CT Head with contrast', 1500.00, 'CT'),
      ('71250', 'CT Chest without contrast', 1400.00, 'CT'),
      ('70551', 'MRI Brain without contrast', 2000.00, 'MRI'),
      ('72148', 'MRI Lumbar Spine without contrast', 2200.00, 'MRI'),
      ('71010', 'Chest X-Ray', 150.00, 'X-Ray'),
      ('73610', 'Ankle X-Ray', 120.00, 'X-Ray')
  ON CONFLICT DO NOTHING;
  
  -- Invoices
  CREATE TABLE IF NOT EXISTS invoices (
      invoice_id SERIAL PRIMARY KEY,
      invoice_number VARCHAR(50) UNIQUE NOT NULL,
      patient_id VARCHAR(50) NOT NULL,
      study_id VARCHAR(100),  -- Link to DICOM study
      accession_number VARCHAR(50),  -- Link to RIS appointment
      invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
      due_date DATE,
      subtotal DECIMAL(10, 2) NOT NULL,
      tax DECIMAL(10, 2) DEFAULT 0.00,
      total_amount DECIMAL(10, 2) NOT NULL,
      amount_paid DECIMAL(10, 2) DEFAULT 0.00,
      balance DECIMAL(10, 2) NOT NULL,
      status VARCHAR(20) DEFAULT 'pending',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT status_check CHECK (status IN ('draft', 'pending', 'sent', 'paid', 'overdue', 'cancelled'))
  );
  
  -- Invoice line items
  CREATE TABLE IF NOT EXISTS invoice_items (
      item_id SERIAL PRIMARY KEY,
      invoice_id INT REFERENCES invoices(invoice_id) ON DELETE CASCADE,
      procedure_code VARCHAR(10) REFERENCES procedure_codes(cpt_code),
      description TEXT NOT NULL,
      quantity INT DEFAULT 1,
      unit_price DECIMAL(10, 2) NOT NULL,
      total_price DECIMAL(10, 2) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Payments
  CREATE TABLE IF NOT EXISTS payments (
      payment_id SERIAL PRIMARY KEY,
      invoice_id INT REFERENCES invoices(invoice_id),
      payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
      amount DECIMAL(10, 2) NOT NULL,
      payment_method VARCHAR(50) NOT NULL,
      transaction_id VARCHAR(100),
      notes TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Insurance claims
  CREATE TABLE IF NOT EXISTS insurance_claims (
      claim_id SERIAL PRIMARY KEY,
      invoice_id INT REFERENCES invoices(invoice_id),
      insurance_provider VARCHAR(100) NOT NULL,
      policy_number VARCHAR(50) NOT NULL,
      claim_number VARCHAR(50) UNIQUE,
      submitted_date DATE,
      status VARCHAR(20) DEFAULT 'draft',
      claim_amount DECIMAL(10, 2),
      approved_amount DECIMAL(10, 2),
      denial_reason TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT claim_status_check CHECK (status IN ('draft', 'submitted', 'pending', 'approved', 'denied', 'appealed'))
  );
  
  -- Indexes
  CREATE INDEX idx_invoices_patient ON invoices(patient_id);
  CREATE INDEX idx_invoices_status ON invoices(status);
  CREATE INDEX idx_invoices_date ON invoices(invoice_date DESC);
  CREATE INDEX idx_claims_status ON insurance_claims(status);
  ```

- [ ] Create migration script `database/setup_billing_db.py`:
  ```python
  import asyncpg
  import asyncio
  
  async def setup_billing_database(db_url: str):
      conn = await asyncpg.connect(db_url)
      
      with open('database/billing_schema.sql', 'r') as f:
          schema_sql = f.read()
      
      await conn.execute(schema_sql)
      print("Billing database schema created successfully")
      
      await conn.close()
  
  if __name__ == "__main__":
      asyncio.run(setup_billing_database(
          "postgresql://billing:billing@localhost/billing"
      ))
  ```

**Deliverables:** Billing database schema with CPT codes

---

#### Task 3.6: Billing Adapter Implementation
**Estimated Time:** 14 hours  
**Priority:** Critical

- [ ] Create `adapters/billing_adapter.py`:
  ```python
  from adapters.base_adapter import ModuleAdapter
  import asyncpg
  from typing import Dict, List, Optional
  from decimal import Decimal
  from datetime import datetime, timedelta
  
  class BillingAdapter(ModuleAdapter):
      """Adapter for Billing/Accounting Module"""
      
      def __init__(self, config: Dict):
          super().__init__(config)
          self.db_url = config["billing_db_url"]
          self.pool: Optional[asyncpg.Pool] = None
      
      async def initialize(self):
          """Create database connection pool"""
          self.pool = await asyncpg.create_pool(
              self.db_url,
              min_size=5,
              max_size=20
          )
          
          async with self.pool.acquire() as conn:
              await conn.fetchval("SELECT 1")
      
      async def health_check(self) -> bool:
          """Check database connectivity"""
          try:
              async with self.pool.acquire() as conn:
                  await conn.fetchval("SELECT 1")
              return True
          except:
              return False
      
      async def invoke_tool(self, tool_name: str, params: Dict) -> Dict:
          """Route tool invocations"""
          tool_map = {
              "billing_create_invoice": self._create_invoice,
              "billing_get_patient_balance": self._get_patient_balance,
              "billing_submit_claim": self._submit_claim,
              "billing_reconcile_payment": self._reconcile_payment,
              "billing_get_invoice": self._get_invoice,
              "billing_search_invoices": self._search_invoices,
          }
          
          if tool_name not in tool_map:
              raise ValueError(f"Unknown billing tool: {tool_name}")
          
          handler = tool_map[tool_name]
          return await handler(**params)
      
      async def shutdown(self):
          """Close database pool"""
          if self.pool:
              await self.pool.close()
  ```

- [ ] Implement invoice creation:
  ```python
  async def _create_invoice(
      self,
      patient_id: str,
      line_items: List[Dict],  # [{"cpt_code": "70450", "quantity": 1, "description": "..."}]
      study_id: Optional[str] = None,
      accession_number: Optional[str] = None,
      due_days: int = 30
  ) -> Dict:
      """
      Create a new invoice
      
      Args:
          patient_id: Patient identifier
          line_items: List of procedure codes and quantities
          study_id: Optional DICOM study UID
          accession_number: Optional RIS accession number
          due_days: Days until invoice is due
      
      Returns:
          invoice_id, invoice_number, total_amount, due_date
      """
      async with self.pool.acquire() as conn:
          # Generate invoice number
          invoice_number = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
          
          # Calculate totals
          subtotal = Decimal('0.00')
          invoice_items_data = []
          
          for item in line_items:
              # Get procedure price
              price_row = await conn.fetchrow(
                  "SELECT base_price FROM procedure_codes WHERE cpt_code = $1",
                  item.get("cpt_code")
              )
              
              if not price_row:
                  raise ValueError(f"Invalid CPT code: {item.get('cpt_code')}")
              
              unit_price = Decimal(str(price_row['base_price']))
              quantity = item.get("quantity", 1)
              total_price = unit_price * quantity
              subtotal += total_price
              
              invoice_items_data.append({
                  "procedure_code": item.get("cpt_code"),
                  "description": item.get("description", ""),
                  "quantity": quantity,
                  "unit_price": unit_price,
                  "total_price": total_price
              })
          
          # Calculate tax (example: 8% sales tax)
          tax = subtotal * Decimal('0.08')
          total_amount = subtotal + tax
          
          # Insert invoice
          invoice_date = datetime.now().date()
          due_date = invoice_date + timedelta(days=due_days)
          
          invoice_id = await conn.fetchval("""
              INSERT INTO invoices (
                  invoice_number, patient_id, study_id, accession_number,
                  invoice_date, due_date, subtotal, tax, total_amount,
                  balance, status
              )
              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
              RETURNING invoice_id
          """, invoice_number, patient_id, study_id, accession_number,
               invoice_date, due_date, subtotal, tax, total_amount,
               total_amount, "pending")
          
          # Insert line items
          for item_data in invoice_items_data:
              await conn.execute("""
                  INSERT INTO invoice_items (
                      invoice_id, procedure_code, description,
                      quantity, unit_price, total_price
                  )
                  VALUES ($1, $2, $3, $4, $5, $6)
              """, invoice_id, item_data["procedure_code"],
                   item_data["description"], item_data["quantity"],
                   item_data["unit_price"], item_data["total_price"])
          
          return {
              "invoice_id": invoice_id,
              "invoice_number": invoice_number,
              "subtotal": float(subtotal),
              "tax": float(tax),
              "total_amount": float(total_amount),
              "due_date": due_date.isoformat(),
              "status": "pending"
          }
  ```

- [ ] Implement payment reconciliation:
  ```python
  async def _reconcile_payment(
      self,
      invoice_id: int,
      payment_amount: float,
      payment_method: str,
      transaction_id: Optional[str] = None,
      notes: Optional[str] = None
  ) -> Dict:
      """
      Record a payment against an invoice
      
      Returns:
          payment_id, remaining_balance, invoice_status
      """
      async with self.pool.acquire() as conn:
          # Get current invoice balance
          invoice = await conn.fetchrow(
              "SELECT total_amount, amount_paid, balance FROM invoices WHERE invoice_id = $1",
              invoice_id
          )
          
          if not invoice:
              raise ValueError(f"Invoice {invoice_id} not found")
          
          # Record payment
          payment_id = await conn.fetchval("""
              INSERT INTO payments (
                  invoice_id, amount, payment_method, transaction_id, notes
              )
              VALUES ($1, $2, $3, $4, $5)
              RETURNING payment_id
          """, invoice_id, payment_amount, payment_method, transaction_id, notes)
          
          # Update invoice
          new_amount_paid = Decimal(str(invoice['amount_paid'])) + Decimal(str(payment_amount))
          new_balance = Decimal(str(invoice['total_amount'])) - new_amount_paid
          
          new_status = "paid" if new_balance <= 0 else "pending"
          
          await conn.execute("""
              UPDATE invoices
              SET amount_paid = $1, balance = $2, status = $3
              WHERE invoice_id = $4
          """, new_amount_paid, new_balance, new_status, invoice_id)
          
          return {
              "payment_id": payment_id,
              "amount_paid": float(payment_amount),
              "remaining_balance": float(new_balance),
              "invoice_status": new_status
          }
  ```

**Deliverables:** Billing adapter with invoice and payment tools

---

### Week 4: Integration & Testing

#### Task 3.7: Register Tools with MCP Server
**Estimated Time:** 4 hours  
**Priority:** High  
**Collaboration:** Work with Dev 1

- [ ] Create tool definitions JSON files:
  - [ ] `adapters/reporting_tools.json`
  - [ ] `adapters/billing_tools.json`

- [ ] Register adapters in `server/main.py`:
  ```python
  from adapters.reporting_adapter import ReportingAdapter
  from adapters.billing_adapter import BillingAdapter
  
  @app.on_event("startup")
  async def startup():
      # Register reporting adapter
      reporting_adapter = ReportingAdapter(config)
      await reporting_adapter.initialize()
      # ... register tools
      
      # Register billing adapter
      billing_adapter = BillingAdapter(config)
      await billing_adapter.initialize()
      # ... register tools
  ```

**Deliverables:** Adapters registered with MCP server

---

#### Task 3.8: Cross-Module Integration Testing
**Estimated Time:** 12 hours  
**Priority:** Critical

- [ ] Test end-to-end workflow:
  ```python
  @pytest.mark.asyncio
  async def test_complete_patient_workflow():
      """
      Test complete workflow:
      1. Schedule appointment (RIS)
      2. Perform study (PACS)
      3. Transcribe and generate report (Reporting)
      4. Create invoice (Billing)
      5. Record payment (Billing)
      """
      # Step 1: Schedule
      appointment = await ris_adapter.invoke_tool(
          "ris_schedule_appointment",
          {
              "patient_id": "P00001",
              "modality": "CT",
              "requested_date": "2025-10-15T09:00:00"
          }
      )
      
      # Step 2: Upload study (mock)
      study_uid = "1.2.3.4.5"
      
      # Step 3: Generate report
      report = await reporting_adapter.invoke_tool(
          "reporting_generate_report",
          {
              "study_id": study_uid,
              "patient_id": "P00001",
              "findings": "No acute findings",
              "impression": "Normal CT chest",
              "radiologist_id": "RAD001"
          }
      )
      
      # Step 4: Create invoice
      invoice = await billing_adapter.invoke_tool(
          "billing_create_invoice",
          {
              "patient_id": "P00001",
              "line_items": [
                  {"cpt_code": "71250", "quantity": 1, "description": "CT Chest"}
              ],
              "study_id": study_uid,
              "accession_number": appointment["accession_number"]
          }
      )
      
      # Step 5: Record payment
      payment = await billing_adapter.invoke_tool(
          "billing_reconcile_payment",
          {
              "invoice_id": invoice["invoice_id"],
              "payment_amount": invoice["total_amount"],
              "payment_method": "insurance"
          }
      )
      
      assert payment["invoice_status"] == "paid"
  ```

- [ ] Test report → billing automation:
  ```python
  async def test_auto_billing_from_report():
      """Verify that completing a report can trigger invoice creation"""
      # This would be implemented as an event listener in production
      pass
  ```

**Deliverables:** Complete integration test suite

---

## Phase 2: Enhancement (Weeks 5-8)

### Week 5-6: Advanced Reporting Features

#### Task 3.9: Report Templates System
**Estimated Time:** 10 hours  
**Priority:** Medium

- [ ] Implement template management:
  ```python
  async def _get_templates(
      self,
      report_type: Optional[str] = None
  ) -> Dict:
      """Get available report templates"""
      query = "SELECT * FROM report_templates"
      params = []
      
      if report_type:
          query += " WHERE report_type = ?"
          params.append(report_type)
      
      cursor = await self.db.execute(query, params)
      rows = await cursor.fetchall()
      
      templates = [
          {
              "template_id": row[0],
              "name": row[1],
              "report_type": row[2],
              "content": row[3]
          }
          for row in rows
      ]
      
      return {"templates": templates, "count": len(templates)}
  ```

- [ ] Add template creation tool:
  ```python
  async def _create_template(
      self,
      name: str,
      report_type: str,
      content: str
  ) -> Dict:
      """Create a new report template"""
      cursor = await self.db.execute("""
          INSERT INTO report_templates (name, report_type, content)
          VALUES (?, ?, ?)
      """, (name, report_type, content))
      
      await self.db.commit()
      
      return {
          "template_id": cursor.lastrowid,
          "name": name
      }
  ```

**Deliverables:** Template management system

---

#### Task 3.10: Voice Recording Storage
**Estimated Time:** 8 hours  
**Priority:** Low

- [ ] Add database table for voice recordings:
  ```sql
  CREATE TABLE IF NOT EXISTS voice_recordings (
      recording_id INTEGER PRIMARY KEY AUTOINCREMENT,
      report_id TEXT,
      audio_file_path TEXT NOT NULL,
      duration_seconds REAL,
      transcription_status TEXT DEFAULT 'pending',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

- [ ] Implement recording storage:
  ```python
  async def _store_voice_recording(
      self,
      audio_data: bytes,
      report_id: Optional[str] = None
  ) -> Dict:
      """Store voice recording for audit trail"""
      import hashlib
      
      # Generate filename
      file_hash = hashlib.md5(audio_data).hexdigest()
      filename = f"recordings/{file_hash}.wav"
      
      # Save file
      with open(filename, "wb") as f:
          f.write(audio_data)
      
      # Store metadata
      await self.db.execute("""
          INSERT INTO voice_recordings (report_id, audio_file_path)
          VALUES (?, ?)
      """, (report_id, filename))
      await self.db.commit()
      
      return {"recording_path": filename}
  ```

**Deliverables:** Voice recording audit trail

---

### Week 7-8: Billing Enhancements

#### Task 3.11: Insurance Claims Processing
**Estimated Time:** 12 hours  
**Priority:** High

- [ ] Implement claim submission:
  ```python
  async def _submit_claim(
      self,
      patient_id: str,
      insurance_provider: str,
      policy_number: str,
      procedure_codes: List[str],
      diagnosis_codes: Optional[List[str]] = None
  ) -> Dict:
      """
      Submit insurance claim for procedures
      
      Returns:
          claim_id, claim_number, status
      """
      async with self.pool.acquire() as conn:
          # Create invoice first (if not exists)
          line_items = [
              {"cpt_code": code, "quantity": 1}
              for code in procedure_codes
          ]
          
          invoice = await self._create_invoice(
              patient_id=patient_id,
              line_items=line_items
          )
          
          # Generate claim number
          claim_number = f"CLM{datetime.now().strftime('%Y%m%d%H%M%S')}"
          
          # Insert claim
          claim_id = await conn.fetchval("""
              INSERT INTO insurance_claims (
                  invoice_id, insurance_provider, policy_number,
                  claim_number, claim_amount, status
              )
              VALUES ($1, $2, $3, $4, $5, $6)
              RETURNING claim_id
          """, invoice["invoice_id"], insurance_provider, policy_number,
               claim_number, invoice["total_amount"], "submitted")
          
          # In production, integrate with clearinghouse API here
          # await self._send_to_clearinghouse(claim_id, ...)
          
          return {
              "claim_id": claim_id,
              "claim_number": claim_number,
              "invoice_id": invoice["invoice_id"],
              "claim_amount": invoice["total_amount"],
              "status": "submitted"
          }
  ```

**Deliverables:** Insurance claims workflow

---

## Phase 3: Production (Weeks 9-12)

### Week 9-10: Financial Reporting

#### Task 3.12: Revenue Analytics
**Estimated Time:** 10 hours  
**Priority:** Medium

- [ ] Implement revenue reports:
  ```python
  async def _get_revenue_summary(
      self,
      start_date: str,
      end_date: str,
      group_by: str = "day"  # day, week, month
  ) -> Dict:
      """Get revenue summary for date range"""
      async with self.pool.acquire() as conn:
          query = """
              SELECT
                  DATE_TRUNC($1, invoice_date) AS period,
                  COUNT(*) AS invoice_count,
                  SUM(total_amount) AS total_revenue,
                  SUM(amount_paid) AS total_paid,
                  SUM(balance) AS total_outstanding
              FROM invoices
              WHERE invoice_date BETWEEN $2 AND $3
              GROUP BY period
              ORDER BY period
          """
          
          rows = await conn.fetch(query, group_by, start_date, end_date)
          
          summary = [
              {
                  "period": str(row['period']),
                  "invoice_count": row['invoice_count'],
                  "total_revenue": float(row['total_revenue']),
                  "total_paid": float(row['total_paid']),
                  "total_outstanding": float(row['total_outstanding'])
              }
              for row in rows
          ]
          
          return {"summary": summary}
  ```

**Deliverables:** Financial reporting tools

---

### Week 11-12: Documentation & Polish

#### Task 3.13: Complete Documentation
**Estimated Time:** 8 hours  
**Priority:** High

- [ ] Create `docs/REPORTING_ADAPTER_GUIDE.md`
- [ ] Create `docs/BILLING_ADAPTER_GUIDE.md`
- [ ] Create workflow diagrams
- [ ] Document CPT codes and billing rules
- [ ] Create example scripts

**Deliverables:** Complete adapter documentation

---

## Success Metrics

- ✅ Reporting adapter can transcribe and generate reports
- ✅ Billing adapter can create invoices and process payments
- ✅ Integration tests for cross-module workflows passing
- ✅ 80%+ code coverage

---

**Good luck, Developer 3! You're building the clinical and financial workflows. 💼**
