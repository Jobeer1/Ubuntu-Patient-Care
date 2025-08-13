## Secure Active Directory Integration & User Management for PACS

### Goals
- Integrate a robust, efficient, and accurate Active Directory (AD) or LDAP system with Orthanc PACS for user authentication and access control.
- Make user and access management extremely easy for admins, but with strong security (multi-factor authentication, role-based access, audit logging).
- Ensure only authorized users can access patient data and images, with all actions logged for POPI compliance.
- Images should be rendered using host/user resources (client-side rendering) to optimize performance and privacy.
- Reports must be attached to images in the PACS, and sharing must be possible via secure, expiring links so patients can only access their own images and reports.

### Implementation Steps
1. **Active Directory/LDAP Integration**
  - Integrate Orthanc PACS with AD/LDAP for single sign-on (SSO) and centralized user management.
  - Support for multi-factor authentication (MFA) for all admin and clinical users.
  - Map AD groups to system roles (admin, radiologist, transcriptionist, billing, patient).
2. **User & Access Management**
  - Build or configure an admin UI for adding/removing users, assigning roles, and setting access to patient data.
  - All changes to users/roles are logged and require MFA for approval.
  - Provide easy bulk user import (CSV/Excel) for onboarding.
3. **Image Rendering**
  - Use client-side rendering (e.g., Cornerstone.js) for DICOM images in the viewer, leveraging the user's device for performance and privacy.
  - Ensure server never sends images to unauthorized users; all access is checked against AD roles.
4. **Secure Report Attachment & Sharing**
  - Attach finalized reports to DICOM studies in Orthanc.
  - Generate secure, expiring links for patients to view only their own images and reports (one-time access, strong encryption, audit logging).
  - Optionally, allow doctors to share images/reports with referring physicians via secure links.
5. **Compliance & Audit**
  - All access and sharing actions are logged for POPI Act compliance.
  - Regularly review access logs and test for unauthorized access.

### Success Criteria
- Admins can easily and securely manage users and access rights.
- Only authorized users can access patient data and images.
- Images are rendered efficiently on user devices.
- Patients can securely access only their own images and reports via expiring links.
- All actions are logged and system passes compliance review.
## Real-World Reporting & Billing Workflow (South African Radiology)

### Reporting & Authorisation
1. **Doctor Dictation:** Doctor creates a report using voice dictation (STT) or keyboard in the reporting module.
2. **Transcription Review:** The draft report is sent to a team of three transcriptionists who review and correct the STT output for medical accuracy and terminology, especially for complex South African medical terms.
3. **Doctor Proofreading & Authorisation:** The corrected report is sent back to the doctor for final proofreading and digital authorisation/sign-off.
4. **Billing Team Processing:** Once authorised, the report is sent to the billing team to assign fees and submit claims to medical schemes, ensuring compliance with local billing codes and requirements.

This workflow ensures high-quality, accurate reports and proper billing, tailored for South African radiology practice. All steps are logged for audit and POPI compliance.
# Ubuntu Patient Sorg – Step-by-Step Project Plan


## Project Overview

**Goal:**
Create a robust, offline-first medical software suite for South African radiology practices. The system will combine patient management (OpenEMR), image storage (Orthanc PACS), a DICOM viewer, local billing logic, and compliance features. It must work without internet, be easy to install, and meet all local legal and billing requirements.

**Team (2 Developers):**
- **Developer 1:** User interface, OpenEMR customization, dashboards
- **Developer 2:** Backend, integration, billing, compliance, deployment

---


## Module 1: Foundation & Workflow (Offline-First)

### 1.1 Design Offline-First Data Sync
**Owner:** Developer 2

**Steps:**
1. Choose a local database (e.g., SQLite for simplicity, or CouchDB for built-in sync).
2. Sketch out what data must be available offline (patients, appointments, images, billing, logs).
3. Implement a sync service:
   - When online, push/pull changes to a central server.
   - When offline, queue changes locally.
   - On reconnect, resolve conflicts (last-write-wins or prompt user).
4. Test by simulating network loss and recovery.

**Success:**
- All data is usable offline and syncs automatically when online, with no data loss.

---

### 1.2 Containerize OpenEMR & Orthanc
**Owner:** Developer 2

**Steps:**
1. Write Dockerfiles for OpenEMR and Orthanc (use official images as base).
2. Create a `docker-compose.yml` to run both with correct networking.
3. Add persistent storage volumes for databases and images.
4. Test: `docker-compose up` should start both services, accessible via browser.
5. Write a simple setup guide for users.

**Success:**
- Both services run locally with one command, and data persists after restart.

---

### 1.3 Customize OpenEMR for Local Radiology
**Owner:** Developer 1
**Depends on:** 1.1

**Steps:**
1. List all fields and workflows needed for South African radiology (consult with users if possible).
2. Modify OpenEMR forms and appointment logic to match local needs (e.g., add NRPL fields, custom statuses).
3. Remove or hide irrelevant features.
4. Test with sample patient journeys.

**Success:**
- Patient and appointment screens are simple, relevant, and match local workflow.

---

### 1.4 Build a Visual Dashboard/Worklist
**Owner:** Developer 1
**Depends on:** 1.3

**Steps:**
1. Design a simple dashboard showing all patients and their status (waiting, scanned, reported, etc.).
2. Use a modern JS framework (React or Vue) for the UI.
3. Connect to OpenEMR via API to fetch and update patient status.
4. Add filters/search for quick navigation.
5. Test with real data and get user feedback.

**Success:**
- Staff can see and update patient status in real time, with no confusion.

---


## Module 2: DICOM Viewer & PACS Integration

### 2.1 Integrate an Offline DICOM Viewer
**Owner:** Developer 1
**Depends on:** 1.2

**Steps:**
1. Evaluate open-source DICOM viewers (OHIF, DWV) for offline use.
2. Set up the viewer to run locally in the browser.
3. Connect the viewer to Orthanc using its REST API to fetch images.
4. Test loading studies with no internet connection.

**Success:**
- Users can view DICOM images from Orthanc even when offline.

---

### 2.2 Auto-Update Patient Status on New Study
**Owner:** Developer 2
**Depends on:** 1.4, 2.1

**Steps:**
1. Write a plugin or script for Orthanc to detect new image uploads.
2. When a new study arrives, call OpenEMR's API to update the patient's status (e.g., "Imaging Complete").
3. Log all updates for audit purposes.
4. Test by uploading new studies and checking dashboard updates.

**Success:**
- Patient status updates automatically when new images are received.

---

### 2.3 Prevent Image/Patient Mismatches
**Owner:** Developer 2
**Depends on:** 2.2

**Steps:**
1. On new study upload, extract patient info from DICOM metadata.
2. Cross-check with OpenEMR patient records (name, ID, date of birth).
3. If mismatch, flag for manual review and log the event.
4. Test with both correct and incorrect data.

**Success:**
- All images are correctly linked to patients; mismatches are caught early.

---


## Module 3: South African Billing & Compliance

### 3.1 Add Local Billing Codes to OpenEMR
**Owner:** Developer 2
**Depends on:** 1.1

**Steps:**
1. Gather all required codes (ICD-10, NRPL, etc.) from official sources.
2. Create or update OpenEMR database tables to store these codes.
3. Update billing forms to use dropdowns/search for these codes.
4. Test by entering real billing scenarios.

**Success:**
- All codes are available and used in daily billing.

---

### 3.2 Generate Invoices & Claims for SA Medical Aids
**Owner:** Developer 2
**Depends on:** 3.1

**Steps:**
1. Research file formats and requirements for major medical aids (e.g., Discovery, GEMS, Workman's Comp).
2. Write code to generate invoices and claims in these formats from OpenEMR data.
3. Add a button or automation to generate and export these files after a report is finalized.
4. Test by submitting files to test portals or with real payers.

**Success:**
- Claims are accepted by medical aids with no manual rework.

---

### 3.3 Ensure POPI Act Compliance
**Owner:** Developer 2
**Depends on:** 1.1

**Steps:**
1. Encrypt all patient data at rest (use database encryption features or file-level encryption).
2. Use HTTPS for all data in transit.
3. Add logging for all data access and changes (who, what, when).
4. Add a consent management screen for patients.
5. Regularly review logs and test for compliance.

**Success:**
- Data is secure, access is tracked, and the system passes a compliance review.

---


## Collaboration & Progress Tracking

To ensure smooth collaboration and progress tracking among developers, the following practices and tools should be implemented:

### 1. Use a Shared Project Management Tool
- **Tool Options:** GitHub Projects, Jira, Trello, or Asana.
- **Setup:**
  1. Create a project board with columns such as "To Do," "In Progress," "In Review," and "Done."
  2. Add all tasks from this plan as individual cards or issues.
  3. Assign each task to the responsible developer (e.g., Developer 1 or Developer 2).
  4. Add due dates and dependencies to each task.

### 2. Regular Stand-Up Meetings
- **Frequency:** Daily or bi-weekly.
- **Purpose:**
  1. Share updates on completed tasks.
  2. Discuss blockers or challenges.
  3. Plan the next steps collaboratively.

### 3. Code Reviews and Pull Requests
- **Process:**
  1. Each developer works on a separate branch for their assigned tasks.
  2. Submit a pull request (PR) when a task is complete.
  3. The other developer reviews the PR for quality, functionality, and adherence to the plan.
  4. Merge the PR only after approval.

### 4. Shared Documentation
- **Tool Options:** Confluence, Notion, or a shared Markdown repository.
- **Content:**
  1. Document all decisions, workflows, and technical details.
  2. Maintain a changelog to track updates to the plan or codebase.

### 5. Progress Tracking Metrics
- **Metrics to Track:**
  1. Number of tasks completed vs. pending.
  2. Average time taken per task.
  3. Number of bugs or issues resolved.
- **Tools:** Use built-in reporting features in the project management tool or a custom dashboard.

### 6. Communication Channels
- **Tool Options:** Slack, Microsoft Teams, or Discord.
- **Best Practices:**
  1. Create channels for general updates, specific modules, and urgent issues.
  2. Use threads to keep discussions organized.

### 7. Testing and Feedback Cycles
- **Process:**
  1. After completing a module, conduct joint testing sessions.
  2. Log all feedback and bugs in the project management tool.
  3. Assign fixes to the responsible developer.

By following these practices, developers can collaborate effectively, track each other's progress, and ensure the project stays on schedule.

---

## Notes & Best Practices

- Track all tasks in a project board (GitHub Projects, Jira, or Trello).
- Do regular code reviews and test each feature with real users if possible.
- Write clear documentation for setup and daily use.
- Keep all code open-source and easy to audit.
