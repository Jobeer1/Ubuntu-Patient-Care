-- =====================================================
-- Medical Billing Module - Database Schema
-- For Gift of the Givers - Offline-First Sustainability
-- =====================================================

-- =====================================================
-- INSURANCE COMPANY DATA
-- =====================================================
CREATE TABLE IF NOT EXISTS insurance_companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    region TEXT,
    website TEXT,
    portal_url TEXT,
    claim_email TEXT,
    api_endpoint TEXT,
    supported_formats TEXT,  -- JSON: ["CMS-1500", "EDI", "WEB_PORTAL", "EMAIL"]
    llm_scraper_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PATIENT INSURANCE INFORMATION
-- =====================================================
CREATE TABLE IF NOT EXISTS patient_insurance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL UNIQUE,
    insurance_company_id TEXT NOT NULL,
    policy_number TEXT NOT NULL,
    group_number TEXT,
    member_id TEXT,
    plan_name TEXT,
    plan_type TEXT,  -- HMO, PPO, MEDICAID, MEDICARE, etc.
    effective_date DATE,
    termination_date DATE,
    verification_status TEXT,  -- VERIFIED, PENDING, FAILED, MANUAL
    verification_method TEXT,  -- LLM_SCRAPED, WEBSITE, API, MANUAL
    last_verified TIMESTAMP,
    verification_confidence FLOAT,
    data_source TEXT,  -- JSON of all sources that contributed
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (insurance_company_id) REFERENCES insurance_companies(id)
);

-- =====================================================
-- PATIENT INSURANCE BENEFITS
-- =====================================================
CREATE TABLE IF NOT EXISTS patient_benefits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_insurance_id INTEGER NOT NULL,
    service_category TEXT,  -- EMERGENCY, INPATIENT, OUTPATIENT, LAB, IMAGING, etc.
    copay DECIMAL(10,2),
    coinsurance_percent DECIMAL(5,2),
    deductible DECIMAL(10,2),
    deductible_met DECIMAL(10,2),
    out_of_pocket_max DECIMAL(10,2),
    out_of_pocket_met DECIMAL(10,2),
    coverage_percent DECIMAL(5,2),  -- 0-100
    pre_authorization_required BOOLEAN,
    prior_auth_days_allowed INTEGER,
    network_restrictions TEXT,  -- IN_NETWORK_ONLY, OUT_OF_NETWORK_OK
    exclusions TEXT,  -- JSON list of excluded services
    effective_date DATE,
    extracted_from TEXT,  -- Document/URL where benefits were extracted
    extraction_method TEXT,  -- LLM_SCRAPED, MANUAL, API
    extraction_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_insurance_id) REFERENCES patient_insurance(id)
);

-- =====================================================
-- INSURANCE VERIFICATION ATTEMPTS
-- =====================================================
CREATE TABLE IF NOT EXISTS verification_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_insurance_id INTEGER NOT NULL,
    attempt_method TEXT,  -- WEB_SCRAPE, API, MANUAL, WEBSITE_FORM
    attempt_url TEXT,
    request_data TEXT,  -- JSON of what was sent
    response_data TEXT,  -- JSON of what was received
    success BOOLEAN,
    error_message TEXT,
    confidence_score FLOAT,
    llm_model_used TEXT,  -- claude-3, gpt-4, etc.
    extraction_time_seconds FLOAT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- CLAIMS
-- =====================================================
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL UNIQUE,  -- Unique identifier for this claim
    patient_id TEXT NOT NULL,
    patient_insurance_id INTEGER NOT NULL,
    service_date DATE NOT NULL,
    service_description TEXT,
    service_codes TEXT,  -- JSON: [{"code": "CPT-99213", "description": "Office visit", "charge": 150}]
    total_charge DECIMAL(10,2),
    insurance_payment_estimate DECIMAL(10,2),
    patient_responsibility DECIMAL(10,2),
    copay DECIMAL(10,2),
    coinsurance DECIMAL(10,2),
    deductible_applied DECIMAL(10,2),
    claim_status TEXT,  -- DRAFT, QUEUED_OFFLINE, SUBMITTED, PENDING, APPROVED, DENIED, PARTIAL
    submission_method TEXT,  -- CMS_1500_EMAIL, WEB_PORTAL, TELEHEALTH_API, MANUAL
    provider_portal_url TEXT,
    submission_url TEXT,
    claim_number TEXT,
    diagnosis_codes TEXT,  -- JSON: [{"code": "ICD10-E11", "description": "Type 2 diabetes"}]
    provider_npi TEXT,
    provider_name TEXT,
    provider_taxonomy TEXT,
    claim_form_data TEXT,  -- Full CMS-1500 or other form as JSON
    submission_attempts INTEGER DEFAULT 0,
    last_submission_attempt TIMESTAMP,
    next_retry_at TIMESTAMP,
    submitted_at TIMESTAMP,
    expected_payment_date DATE,
    actual_payment_received DECIMAL(10,2),
    payment_received_date DATE,
    denial_reason TEXT,
    offline_synced_at TIMESTAMP,  -- When synced from disaster zone
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,  -- Clinic/staff ID that created claim
    FOREIGN KEY (patient_insurance_id) REFERENCES patient_insurance(id)
);

-- =====================================================
-- OFFLINE CLAIM QUEUE
-- =====================================================
CREATE TABLE IF NOT EXISTS offline_claim_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT,  -- PENDING, SYNCED, FAILED
    sync_attempts INTEGER DEFAULT 0,
    last_sync_attempt TIMESTAMP,
    last_sync_error TEXT,
    synced_at TIMESTAMP,
    clinic_id TEXT,  -- Source clinic that created it
    FOREIGN KEY (claim_id) REFERENCES claims(id)
);

-- =====================================================
-- CLAIM SUBMISSIONS LOG
-- =====================================================
CREATE TABLE IF NOT EXISTS claim_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    submission_method TEXT,
    target_url TEXT,
    submission_timestamp TIMESTAMP,
    http_status_code INTEGER,
    response_body TEXT,
    submission_success BOOLEAN,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claim_id) REFERENCES claims(id)
);

-- =====================================================
-- REVENUE TRACKING FOR SUSTAINABILITY
-- =====================================================
CREATE TABLE IF NOT EXISTS revenue_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id INTEGER NOT NULL,
    billing_month DATE,
    total_charge DECIMAL(10,2),
    insurance_payment DECIMAL(10,2),
    payment_status TEXT,  -- PENDING, RECEIVED, WRITTEN_OFF
    payment_date DATE,
    gift_of_givers_share DECIMAL(10,2),  -- Amount allocated to GOTG
    share_percentage DECIMAL(5,2),  -- Percentage of payment going to GOTG
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (claim_id) REFERENCES claims(id)
);

-- =====================================================
-- DATA SYNC LOG WITH OTHER MODULES
-- =====================================================
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT NOT NULL UNIQUE,
    module_source TEXT,  -- BILLING, RIS, PACS, DICTATION
    module_target TEXT,
    data_type TEXT,  -- PATIENT, CLAIM, PROCEDURE, IMAGING, REPORT
    record_count INTEGER,
    sync_direction TEXT,  -- PUSH, PULL, BIDIRECTIONAL
    sync_status TEXT,  -- PENDING, IN_PROGRESS, SUCCESS, FAILED
    payload_size_kb FLOAT,
    compression_ratio FLOAT,
    sync_started_at TIMESTAMP,
    sync_completed_at TIMESTAMP,
    error_message TEXT,
    offline_synced BOOLEAN DEFAULT 0,
    synced_from_clinic TEXT,  -- Which clinic this sync originated from
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- MULTIMODULE DATA MAPPING
-- =====================================================
CREATE TABLE IF NOT EXISTS module_data_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billing_patient_id TEXT NOT NULL,
    ris_patient_id TEXT,
    pacs_patient_id TEXT,
    dictation_patient_id TEXT,
    mapping_status TEXT,  -- MATCHED, PENDING, CONFLICT
    last_matched_at TIMESTAMP,
    matching_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_patient_insurance_patient_id ON patient_insurance(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_insurance_company ON patient_insurance(insurance_company_id);
CREATE INDEX IF NOT EXISTS idx_patient_benefits_insurance ON patient_benefits(patient_insurance_id);
CREATE INDEX IF NOT EXISTS idx_claims_patient_id ON claims(patient_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(claim_status);
CREATE INDEX IF NOT EXISTS idx_claims_service_date ON claims(service_date);
CREATE INDEX IF NOT EXISTS idx_offline_queue_status ON offline_claim_queue(sync_status);
CREATE INDEX IF NOT EXISTS idx_sync_log_modules ON sync_log(module_source, module_target);
CREATE INDEX IF NOT EXISTS idx_revenue_tracking_month ON revenue_tracking(billing_month);
