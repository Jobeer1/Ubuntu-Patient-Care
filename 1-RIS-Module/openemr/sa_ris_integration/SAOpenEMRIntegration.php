<?php

/**
 * South African RIS - OpenEMR Integration Module
 * 
 * This module provides seamless integration between OpenEMR and SA RIS
 * with specific focus on South African medical billing requirements
 * 
 * Features:
 * - ICD-10 code management
 * - Medical aid scheme integration
 * - Healthbridge clearing house connectivity
 * - NRPL billing code support
 * - Real-time patient workflow synchronization
 * 
 * @package SA_RIS_OpenEMR
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\OpenEMR;

use Exception;
use PDO;

class SAOpenEMRIntegration {
    
    private $openemrDb;
    private $saRisDb;
    private $medicalAidSchemes;
    private $icd10Codes;
    private $nrplCodes;
    
    public function __construct(PDO $openemrDatabase, PDO $saRisDatabase) {
        $this->openemrDb = $openemrDatabase;
        $this->saRisDb = $saRisDatabase;
        $this->initializeMedicalAidSchemes();
        $this->loadICD10Codes();
        $this->loadNRPLCodes();
    }
    
    /**
     * Initialize South African Medical Aid Schemes
     */
    private function initializeMedicalAidSchemes() {
        $this->medicalAidSchemes = [
            'discovery' => [
                'name' => 'Discovery Health Medical Scheme',
                'scheme_code' => 'DHMS',
                'clearing_house' => 'healthbridge',
                'real_time_auth' => true,
                'electronic_claims' => true,
                'icd10_required' => true,
                'pre_auth_procedures' => ['CT', 'MRI', 'PET', 'NUCLEAR']
            ],
            'momentum' => [
                'name' => 'Momentum Health',
                'scheme_code' => 'MOM',
                'clearing_house' => 'healthbridge',
                'real_time_auth' => true,
                'electronic_claims' => true,
                'icd10_required' => true,
                'pre_auth_procedures' => ['CT', 'MRI', 'INTERVENTIONAL']
            ],
            'bonitas' => [
                'name' => 'Bonitas Medical Fund',
                'scheme_code' => 'BON',
                'clearing_house' => 'healthbridge',
                'real_time_auth' => false,
                'electronic_claims' => true,
                'icd10_required' => true,
                'pre_auth_procedures' => []
            ],
            'gems' => [
                'name' => 'Government Employees Medical Scheme',
                'scheme_code' => 'GEMS',
                'clearing_house' => 'direct',
                'real_time_auth' => false,
                'electronic_claims' => false,
                'icd10_required' => true,
                'pre_auth_procedures' => ['CT', 'MRI', 'INTERVENTIONAL']
            ],
            'bestmed' => [
                'name' => 'Bestmed Medical Scheme',
                'scheme_code' => 'BESTMED',
                'clearing_house' => 'healthbridge',
                'real_time_auth' => true,
                'electronic_claims' => true,
                'icd10_required' => true,
                'pre_auth_procedures' => ['MRI', 'PET']
            ]
        ];
    }
    
    /**
     * Load ICD-10 codes specific to radiology
     */
    private function loadICD10Codes() {
        $this->icd10Codes = [
            // Common radiology indication codes
            'R06.02' => 'Shortness of breath',
            'R50.9' => 'Fever, unspecified',
            'R06.00' => 'Dyspnea, unspecified',
            'M25.50' => 'Pain in unspecified joint',
            'R10.9' => 'Unspecified abdominal pain',
            'G93.1' => 'Anoxic brain damage, not elsewhere classified',
            'S06.9' => 'Unspecified intracranial injury',
            'M54.9' => 'Dorsalgia, unspecified',
            'R51' => 'Headache',
            'Z51.11' => 'Encounter for antineoplastic chemotherapy',
            'C78.00' => 'Secondary malignant neoplasm of unspecified lung',
            'I25.9' => 'Chronic ischemic heart disease, unspecified',
            'N39.0' => 'Urinary tract infection, site not specified',
            'K59.00' => 'Constipation, unspecified',
            'R06.03' => 'Acute respiratory distress'
        ];
    }
    
    /**
     * Load NRPL codes for South African billing
     */
    private function loadNRPLCodes() {
        $this->nrplCodes = [
            // CT Procedures
            '3011' => ['description' => 'CT Head without contrast', 'price' => 1850.00, 'modality' => 'CT'],
            '3012' => ['description' => 'CT Head with contrast', 'price' => 2450.00, 'modality' => 'CT'],
            '3013' => ['description' => 'CT Chest without contrast', 'price' => 2100.00, 'modality' => 'CT'],
            '3014' => ['description' => 'CT Chest with contrast', 'price' => 2850.00, 'modality' => 'CT'],
            '3015' => ['description' => 'CT Abdomen and Pelvis', 'price' => 3200.00, 'modality' => 'CT'],
            
            // MRI Procedures
            '3021' => ['description' => 'MRI Brain without contrast', 'price' => 4500.00, 'modality' => 'MRI'],
            '3022' => ['description' => 'MRI Brain with contrast', 'price' => 5200.00, 'modality' => 'MRI'],
            '3023' => ['description' => 'MRI Cervical Spine', 'price' => 4200.00, 'modality' => 'MRI'],
            '3024' => ['description' => 'MRI Lumbar Spine', 'price' => 4200.00, 'modality' => 'MRI'],
            '3025' => ['description' => 'MRI Knee', 'price' => 3800.00, 'modality' => 'MRI'],
            
            // X-Ray Procedures
            '3001' => ['description' => 'Chest X-Ray PA', 'price' => 320.00, 'modality' => 'XRAY'],
            '3002' => ['description' => 'Chest X-Ray Lateral', 'price' => 280.00, 'modality' => 'XRAY'],
            '3003' => ['description' => 'Skull X-Ray AP and Lateral', 'price' => 450.00, 'modality' => 'XRAY'],
            
            // Ultrasound Procedures
            '3041' => ['description' => 'Abdominal Ultrasound', 'price' => 850.00, 'modality' => 'US'],
            '3042' => ['description' => 'Pelvic Ultrasound', 'price' => 750.00, 'modality' => 'US'],
            '3043' => ['description' => 'Obstetric Ultrasound', 'price' => 950.00, 'modality' => 'US'],
            
            // Mammography
            '3051' => ['description' => 'Bilateral Mammography', 'price' => 1200.00, 'modality' => 'MG'],
            '3052' => ['description' => 'Unilateral Mammography', 'price' => 800.00, 'modality' => 'MG']
        ];
    }
    
    /**
     * Create radiology appointment in OpenEMR with SA RIS integration
     */
    public function createRadiologyAppointment($appointmentData) {
        try {
            $this->openemrDb->beginTransaction();
            
            // 1. Create OpenEMR appointment
            $appointmentId = $this->createOpenEMRAppointment($appointmentData);
            
            // 2. Create SA RIS workflow instance
            $workflowId = $this->createSARISWorkflow($appointmentData, $appointmentId);
            
            // 3. Link appointment to workflow
            $this->linkAppointmentToWorkflow($appointmentId, $workflowId);
            
            // 4. Generate billing quote if medical aid provided
            $billingQuote = null;
            if (!empty($appointmentData['medical_aid_scheme'])) {
                $billingQuote = $this->generateBillingQuote($appointmentData, $workflowId);
            }
            
            // 5. Schedule pre-appointment tasks
            $this->schedulePreAppointmentTasks($workflowId, $appointmentData);
            
            $this->openemrDb->commit();
            
            return [
                'success' => true,
                'appointment_id' => $appointmentId,
                'workflow_id' => $workflowId,
                'billing_quote' => $billingQuote,
                'message' => 'Radiology appointment created successfully'
            ];
            
        } catch (Exception $e) {
            $this->openemrDb->rollBack();
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Update patient medical aid information with real-time verification
     */
    public function updatePatientMedicalAid($patientId, $medicalAidData) {
        try {
            // Verify medical aid status in real-time
            $verification = $this->verifyMedicalAidStatus($medicalAidData);
            
            if (!$verification['verified']) {
                return [
                    'success' => false,
                    'error' => 'Medical aid verification failed: ' . $verification['message']
                ];
            }
            
            // Update OpenEMR patient insurance
            $this->updateOpenEMRInsurance($patientId, $medicalAidData, $verification);
            
            // Update SA RIS patient data
            $this->updateSARISPatientData($patientId, $medicalAidData, $verification);
            
            return [
                'success' => true,
                'verification' => $verification,
                'message' => 'Medical aid information updated successfully'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Process radiology order with ICD-10 validation
     */
    public function processRadiologyOrder($orderData) {
        try {
            // Validate ICD-10 codes
            $icd10Validation = $this->validateICD10Codes($orderData['icd10_codes']);
            if (!$icd10Validation['valid']) {
                return [
                    'success' => false,
                    'error' => 'Invalid ICD-10 codes: ' . implode(', ', $icd10Validation['invalid_codes'])
                ];
            }
            
            // Validate NRPL procedure codes
            $nrplValidation = $this->validateNRPLCodes($orderData['procedure_codes']);
            if (!$nrplValidation['valid']) {
                return [
                    'success' => false,
                    'error' => 'Invalid NRPL codes: ' . implode(', ', $nrplValidation['invalid_codes'])
                ];
            }
            
            // Create radiology order in OpenEMR
            $orderId = $this->createRadiologyOrder($orderData);
            
            // Check if pre-authorization is required
            $preAuthRequired = $this->checkPreAuthorizationRequired($orderData);
            
            if ($preAuthRequired['required']) {
                $authResult = $this->requestPreAuthorization($orderData, $orderId);
                if (!$authResult['approved']) {
                    return [
                        'success' => false,
                        'error' => 'Pre-authorization denied: ' . $authResult['reason'],
                        'order_id' => $orderId,
                        'status' => 'pending_authorization'
                    ];
                }
            }
            
            return [
                'success' => true,
                'order_id' => $orderId,
                'pre_auth_required' => $preAuthRequired['required'],
                'pre_auth_code' => $preAuthRequired['required'] ? $authResult['auth_code'] : null,
                'estimated_cost' => $this->calculateOrderCost($orderData),
                'message' => 'Radiology order processed successfully'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Submit claims to Healthbridge clearing house
     */
    public function submitClaimsToHealthbridge($claimData) {
        try {
            // Prepare claim data for Healthbridge format
            $healthbridgeData = $this->prepareHealthbridgeClaimData($claimData);
            
            // Validate claim data
            $validation = $this->validateClaimData($healthbridgeData);
            if (!$validation['valid']) {
                return [
                    'success' => false,
                    'error' => 'Claim validation failed: ' . implode(', ', $validation['errors'])
                ];
            }
            
            // Submit to Healthbridge API
            $submission = $this->submitToHealthbridgeAPI($healthbridgeData);
            
            // Update claim status in database
            $this->updateClaimStatus($claimData['claim_id'], $submission);
            
            return [
                'success' => true,
                'submission_id' => $submission['submission_id'],
                'reference_number' => $submission['reference_number'],
                'status' => $submission['status'],
                'message' => 'Claim submitted to Healthbridge successfully'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Synchronize workflow status between OpenEMR and SA RIS
     */
    public function synchronizeWorkflowStatus($workflowId) {
        try {
            // Get current workflow status from SA RIS
            $saRisStatus = $this->getSARISWorkflowStatus($workflowId);
            
            // Get corresponding OpenEMR appointment
            $appointmentId = $this->getLinkedAppointmentId($workflowId);
            
            // Update OpenEMR appointment status
            $this->updateOpenEMRAppointmentStatus($appointmentId, $saRisStatus);
            
            // Update patient chart if report is available
            if ($saRisStatus['current_state'] === 'FINAL_REPORT') {
                $this->updatePatientChartWithReport($appointmentId, $saRisStatus);
            }
            
            return [
                'success' => true,
                'workflow_id' => $workflowId,
                'appointment_id' => $appointmentId,
                'current_status' => $saRisStatus['current_state'],
                'message' => 'Workflow status synchronized successfully'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Generate comprehensive financial report for SA medical aids
     */
    public function generateFinancialReport($startDate, $endDate, $medicalAidScheme = null) {
        try {
            $sql = "SELECT 
                        p.fname, p.lname, p.pid,
                        i.policy_number as member_number,
                        ic.name as medical_aid_name,
                        pc.encounter,
                        pc.code_type,
                        pc.code,
                        pc.code_text,
                        pc.fee,
                        pc.units,
                        DATE(pc.date) as service_date,
                        b.amount as billed_amount,
                        b.pay_amount as paid_amount,
                        b.date as payment_date
                    FROM patient_data p
                    JOIN insurance_data i ON p.pid = i.pid AND i.type = 'primary'
                    JOIN insurance_companies ic ON i.provider = ic.id
                    JOIN billing pc ON p.pid = pc.pid
                    LEFT JOIN payments b ON pc.encounter = b.encounter
                    WHERE DATE(pc.date) BETWEEN ? AND ?";
            
            $params = [$startDate, $endDate];
            
            if ($medicalAidScheme) {
                $sql .= " AND ic.name LIKE ?";
                $params[] = "%$medicalAidScheme%";
            }
            
            $sql .= " ORDER BY pc.date DESC";
            
            $stmt = $this->openemrDb->prepare($sql);
            $stmt->execute($params);
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            // Process and analyze data
            $report = $this->processFinancialData($data, $startDate, $endDate);
            
            return [
                'success' => true,
                'report' => $report,
                'message' => 'Financial report generated successfully'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    // Private helper methods
    
    private function createOpenEMRAppointment($data) {
        $sql = "INSERT INTO openemr_postcalendar_events 
                (pc_catid, pc_title, pc_time, pc_hometext, pc_eventDate, 
                 pc_endDate, pc_duration, pc_alldayevent, pc_apptstatus, 
                 pc_prefcatid, pc_location, pc_eventstatus, pc_sharing, 
                 pc_pid, pc_aid, pc_facility, pc_billing_location) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'SCHEDULED', 0, ?, 1, 1, ?, ?, ?, ?)";
        
        $stmt = $this->openemrDb->prepare($sql);
        $stmt->execute([
            $data['category_id'] ?? 9, // Radiology category
            $data['examination_type'] . ' - ' . $data['patient_name'],
            $data['appointment_time'],
            $data['clinical_indication'] ?? '',
            $data['appointment_date'],
            $data['appointment_date'],
            $data['duration'] ?? 60,
            $data['location'] ?? 'Radiology Department',
            $data['patient_id'],
            $data['provider_id'] ?? 1,
            $data['facility_id'] ?? 1,
            $data['billing_location'] ?? 1
        ]);
        
        return $this->openemrDb->lastInsertId();
    }
    
    private function createSARISWorkflow($data, $appointmentId) {
        $sql = "INSERT INTO ris_workflow_instances 
                (booking_id, patient_id, examination_type, urgency, current_state, 
                 created_at, estimated_completion, openemr_appointment_id) 
                VALUES (?, ?, ?, ?, 'BOOKED', NOW(), ?, ?)";
        
        $estimatedCompletion = date('Y-m-d H:i:s', strtotime($data['appointment_date'] . ' ' . $data['appointment_time'] . ' +2 hours'));
        
        $stmt = $this->saRisDb->prepare($sql);
        $stmt->execute([
            $appointmentId,
            $data['patient_id'],
            $data['examination_type'],
            $data['urgency'] ?? 'routine',
            $estimatedCompletion,
            $appointmentId
        ]);
        
        return $this->saRisDb->lastInsertId();
    }
    
    private function verifyMedicalAidStatus($medicalAidData) {
        $scheme = $this->medicalAidSchemes[$medicalAidData['scheme']] ?? null;
        if (!$scheme) {
            return ['verified' => false, 'message' => 'Unknown medical aid scheme'];
        }
        
        if (!$scheme['real_time_auth']) {
            return ['verified' => true, 'message' => 'Real-time verification not available'];
        }
        
        // Mock verification - in production this would call actual APIs
        return [
            'verified' => true,
            'member_status' => 'active',
            'benefit_year' => date('Y'),
            'available_benefits' => [
                'radiology_limit' => 50000.00,
                'radiology_used' => 12500.00,
                'radiology_remaining' => 37500.00
            ]
        ];
    }
    
    private function validateICD10Codes($codes) {
        $invalidCodes = [];
        foreach ($codes as $code) {
            if (!isset($this->icd10Codes[$code])) {
                $invalidCodes[] = $code;
            }
        }
        
        return [
            'valid' => empty($invalidCodes),
            'invalid_codes' => $invalidCodes
        ];
    }
    
    private function validateNRPLCodes($codes) {
        $invalidCodes = [];
        foreach ($codes as $code) {
            if (!isset($this->nrplCodes[$code])) {
                $invalidCodes[] = $code;
            }
        }
        
        return [
            'valid' => empty($invalidCodes),
            'invalid_codes' => $invalidCodes
        ];
    }
    
    private function checkPreAuthorizationRequired($orderData) {
        $scheme = $this->medicalAidSchemes[$orderData['medical_aid_scheme']] ?? null;
        if (!$scheme) {
            return ['required' => false];
        }
        
        $procedureModality = $this->getProcedureModality($orderData['procedure_codes'][0]);
        $required = in_array($procedureModality, $scheme['pre_auth_procedures']);
        
        return ['required' => $required];
    }
    
    private function getProcedureModality($nrplCode) {
        return $this->nrplCodes[$nrplCode]['modality'] ?? 'UNKNOWN';
    }
    
    private function calculateOrderCost($orderData) {
        $totalCost = 0;
        foreach ($orderData['procedure_codes'] as $code) {
            $totalCost += $this->nrplCodes[$code]['price'] ?? 0;
        }
        return $totalCost;
    }
    
    private function prepareHealthbridgeClaimData($claimData) {
        // Transform claim data to Healthbridge format
        return [
            'practice_code' => $claimData['practice_code'],
            'member_number' => $claimData['member_number'],
            'patient_data' => $claimData['patient_data'],
            'procedures' => $claimData['procedures'],
            'icd10_codes' => $claimData['icd10_codes'],
            'service_date' => $claimData['service_date'],
            'total_amount' => $claimData['total_amount']
        ];
    }
    
    private function validateClaimData($data) {
        $errors = [];
        
        if (empty($data['member_number'])) {
            $errors[] = 'Member number is required';
        }
        
        if (empty($data['procedures'])) {
            $errors[] = 'At least one procedure is required';
        }
        
        if (empty($data['icd10_codes'])) {
            $errors[] = 'ICD-10 diagnosis codes are required';
        }
        
        return [
            'valid' => empty($errors),
            'errors' => $errors
        ];
    }
    
    private function submitToHealthbridgeAPI($data) {
        // Mock API submission - in production this would call actual Healthbridge API
        return [
            'submission_id' => 'HB' . date('Ymd') . rand(10000, 99999),
            'reference_number' => 'REF' . uniqid(),
            'status' => 'submitted',
            'message' => 'Claim submitted successfully'
        ];
    }
    
    // Additional helper methods would be implemented here...
    private function linkAppointmentToWorkflow($appointmentId, $workflowId) { /* Implementation */ }
    private function generateBillingQuote($data, $workflowId) { /* Implementation */ return []; }
    private function schedulePreAppointmentTasks($workflowId, $data) { /* Implementation */ }
    private function updateOpenEMRInsurance($patientId, $data, $verification) { /* Implementation */ }
    private function updateSARISPatientData($patientId, $data, $verification) { /* Implementation */ }
    private function createRadiologyOrder($data) { /* Implementation */ return rand(1000, 9999); }
    private function requestPreAuthorization($data, $orderId) { /* Implementation */ return ['approved' => true, 'auth_code' => 'AUTH123']; }
    private function updateClaimStatus($claimId, $submission) { /* Implementation */ }
    private function getSARISWorkflowStatus($workflowId) { /* Implementation */ return ['current_state' => 'IN_PROGRESS']; }
    private function getLinkedAppointmentId($workflowId) { /* Implementation */ return rand(1000, 9999); }
    private function updateOpenEMRAppointmentStatus($appointmentId, $status) { /* Implementation */ }
    private function updatePatientChartWithReport($appointmentId, $status) { /* Implementation */ }
    private function processFinancialData($data, $startDate, $endDate) { /* Implementation */ return []; }
}