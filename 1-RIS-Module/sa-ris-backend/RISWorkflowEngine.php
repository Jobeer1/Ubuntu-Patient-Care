<?php

/**
 * South African RIS - Advanced Workflow Engine
 * 
 * Handles complete radiology workflow from booking to reporting
 * Optimized for SA medical practices with DICOM integration
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\Workflow;

use SA_RIS\DICOM\OrthancConnector;
use SA_RIS\Billing\SABillingEngine;
use SA_RIS\Notifications\NotificationService;
use Exception;
use PDO;

class RISWorkflowEngine {
    
    private $db;
    private $orthancConnector;
    private $billingEngine;
    private $notificationService;
    private $workflowStates;
    
    public function __construct(PDO $database) {
        $this->db = $database;
        $this->orthancConnector = new OrthancConnector();
        $this->billingEngine = new SABillingEngine($database);
        $this->notificationService = new NotificationService();
        $this->initializeWorkflowStates();
    }
    
    private function initializeWorkflowStates() {
        $this->workflowStates = [
            'BOOKED' => [
                'name' => 'Appointment Booked',
                'next_states' => ['REGISTERED', 'CANCELLED'],
                'notifications' => ['patient_sms', 'reminder_24h'],
                'required_actions' => ['verify_insurance', 'prepare_contrast']
            ],
            'REGISTERED' => [
                'name' => 'Patient Registered',
                'next_states' => ['IN_PROGRESS', 'NO_SHOW'],
                'notifications' => ['technologist_alert'],
                'required_actions' => ['patient_prep', 'equipment_check']
            ],
            'IN_PROGRESS' => [
                'name' => 'Examination In Progress',
                'next_states' => ['COMPLETED', 'CANCELLED'],
                'notifications' => ['referring_doctor_progress'],
                'required_actions' => ['image_acquisition', 'quality_check']
            ],
            'COMPLETED' => [
                'name' => 'Images Acquired',
                'next_states' => ['PRELIMINARY_READ', 'RADIOLOGIST_ASSIGNED'],
                'notifications' => ['radiologist_alert', 'images_available'],
                'required_actions' => ['send_to_pacs', 'assign_radiologist']
            ],
            'PRELIMINARY_READ' => [
                'name' => 'Preliminary Reading',
                'next_states' => ['FINAL_REPORT', 'ADDITIONAL_VIEWS'],
                'notifications' => ['critical_findings_alert'],
                'required_actions' => ['preliminary_report', 'critical_value_check']
            ],
            'FINAL_REPORT' => [
                'name' => 'Final Report Available',
                'next_states' => ['DELIVERED', 'AMENDED'],
                'notifications' => ['referring_doctor_report', 'patient_results'],
                'required_actions' => ['report_delivery', 'billing_submission']
            ],
            'DELIVERED' => [
                'name' => 'Report Delivered',
                'next_states' => ['ARCHIVED', 'FOLLOW_UP'],
                'notifications' => ['delivery_confirmation'],
                'required_actions' => ['payment_tracking', 'archive_images']
            ]
        ];
    }
    
    /**
     * Process new radiology booking through the workflow
     */
    public function processNewBooking($bookingData) {
        try {
            // Create workflow instance
            $workflowId = $this->createWorkflowInstance($bookingData);
            
            // Initialize at BOOKED state
            $this->updateWorkflowState($workflowId, 'BOOKED');
            
            // Perform automatic actions
            $this->executeAutomaticActions($workflowId, 'BOOKED', $bookingData);
            
            // Schedule notifications
            $this->scheduleNotifications($workflowId, 'BOOKED', $bookingData);
            
            // Generate billing quote
            $billingQuote = $this->generateInitialBillingQuote($bookingData);
            
            return [
                'success' => true,
                'workflow_id' => $workflowId,
                'current_state' => 'BOOKED',
                'billing_quote' => $billingQuote,
                'next_actions' => $this->getNextActions($workflowId)
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Advance workflow to next state
     */
    public function advanceWorkflow($workflowId, $targetState, $actionData = []) {
        try {
            $currentWorkflow = $this->getWorkflowInstance($workflowId);
            $currentState = $currentWorkflow['current_state'];
            
            // Validate state transition
            if (!$this->isValidTransition($currentState, $targetState)) {
                throw new Exception("Invalid state transition from $currentState to $targetState");
            }
            
            // Execute pre-transition actions
            $this->executePreTransitionActions($workflowId, $currentState, $targetState, $actionData);
            
            // Update state
            $this->updateWorkflowState($workflowId, $targetState);
            
            // Execute post-transition actions
            $this->executePostTransitionActions($workflowId, $targetState, $actionData);
            
            // Schedule notifications
            $this->scheduleNotifications($workflowId, $targetState, $currentWorkflow);
            
            return [
                'success' => true,
                'workflow_id' => $workflowId,
                'previous_state' => $currentState,
                'current_state' => $targetState,
                'next_actions' => $this->getNextActions($workflowId)
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Handle DICOM image reception and processing
     */
    public function processDICOMImages($workflowId, $studyInstanceUID) {
        try {
            // Retrieve study from Orthanc
            $study = $this->orthancConnector->getStudy($studyInstanceUID);
            if (!$study) {
                throw new Exception("Study not found in PACS: $studyInstanceUID");
            }
            
            // Validate patient matching
            $workflow = $this->getWorkflowInstance($workflowId);
            $patientMatched = $this->validatePatientMatch($workflow, $study);
            
            if (!$patientMatched) {
                $this->createMismatchAlert($workflowId, $study);
                return ['success' => false, 'error' => 'Patient mismatch detected'];
            }
            
            // Process images
            $imageProcessing = $this->processImages($workflowId, $study);
            
            // Auto-advance workflow if images are complete
            if ($imageProcessing['complete']) {
                $this->advanceWorkflow($workflowId, 'COMPLETED', [
                    'study_uid' => $studyInstanceUID,
                    'image_count' => $imageProcessing['image_count'],
                    'series_count' => $imageProcessing['series_count']
                ]);
            }
            
            return [
                'success' => true,
                'study_processed' => true,
                'images_processed' => $imageProcessing['image_count'],
                'workflow_advanced' => $imageProcessing['complete']
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * AI-powered automatic report generation
     */
    public function generateAIReport($workflowId, $studyInstanceUID) {
        try {
            $workflow = $this->getWorkflowInstance($workflowId);
            $study = $this->orthancConnector->getStudy($studyInstanceUID);
            
            // Get AI analysis based on examination type
            $aiAnalysis = $this->performAIAnalysis($workflow['examination_type'], $study);
            
            // Generate structured report
            $report = $this->generateStructuredReport($workflow, $aiAnalysis);
            
            // Save preliminary report
            $reportId = $this->savePreliminaryReport($workflowId, $report);
            
            // Check for critical findings
            if ($aiAnalysis['critical_findings']) {
                $this->handleCriticalFindings($workflowId, $aiAnalysis['critical_findings']);
            }
            
            // Advance to preliminary read state
            $this->advanceWorkflow($workflowId, 'PRELIMINARY_READ', [
                'report_id' => $reportId,
                'ai_confidence' => $aiAnalysis['confidence'],
                'critical_findings' => $aiAnalysis['critical_findings']
            ]);
            
            return [
                'success' => true,
                'report_id' => $reportId,
                'ai_confidence' => $aiAnalysis['confidence'],
                'critical_findings' => $aiAnalysis['critical_findings'],
                'requires_radiologist_review' => $aiAnalysis['confidence'] < 0.9
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Smart radiologist assignment based on subspecialty and workload
     */
    public function assignRadiologist($workflowId) {
        try {
            $workflow = $this->getWorkflowInstance($workflowId);
            
            // Get available radiologists with relevant subspecialty
            $availableRadiologists = $this->getAvailableRadiologists($workflow['examination_type']);
            
            // Apply intelligent assignment algorithm
            $assignedRadiologist = $this->intelligentRadiologistAssignment($availableRadiologists, $workflow);
            
            // Update workflow
            $this->updateWorkflowRadiologist($workflowId, $assignedRadiologist['id']);
            
            // Notify radiologist
            $this->notificationService->notifyRadiologist($assignedRadiologist, $workflow);
            
            return [
                'success' => true,
                'radiologist_assigned' => $assignedRadiologist,
                'estimated_report_time' => $assignedRadiologist['estimated_completion']
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Generate comprehensive workflow analytics
     */
    public function generateWorkflowAnalytics($startDate, $endDate) {
        $sql = "SELECT 
                    w.current_state,
                    w.examination_type,
                    w.urgency,
                    COUNT(*) as count,
                    AVG(TIMESTAMPDIFF(MINUTE, w.created_at, w.completed_at)) as avg_duration_minutes,
                    AVG(w.patient_satisfaction_score) as avg_satisfaction
                FROM ris_workflow_instances w
                WHERE w.created_at BETWEEN ? AND ?
                GROUP BY w.current_state, w.examination_type, w.urgency
                ORDER BY w.current_state, count DESC";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$startDate, $endDate]);
        $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        $analytics = [
            'period' => ['start' => $startDate, 'end' => $endDate],
            'workflow_performance' => [],
            'bottlenecks' => [],
            'efficiency_metrics' => [],
            'recommendations' => []
        ];
        
        foreach ($data as $row) {
            $analytics['workflow_performance'][] = $row;
            
            // Identify bottlenecks (states with long duration)
            if ($row['avg_duration_minutes'] > 120) { // More than 2 hours
                $analytics['bottlenecks'][] = [
                    'state' => $row['current_state'],
                    'examination_type' => $row['examination_type'],
                    'avg_duration' => $row['avg_duration_minutes'],
                    'cases' => $row['count']
                ];
            }
        }
        
        // Calculate efficiency metrics
        $analytics['efficiency_metrics'] = $this->calculateEfficiencyMetrics($data);
        
        // Generate recommendations
        $analytics['recommendations'] = $this->generateWorkflowRecommendations($analytics);
        
        return $analytics;
    }
    
    /**
     * Real-time dashboard data for radiology department
     */
    public function getDashboardData() {
        $dashboard = [
            'current_status' => $this->getCurrentWorkflowStatus(),
            'urgent_cases' => $this->getUrgentCases(),
            'critical_findings' => $this->getCriticalFindingsCases(),
            'pending_reports' => $this->getPendingReports(),
            'radiologist_workload' => $this->getRadiologistWorkload(),
            'equipment_status' => $this->getEquipmentStatus(),
            'performance_metrics' => $this->getTodayPerformanceMetrics()
        ];
        
        return $dashboard;
    }
    
    private function createWorkflowInstance($bookingData) {
        $sql = "INSERT INTO ris_workflow_instances 
                (booking_id, patient_id, examination_type, urgency, current_state, 
                 created_at, estimated_completion) 
                VALUES (?, ?, ?, ?, 'BOOKED', NOW(), ?)";
        
        $estimatedCompletion = $this->calculateEstimatedCompletion($bookingData);
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $bookingData['booking_id'],
            $bookingData['patient_id'],
            $bookingData['examination_type'],
            $bookingData['urgency'],
            $estimatedCompletion
        ]);
        
        return $this->db->lastInsertId();
    }
    
    private function updateWorkflowState($workflowId, $newState) {
        $sql = "UPDATE ris_workflow_instances 
                SET current_state = ?, last_updated = NOW() 
                WHERE id = ?";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$newState, $workflowId]);
        
        // Log state change
        $this->logStateChange($workflowId, $newState);
    }
    
    private function isValidTransition($currentState, $targetState) {
        $validStates = $this->workflowStates[$currentState]['next_states'] ?? [];
        return in_array($targetState, $validStates);
    }
    
    private function executeAutomaticActions($workflowId, $state, $data) {
        $actions = $this->workflowStates[$state]['required_actions'] ?? [];
        
        foreach ($actions as $action) {
            switch ($action) {
                case 'verify_insurance':
                    $this->verifyInsuranceAutomatically($workflowId, $data);
                    break;
                case 'prepare_contrast':
                    $this->scheduleContrastPreparation($workflowId, $data);
                    break;
                case 'send_to_pacs':
                    $this->sendImagesToPACS($workflowId, $data);
                    break;
                case 'assign_radiologist':
                    $this->assignRadiologist($workflowId);
                    break;
            }
        }
    }
    
    private function performAIAnalysis($examinationType, $study) {
        // Mock AI analysis - in production this would integrate with actual AI models
        $confidence = 0.85 + (rand(0, 15) / 100); // 85-100% confidence
        
        $findings = [
            'CT' => [
                'No acute intracranial abnormality detected',
                'Normal brain parenchyma',
                'No evidence of hemorrhage or mass effect'
            ],
            'MRI' => [
                'Normal signal characteristics',
                'No pathological enhancement',
                'Unremarkable findings'
            ],
            'XRAY' => [
                'Normal cardiopulmonary silhouette',
                'No acute osseous abnormality',
                'Clear lung fields'
            ]
        ][$examinationType] ?? ['Normal examination'];
        
        $criticalFindings = rand(1, 100) <= 5; // 5% chance of critical findings
        
        return [
            'confidence' => $confidence,
            'findings' => $findings,
            'critical_findings' => $criticalFindings,
            'ai_model_version' => '2024.1',
            'processing_time' => rand(30, 120) // seconds
        ];
    }
    
    private function generateStructuredReport($workflow, $aiAnalysis) {
        return [
            'patient_id' => $workflow['patient_id'],
            'examination_type' => $workflow['examination_type'],
            'clinical_indication' => $workflow['clinical_history'],
            'technique' => $this->getStandardTechnique($workflow['examination_type']),
            'findings' => implode('. ', $aiAnalysis['findings']),
            'impression' => $this->generateImpression($aiAnalysis['findings']),
            'recommendations' => $this->generateRecommendations($workflow, $aiAnalysis),
            'ai_assisted' => true,
            'confidence_score' => $aiAnalysis['confidence'],
            'generated_at' => date('Y-m-d H:i:s')
        ];
    }
    
    private function calculateEstimatedCompletion($bookingData) {
        $baseDuration = [
            'xray' => 30,      // 30 minutes
            'ct' => 45,        // 45 minutes
            'mri' => 90,       // 90 minutes
            'ultrasound' => 30,
            'mammography' => 45
        ][$bookingData['examination_type']] ?? 60;
        
        // Add urgency factor
        if ($bookingData['urgency'] === 'stat') {
            $baseDuration = $baseDuration * 0.5; // STAT cases processed faster
        } elseif ($bookingData['urgency'] === 'urgent') {
            $baseDuration = $baseDuration * 0.75;
        }
        
        return date('Y-m-d H:i:s', strtotime("+{$baseDuration} minutes"));
    }
    
    // Additional helper methods would be implemented here...
    private function getWorkflowInstance($workflowId) { /* Implementation */ return []; }
    private function scheduleNotifications($workflowId, $state, $data) { /* Implementation */ }
    private function getNextActions($workflowId) { /* Implementation */ return []; }
    private function executePreTransitionActions($workflowId, $currentState, $targetState, $actionData) { /* Implementation */ }
    private function executePostTransitionActions($workflowId, $targetState, $actionData) { /* Implementation */ }
    private function validatePatientMatch($workflow, $study) { /* Implementation */ return true; }
    private function processImages($workflowId, $study) { /* Implementation */ return ['complete' => true, 'image_count' => 100, 'series_count' => 5]; }
    private function savePreliminaryReport($workflowId, $report) { /* Implementation */ return rand(1000, 9999); }
    private function handleCriticalFindings($workflowId, $findings) { /* Implementation */ }
    private function getAvailableRadiologists($examinationType) { /* Implementation */ return []; }
    private function intelligentRadiologistAssignment($radiologists, $workflow) { /* Implementation */ return ['id' => 1, 'name' => 'Dr. Smith', 'estimated_completion' => date('Y-m-d H:i:s', strtotime('+2 hours'))]; }
    private function updateWorkflowRadiologist($workflowId, $radiologistId) { /* Implementation */ }
    private function getCurrentWorkflowStatus() { /* Implementation */ return []; }
    private function getUrgentCases() { /* Implementation */ return []; }
    private function getCriticalFindingsCases() { /* Implementation */ return []; }
    private function getPendingReports() { /* Implementation */ return []; }
    private function getRadiologistWorkload() { /* Implementation */ return []; }
    private function getEquipmentStatus() { /* Implementation */ return []; }
    private function getTodayPerformanceMetrics() { /* Implementation */ return []; }
    private function calculateEfficiencyMetrics($data) { /* Implementation */ return []; }
    private function generateWorkflowRecommendations($analytics) { /* Implementation */ return []; }
    private function logStateChange($workflowId, $newState) { /* Implementation */ }
    private function verifyInsuranceAutomatically($workflowId, $data) { /* Implementation */ }
    private function scheduleContrastPreparation($workflowId, $data) { /* Implementation */ }
    private function sendImagesToPACS($workflowId, $data) { /* Implementation */ }
    private function createMismatchAlert($workflowId, $study) { /* Implementation */ }
    private function getStandardTechnique($examinationType) { /* Implementation */ return 'Standard technique'; }
    private function generateImpression($findings) { /* Implementation */ return 'Normal study'; }
    private function generateRecommendations($workflow, $aiAnalysis) { /* Implementation */ return 'No follow-up required'; }
    private function generateInitialBillingQuote($bookingData) { /* Implementation */ return []; }
}
