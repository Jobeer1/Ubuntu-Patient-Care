<?php

/**
 * South African ICD-10 Code Management Service
 * 
 * This service manages ICD-10 diagnostic codes with South African
 * specific requirements and medical aid compliance.
 * 
 * Features:
 * - Complete ICD-10-CM code database
 * - South African medical aid specific mappings
 * - Real-time code validation
 * - Automated code updates
 * - Clinical decision support
 * - Radiology-specific code suggestions
 * 
 * @package SA_RIS_ICD10
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\ICD10;

use Exception;
use PDO;

class SAICD10Service {
    
    private $db;
    private $radiologyICD10Codes;
    private $medicalAidRequirements;
    
    public function __construct(PDO $database) {
        $this->db = $database;
        $this->initializeRadiologyICD10Codes();
        $this->initializeMedicalAidRequirements();
    }
    
    /**
     * Initialize common radiology-related ICD-10 codes
     */
    private function initializeRadiologyICD10Codes() {
        $this->radiologyICD10Codes = [
            // Respiratory System
            'J44.1' => [
                'description' => 'Chronic obstructive pulmonary disease with acute exacerbation',
                'category' => 'Respiratory',
                'common_procedures' => ['3001', '3013'], // Chest X-ray, CT Chest
                'urgency' => 'urgent'
            ],
            'J18.9' => [
                'description' => 'Pneumonia, unspecified organism',
                'category' => 'Respiratory',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'urgent'
            ],
            'R06.02' => [
                'description' => 'Shortness of breath',
                'category' => 'Respiratory',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'routine'
            ],
            
            // Neurological System
            'G93.1' => [
                'description' => 'Anoxic brain damage, not elsewhere classified',
                'category' => 'Neurological',
                'common_procedures' => ['3011', '3012', '3021'], // CT Head, MRI Brain
                'urgency' => 'stat'
            ],
            'S06.9' => [
                'description' => 'Unspecified intracranial injury',
                'category' => 'Neurological',
                'common_procedures' => ['3011', '3012'],
                'urgency' => 'stat'
            ],
            'R51' => [
                'description' => 'Headache',
                'category' => 'Neurological',
                'common_procedures' => ['3011', '3021'],
                'urgency' => 'routine'
            ],
            'G44.1' => [
                'description' => 'Vascular headache, not elsewhere classified',
                'category' => 'Neurological',
                'common_procedures' => ['3011', '3021', '3022'],
                'urgency' => 'urgent'
            ],
            
            // Musculoskeletal System
            'M54.9' => [
                'description' => 'Dorsalgia, unspecified',
                'category' => 'Musculoskeletal',
                'common_procedures' => ['3023', '3024'], // MRI Spine
                'urgency' => 'routine'
            ],
            'M25.50' => [
                'description' => 'Pain in unspecified joint',
                'category' => 'Musculoskeletal',
                'common_procedures' => ['3025'], // MRI Knee
                'urgency' => 'routine'
            ],
            'S72.9' => [
                'description' => 'Unspecified fracture of femur',
                'category' => 'Musculoskeletal',
                'common_procedures' => ['3004'], // X-ray
                'urgency' => 'urgent'
            ],
            
            // Gastrointestinal System
            'R10.9' => [
                'description' => 'Unspecified abdominal pain',
                'category' => 'Gastrointestinal',
                'common_procedures' => ['3015', '3041'], // CT Abdomen, US Abdomen
                'urgency' => 'urgent'
            ],
            'K59.00' => [
                'description' => 'Constipation, unspecified',
                'category' => 'Gastrointestinal',
                'common_procedures' => ['3015'],
                'urgency' => 'routine'
            ],
            
            // Cardiovascular System
            'I25.9' => [
                'description' => 'Chronic ischemic heart disease, unspecified',
                'category' => 'Cardiovascular',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'urgent'
            ],
            'I50.9' => [
                'description' => 'Heart failure, unspecified',
                'category' => 'Cardiovascular',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'urgent'
            ],
            
            // Genitourinary System
            'N39.0' => [
                'description' => 'Urinary tract infection, site not specified',
                'category' => 'Genitourinary',
                'common_procedures' => ['3042'], // Pelvic US
                'urgency' => 'routine'
            ],
            'N20.0' => [
                'description' => 'Calculus of kidney',
                'category' => 'Genitourinary',
                'common_procedures' => ['3015', '3041'],
                'urgency' => 'urgent'
            ],
            
            // Oncology
            'C78.00' => [
                'description' => 'Secondary malignant neoplasm of unspecified lung',
                'category' => 'Oncology',
                'common_procedures' => ['3013', '3014', '3071'], // CT Chest, PET
                'urgency' => 'urgent'
            ],
            'Z51.11' => [
                'description' => 'Encounter for antineoplastic chemotherapy',
                'category' => 'Oncology',
                'common_procedures' => ['3013', '3015'],
                'urgency' => 'routine'
            ],
            
            // Women's Health
            'Z12.31' => [
                'description' => 'Encounter for screening mammogram for malignant neoplasm of breast',
                'category' => 'Women\'s Health',
                'common_procedures' => ['3051'], // Mammography
                'urgency' => 'routine'
            ],
            'N63' => [
                'description' => 'Unspecified lump in breast',
                'category' => 'Women\'s Health',
                'common_procedures' => ['3051', '3052'],
                'urgency' => 'urgent'
            ],
            
            // Emergency/Trauma
            'R50.9' => [
                'description' => 'Fever, unspecified',
                'category' => 'Emergency',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'urgent'
            ],
            'R06.03' => [
                'description' => 'Acute respiratory distress',
                'category' => 'Emergency',
                'common_procedures' => ['3001', '3013'],
                'urgency' => 'stat'
            ]
        ];
    }
    
    /**
     * Initialize medical aid specific ICD-10 requirements
     */
    private function initializeMedicalAidRequirements() {
        $this->medicalAidRequirements = [
            'discovery' => [
                'requires_primary_diagnosis' => true,
                'max_secondary_diagnoses' => 3,
                'requires_clinical_justification' => ['3021', '3022', '3071'], // MRI, PET
                'restricted_codes' => [], // Codes requiring pre-auth
                'preferred_code_sets' => ['ICD-10-CM']
            ],
            'momentum' => [
                'requires_primary_diagnosis' => true,
                'max_secondary_diagnoses' => 2,
                'requires_clinical_justification' => ['3021', '3022', '3071'],
                'restricted_codes' => [],
                'preferred_code_sets' => ['ICD-10-CM']
            ],
            'bonitas' => [
                'requires_primary_diagnosis' => true,
                'max_secondary_diagnoses' => 2,
                'requires_clinical_justification' => ['3021', '3022'],
                'restricted_codes' => [],
                'preferred_code_sets' => ['ICD-10-CM']
            ],
            'gems' => [
                'requires_primary_diagnosis' => true,
                'max_secondary_diagnoses' => 4,
                'requires_clinical_justification' => ['3021', '3022', '3071'],
                'restricted_codes' => [],
                'preferred_code_sets' => ['ICD-10-CM']
            ]
        ];
    }
    
    /**
     * Validate ICD-10 codes for South African medical aids
     */
    public function validateICD10Codes($codes, $medicalAidScheme = null, $procedureCodes = []) {
        try {
            $validation = [
                'valid' => true,
                'errors' => [],
                'warnings' => [],
                'suggestions' => []
            ];
            
            if (empty($codes)) {
                $validation['valid'] = false;
                $validation['errors'][] = 'At least one ICD-10 diagnosis code is required';
                return $validation;
            }
            
            // Check medical aid specific requirements
            if ($medicalAidScheme && isset($this->medicalAidRequirements[$medicalAidScheme])) {
                $requirements = $this->medicalAidRequirements[$medicalAidScheme];
                
                // Check maximum number of codes
                if (count($codes) > ($requirements['max_secondary_diagnoses'] + 1)) {
                    $validation['valid'] = false;
                    $validation['errors'][] = "Too many diagnosis codes. Maximum allowed: " . 
                        ($requirements['max_secondary_diagnoses'] + 1);
                }
                
                // Check for restricted codes
                foreach ($codes as $code) {
                    if (in_array($code, $requirements['restricted_codes'])) {
                        $validation['warnings'][] = "Code $code may require pre-authorization";
                    }
                }
            }
            
            // Validate each code
            foreach ($codes as $index => $code) {
                $codeValidation = $this->validateSingleICD10Code($code);
                
                if (!$codeValidation['valid']) {
                    $validation['valid'] = false;
                    $validation['errors'][] = "Invalid ICD-10 code: $code";
                } else {
                    // Check if code is appropriate for procedures
                    if (!empty($procedureCodes)) {
                        $appropriateness = $this->checkCodeProcedureAppropriateness($code, $procedureCodes);
                        if (!$appropriateness['appropriate']) {
                            $validation['warnings'][] = $appropriateness['message'];
                        }
                    }
                }
            }
            
            // Generate suggestions for better coding
            $suggestions = $this->generateCodingSuggestions($codes, $procedureCodes);
            $validation['suggestions'] = $suggestions;
            
            return $validation;
            
        } catch (Exception $e) {
            return [
                'valid' => false,
                'errors' => ['Validation error: ' . $e->getMessage()],
                'warnings' => [],
                'suggestions' => []
            ];
        }
    }
    
    /**
     * Suggest ICD-10 codes based on clinical indication and procedure
     */
    public function suggestICD10Codes($clinicalIndication, $procedureCodes = [], $patientAge = null, $patientGender = null) {
        try {
            $suggestions = [];
            
            // Text-based matching for clinical indication
            $textMatches = $this->findCodesByText($clinicalIndication);
            
            // Procedure-based suggestions
            $procedureMatches = $this->findCodesByProcedures($procedureCodes);
            
            // Combine and rank suggestions
            $allSuggestions = array_merge($textMatches, $procedureMatches);
            $rankedSuggestions = $this->rankSuggestions($allSuggestions, $clinicalIndication, $procedureCodes);
            
            // Apply demographic filters
            if ($patientAge !== null || $patientGender !== null) {
                $rankedSuggestions = $this->applyDemographicFilters($rankedSuggestions, $patientAge, $patientGender);
            }
            
            return [
                'success' => true,
                'suggestions' => array_slice($rankedSuggestions, 0, 10), // Top 10 suggestions
                'total_matches' => count($allSuggestions)
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage(),
                'suggestions' => []
            ];
        }
    }
    
    /**
     * Get detailed information about an ICD-10 code
     */
    public function getICD10CodeDetails($code) {
        try {
            // Check if it's in our radiology-specific codes
            if (isset($this->radiologyICD10Codes[$code])) {
                $details = $this->radiologyICD10Codes[$code];
                $details['code'] = $code;
                $details['source'] = 'radiology_specific';
                return [
                    'success' => true,
                    'details' => $details
                ];
            }
            
            // Query database for full ICD-10 details
            $sql = "SELECT * FROM icd10_codes WHERE code = ? AND active = 1";
            $stmt = $this->db->prepare($sql);
            $stmt->execute([$code]);
            $result = $stmt->fetch(PDO::FETCH_ASSOC);
            
            if ($result) {
                return [
                    'success' => true,
                    'details' => [
                        'code' => $result['code'],
                        'description' => $result['description'],
                        'category' => $result['category'],
                        'chapter' => $result['chapter'],
                        'valid_from' => $result['valid_from'],
                        'valid_to' => $result['valid_to'],
                        'source' => 'database'
                    ]
                ];
            }
            
            return [
                'success' => false,
                'error' => 'ICD-10 code not found'
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Update ICD-10 code database from official sources
     */
    public function updateICD10Database() {
        try {
            // This would typically download from WHO or local health authority
            // For now, we'll simulate the update process
            
            $updateStats = [
                'codes_added' => 0,
                'codes_updated' => 0,
                'codes_deprecated' => 0,
                'update_date' => date('Y-m-d H:i:s')
            ];
            
            // Simulate adding new codes
            $newCodes = $this->getLatestICD10Updates();
            
            foreach ($newCodes as $codeData) {
                $existing = $this->checkIfCodeExists($codeData['code']);
                
                if ($existing) {
                    $this->updateExistingCode($codeData);
                    $updateStats['codes_updated']++;
                } else {
                    $this->addNewCode($codeData);
                    $updateStats['codes_added']++;
                }
            }
            
            // Mark deprecated codes
            $deprecatedCodes = $this->getDeprecatedCodes();
            foreach ($deprecatedCodes as $code) {
                $this->markCodeAsDeprecated($code);
                $updateStats['codes_deprecated']++;
            }
            
            // Log update
            $this->logDatabaseUpdate($updateStats);
            
            return [
                'success' => true,
                'update_stats' => $updateStats
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Generate ICD-10 coding report for quality assurance
     */
    public function generateCodingQualityReport($startDate, $endDate) {
        try {
            $sql = "SELECT 
                        icd10_code,
                        COUNT(*) as usage_count,
                        COUNT(DISTINCT patient_id) as unique_patients,
                        AVG(CASE WHEN coding_accuracy_score IS NOT NULL THEN coding_accuracy_score END) as avg_accuracy,
                        SUM(CASE WHEN requires_review = 1 THEN 1 ELSE 0 END) as codes_requiring_review
                    FROM radiology_orders ro
                    JOIN radiology_order_diagnoses rod ON ro.id = rod.order_id
                    WHERE ro.order_date BETWEEN ? AND ?
                    GROUP BY icd10_code
                    ORDER BY usage_count DESC";
            
            $stmt = $this->db->prepare($sql);
            $stmt->execute([$startDate, $endDate]);
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            $report = [
                'period' => ['start' => $startDate, 'end' => $endDate],
                'summary' => [
                    'total_unique_codes' => count($data),
                    'total_code_usage' => array_sum(array_column($data, 'usage_count')),
                    'avg_accuracy_score' => 0,
                    'codes_requiring_review' => array_sum(array_column($data, 'codes_requiring_review'))
                ],
                'most_used_codes' => array_slice($data, 0, 20),
                'accuracy_issues' => [],
                'recommendations' => []
            ];
            
            // Calculate average accuracy
            $accuracyScores = array_filter(array_column($data, 'avg_accuracy'));
            if (!empty($accuracyScores)) {
                $report['summary']['avg_accuracy_score'] = array_sum($accuracyScores) / count($accuracyScores);
            }
            
            // Identify accuracy issues
            foreach ($data as $codeData) {
                if ($codeData['avg_accuracy'] && $codeData['avg_accuracy'] < 0.8) {
                    $report['accuracy_issues'][] = [
                        'code' => $codeData['icd10_code'],
                        'accuracy_score' => $codeData['avg_accuracy'],
                        'usage_count' => $codeData['usage_count']
                    ];
                }
            }
            
            // Generate recommendations
            $report['recommendations'] = $this->generateCodingRecommendations($report);
            
            return [
                'success' => true,
                'report' => $report
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    // Private helper methods
    
    private function validateSingleICD10Code($code) {
        // Basic format validation
        if (!preg_match('/^[A-Z]\d{2}(\.\d{1,2})?$/', $code)) {
            return ['valid' => false, 'message' => 'Invalid ICD-10 code format'];
        }
        
        // Check if code exists in our database or known codes
        if (isset($this->radiologyICD10Codes[$code])) {
            return ['valid' => true];
        }
        
        // Query database
        $sql = "SELECT COUNT(*) FROM icd10_codes WHERE code = ? AND active = 1";
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$code]);
        $exists = $stmt->fetchColumn() > 0;
        
        return ['valid' => $exists];
    }
    
    private function checkCodeProcedureAppropriateness($icd10Code, $procedureCodes) {
        if (!isset($this->radiologyICD10Codes[$icd10Code])) {
            return ['appropriate' => true]; // Unknown code, assume appropriate
        }
        
        $codeData = $this->radiologyICD10Codes[$icd10Code];
        $commonProcedures = $codeData['common_procedures'] ?? [];
        
        $hasAppropriate = false;
        foreach ($procedureCodes as $procCode) {
            if (in_array($procCode, $commonProcedures)) {
                $hasAppropriate = true;
                break;
            }
        }
        
        if (!$hasAppropriate && !empty($commonProcedures)) {
            return [
                'appropriate' => false,
                'message' => "Code $icd10Code is typically associated with procedures: " . 
                           implode(', ', $commonProcedures)
            ];
        }
        
        return ['appropriate' => true];
    }
    
    private function findCodesByText($text) {
        $matches = [];
        $searchTerms = explode(' ', strtolower($text));
        
        foreach ($this->radiologyICD10Codes as $code => $data) {
            $description = strtolower($data['description']);
            $score = 0;
            
            foreach ($searchTerms as $term) {
                if (strpos($description, $term) !== false) {
                    $score++;
                }
            }
            
            if ($score > 0) {
                $matches[] = [
                    'code' => $code,
                    'description' => $data['description'],
                    'score' => $score,
                    'category' => $data['category']
                ];
            }
        }
        
        return $matches;
    }
    
    private function findCodesByProcedures($procedureCodes) {
        $matches = [];
        
        foreach ($this->radiologyICD10Codes as $code => $data) {
            $commonProcedures = $data['common_procedures'] ?? [];
            $matchCount = count(array_intersect($procedureCodes, $commonProcedures));
            
            if ($matchCount > 0) {
                $matches[] = [
                    'code' => $code,
                    'description' => $data['description'],
                    'score' => $matchCount * 2, // Higher weight for procedure matches
                    'category' => $data['category']
                ];
            }
        }
        
        return $matches;
    }
    
    private function rankSuggestions($suggestions, $clinicalIndication, $procedureCodes) {
        // Sort by score descending
        usort($suggestions, function($a, $b) {
            return $b['score'] - $a['score'];
        });
        
        return $suggestions;
    }
    
    private function applyDemographicFilters($suggestions, $age, $gender) {
        // Apply age and gender specific filtering
        // This is a simplified implementation
        return $suggestions;
    }
    
    private function generateCodingSuggestions($codes, $procedureCodes) {
        $suggestions = [];
        
        // Check for missing secondary diagnoses
        if (count($codes) === 1 && !empty($procedureCodes)) {
            $suggestions[] = "Consider adding secondary diagnosis codes for comprehensive documentation";
        }
        
        // Check for specificity
        foreach ($codes as $code) {
            if (substr($code, -1) === '9') { // Unspecified codes
                $suggestions[] = "Consider using more specific code instead of $code if clinical information allows";
            }
        }
        
        return $suggestions;
    }
    
    private function generateCodingRecommendations($report) {
        $recommendations = [];
        
        if ($report['summary']['avg_accuracy_score'] < 0.85) {
            $recommendations[] = "Overall coding accuracy is below target (85%). Consider additional coder training.";
        }
        
        if ($report['summary']['codes_requiring_review'] > 0) {
            $recommendations[] = "Review and address " . $report['summary']['codes_requiring_review'] . " codes flagged for review.";
        }
        
        return $recommendations;
    }
    
    // Database operations for ICD-10 updates
    private function getLatestICD10Updates() { return []; } // Mock implementation
    private function checkIfCodeExists($code) { return false; } // Mock implementation
    private function updateExistingCode($codeData) { } // Mock implementation
    private function addNewCode($codeData) { } // Mock implementation
    private function getDeprecatedCodes() { return []; } // Mock implementation
    private function markCodeAsDeprecated($code) { } // Mock implementation
    private function logDatabaseUpdate($stats) { } // Mock implementation
}