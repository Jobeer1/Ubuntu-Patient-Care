<?php

/**
 * South African RIS - Advanced Billing Engine
 * 
 * This module handles all SA-specific medical billing requirements including:
 * - Medical aid scheme integration
 * - ICD-10 and CPT code management
 * - NRPL billing codes
 * - Real-time authorization verification
 * - Automated claim submission
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\Billing;

use Exception;
use PDO;

class SABillingEngine {
    
    private $db;
    private $medicalAidSchemes;
    private $nrplCodes;
    
    public function __construct(PDO $database) {
        $this->db = $database;
        $this->initializeMedicalAidSchemes();
        $this->loadNRPLCodes();
    }
    
    /**
     * Initialize South African Medical Aid Schemes with their specific billing requirements
     */
    private function initializeMedicalAidSchemes() {
        $this->medicalAidSchemes = [
            'discovery' => [
                'name' => 'Discovery Health Medical Scheme',
                'scheme_code' => 'DHMS',
                'billing_format' => 'XML',
                'api_endpoint' => 'https://api.discovery.co.za/claims',
                'authorization_required' => true,
                'real_time_verification' => true,
                'supported_procedures' => ['diagnostic_imaging', 'interventional', 'emergency'],
                'tariff_structure' => 'NRPL_2024',
                'claim_submission_method' => 'electronic',
                'pre_auth_codes' => [
                    'CT' => ['3011', '3012', '3013'],
                    'MRI' => ['3021', '3022', '3023'],
                    'PET' => ['3031', '3032'],
                    'NUCLEAR' => ['3041', '3042']
                ]
            ],
            'momentum' => [
                'name' => 'Momentum Health',
                'scheme_code' => 'MOM',
                'billing_format' => 'EDI',
                'api_endpoint' => 'https://gateway.momentum.co.za/claims',
                'authorization_required' => true,
                'real_time_verification' => true,
                'supported_procedures' => ['diagnostic_imaging', 'interventional'],
                'tariff_structure' => 'NRPL_2024',
                'claim_submission_method' => 'electronic'
            ],
            'bonitas' => [
                'name' => 'Bonitas Medical Fund',
                'scheme_code' => 'BON',
                'billing_format' => 'XML',
                'api_endpoint' => 'https://claims.bonitas.co.za/submit',
                'authorization_required' => false,
                'real_time_verification' => true,
                'supported_procedures' => ['diagnostic_imaging'],
                'tariff_structure' => 'NRPL_2024',
                'claim_submission_method' => 'electronic'
            ],
            'gems' => [
                'name' => 'Government Employees Medical Scheme',
                'scheme_code' => 'GEMS',
                'billing_format' => 'PDF',
                'api_endpoint' => 'https://gems.gov.za/claims',
                'authorization_required' => true,
                'real_time_verification' => false,
                'supported_procedures' => ['diagnostic_imaging', 'emergency'],
                'tariff_structure' => 'GEMS_TARIFF',
                'claim_submission_method' => 'manual'
            ]
        ];
    }
    
    /**
     * Load NRPL (National Reference Price List) codes for 2024
     */
    private function loadNRPLCodes() {
        $this->nrplCodes = [
            // CT Scan Codes
            'CT_HEAD_PLAIN' => ['code' => '3011', 'description' => 'CT Head without contrast', 'price' => 1850.00],
            'CT_HEAD_CONTRAST' => ['code' => '3012', 'description' => 'CT Head with contrast', 'price' => 2450.00],
            'CT_CHEST_PLAIN' => ['code' => '3013', 'description' => 'CT Chest without contrast', 'price' => 2100.00],
            'CT_CHEST_CONTRAST' => ['code' => '3014', 'description' => 'CT Chest with contrast', 'price' => 2850.00],
            'CT_ABDOMEN_PELVIS' => ['code' => '3015', 'description' => 'CT Abdomen and Pelvis', 'price' => 3200.00],
            
            // MRI Codes
            'MRI_BRAIN_PLAIN' => ['code' => '3021', 'description' => 'MRI Brain without contrast', 'price' => 4500.00],
            'MRI_BRAIN_CONTRAST' => ['code' => '3022', 'description' => 'MRI Brain with contrast', 'price' => 5200.00],
            'MRI_SPINE_CERVICAL' => ['code' => '3023', 'description' => 'MRI Cervical Spine', 'price' => 4200.00],
            'MRI_SPINE_LUMBAR' => ['code' => '3024', 'description' => 'MRI Lumbar Spine', 'price' => 4200.00],
            'MRI_KNEE' => ['code' => '3025', 'description' => 'MRI Knee', 'price' => 3800.00],
            
            // X-Ray Codes
            'XRAY_CHEST_PA' => ['code' => '3001', 'description' => 'Chest X-Ray PA', 'price' => 320.00],
            'XRAY_CHEST_LATERAL' => ['code' => '3002', 'description' => 'Chest X-Ray Lateral', 'price' => 280.00],
            'XRAY_SKULL_AP_LAT' => ['code' => '3003', 'description' => 'Skull X-Ray AP and Lateral', 'price' => 450.00],
            'XRAY_SPINE_CERVICAL' => ['code' => '3004', 'description' => 'Cervical Spine X-Ray', 'price' => 380.00],
            
            // Ultrasound Codes
            'US_ABDOMEN' => ['code' => '3041', 'description' => 'Abdominal Ultrasound', 'price' => 850.00],
            'US_PELVIS' => ['code' => '3042', 'description' => 'Pelvic Ultrasound', 'price' => 750.00],
            'US_OBSTETRIC' => ['code' => '3043', 'description' => 'Obstetric Ultrasound', 'price' => 950.00],
            
            // Mammography Codes
            'MAMMO_BILATERAL' => ['code' => '3051', 'description' => 'Bilateral Mammography', 'price' => 1200.00],
            'MAMMO_UNILATERAL' => ['code' => '3052', 'description' => 'Unilateral Mammography', 'price' => 800.00],
            
            // Nuclear Medicine Codes
            'NM_BONE_SCAN' => ['code' => '3061', 'description' => 'Bone Scan', 'price' => 2800.00],
            'NM_THYROID_SCAN' => ['code' => '3062', 'description' => 'Thyroid Scan', 'price' => 2200.00],
            
            // PET Scan Codes
            'PET_FDG_WHOLE_BODY' => ['code' => '3071', 'description' => 'PET FDG Whole Body', 'price' => 12500.00],
            'PET_BRAIN' => ['code' => '3072', 'description' => 'PET Brain', 'price' => 8500.00]
        ];
    }
    
    /**
     * Generate comprehensive billing quote for SA medical aids
     */
    public function generateBillingQuote($procedureCodes, $medicalAidScheme, $memberNumber, $patientData) {
        try {
            $scheme = $this->medicalAidSchemes[$medicalAidScheme] ?? null;
            if (!$scheme) {
                throw new Exception("Unsupported medical aid scheme: $medicalAidScheme");
            }
            
            $quote = [
                'patient_id' => $patientData['pid'],
                'member_number' => $memberNumber,
                'scheme_details' => $scheme,
                'procedures' => [],
                'total_amount' => 0,
                'authorization_required' => $scheme['authorization_required'],
                'estimated_payment' => 0,
                'patient_copay' => 0,
                'generated_at' => date('Y-m-d H:i:s')
            ];
            
            foreach ($procedureCodes as $procedureCode) {
                $procedure = $this->nrplCodes[$procedureCode] ?? null;
                if ($procedure) {
                    $procedureQuote = [
                        'nrpl_code' => $procedure['code'],
                        'description' => $procedure['description'],
                        'tariff_amount' => $procedure['price'],
                        'scheme_rate' => $this->getSchemeRate($medicalAidScheme, $procedure['code']),
                        'authorization_code' => $this->generateAuthorizationCode($medicalAidScheme, $procedure['code'])
                    ];
                    
                    $procedureQuote['scheme_amount'] = $procedureQuote['tariff_amount'] * ($procedureQuote['scheme_rate'] / 100);
                    $procedureQuote['patient_portion'] = $procedureQuote['tariff_amount'] - $procedureQuote['scheme_amount'];
                    
                    $quote['procedures'][] = $procedureQuote;
                    $quote['total_amount'] += $procedureQuote['tariff_amount'];
                    $quote['estimated_payment'] += $procedureQuote['scheme_amount'];
                    $quote['patient_copay'] += $procedureQuote['patient_portion'];
                }
            }
            
            // Apply benefits and savings account calculations
            $quote = $this->applyBenefitsCalculation($quote, $medicalAidScheme, $memberNumber);
            
            return $quote;
            
        } catch (Exception $e) {
            throw new Exception("Billing quote generation failed: " . $e->getMessage());
        }
    }
    
    /**
     * Real-time medical aid verification
     */
    public function verifyMedicalAidStatus($medicalAidScheme, $memberNumber, $dependentCode = '00') {
        $scheme = $this->medicalAidSchemes[$medicalAidScheme] ?? null;
        if (!$scheme || !$scheme['real_time_verification']) {
            return ['verified' => false, 'message' => 'Real-time verification not available'];
        }
        
        // Simulate API call to medical aid
        $verificationData = [
            'member_number' => $memberNumber,
            'dependent_code' => $dependentCode,
            'scheme_code' => $scheme['scheme_code'],
            'verification_date' => date('Y-m-d H:i:s')
        ];
        
        // Mock response - in production this would be actual API calls
        return [
            'verified' => true,
            'member_status' => 'active',
            'benefit_year' => date('Y'),
            'available_benefits' => [
                'radiology_limit' => 50000.00,
                'radiology_used' => 12500.00,
                'radiology_remaining' => 37500.00,
                'savings_balance' => 15000.00,
                'annual_threshold_met' => false
            ],
            'authorization_required' => $scheme['authorization_required'],
            'co_payment_percentage' => 20
        ];
    }
    
    /**
     * Submit electronic claim to medical aid
     */
    public function submitElectronicClaim($claimData) {
        $scheme = $this->medicalAidSchemes[$claimData['medical_aid_scheme']] ?? null;
        if (!$scheme) {
            throw new Exception("Invalid medical aid scheme");
        }
        
        $claim = [
            'claim_number' => $this->generateClaimNumber(),
            'submission_date' => date('Y-m-d H:i:s'),
            'provider_number' => $claimData['provider_number'],
            'practice_number' => $claimData['practice_number'],
            'member_number' => $claimData['member_number'],
            'patient_data' => $claimData['patient_data'],
            'procedures' => $claimData['procedures'],
            'total_amount' => $claimData['total_amount'],
            'format' => $scheme['billing_format'],
            'endpoint' => $scheme['api_endpoint']
        ];
        
        // Generate claim in appropriate format
        switch ($scheme['billing_format']) {
            case 'XML':
                $claimDocument = $this->generateXMLClaim($claim);
                break;
            case 'EDI':
                $claimDocument = $this->generateEDIClaim($claim);
                break;
            case 'PDF':
                $claimDocument = $this->generatePDFClaim($claim);
                break;
            default:
                throw new Exception("Unsupported billing format");
        }
        
        // Store claim in database
        $this->storeClaimSubmission($claim, $claimDocument);
        
        // Submit to medical aid (mock implementation)
        return [
            'success' => true,
            'claim_number' => $claim['claim_number'],
            'reference_number' => 'REF' . uniqid(),
            'submission_status' => 'submitted',
            'expected_payment_date' => date('Y-m-d', strtotime('+14 days'))
        ];
    }
    
    /**
     * Generate XML claim format for Discovery/Bonitas
     */
    private function generateXMLClaim($claim) {
        $xml = new \SimpleXMLElement('<claim/>');
        $xml->addChild('claim_number', $claim['claim_number']);
        $xml->addChild('submission_date', $claim['submission_date']);
        $xml->addChild('provider_number', $claim['provider_number']);
        $xml->addChild('member_number', $claim['member_number']);
        
        $patient = $xml->addChild('patient');
        $patient->addChild('name', $claim['patient_data']['name']);
        $patient->addChild('id_number', $claim['patient_data']['id_number']);
        $patient->addChild('date_of_birth', $claim['patient_data']['dob']);
        
        $procedures = $xml->addChild('procedures');
        foreach ($claim['procedures'] as $proc) {
            $procedure = $procedures->addChild('procedure');
            $procedure->addChild('nrpl_code', $proc['nrpl_code']);
            $procedure->addChild('description', $proc['description']);
            $procedure->addChild('amount', $proc['amount']);
            $procedure->addChild('date_of_service', $proc['service_date']);
        }
        
        $xml->addChild('total_amount', $claim['total_amount']);
        
        return $xml->asXML();
    }
    
    /**
     * Generate EDI claim format for Momentum
     */
    private function generateEDIClaim($claim) {
        $edi = "ISA*00*          *00*          *ZZ*{$claim['provider_number']}*ZZ*MOM*" . date('ymd') . "*" . date('Hi') . "*U*00401*" . substr($claim['claim_number'], -9) . "*0*P*>\n";
        $edi .= "GS*HC*{$claim['provider_number']}*MOM*" . date('ymd') . "*" . date('Hi') . "*1*X*004010X098A1\n";
        $edi .= "ST*837*0001\n";
        $edi .= "BHT*0019*00*{$claim['claim_number']}*" . date('ymdHi') . "\n";
        
        // Add patient and procedure information
        $edi .= "NM1*85*2*RADIOLOGY PRACTICE*****XX*{$claim['practice_number']}\n";
        $edi .= "NM1*87*2*MOM\n";
        $edi .= "HL*1**20*1\n";
        $edi .= "NM1*PR*2*MOMENTUM HEALTH*****PI*MOM\n";
        
        // Patient information
        $edi .= "HL*2*1*22*0\n";
        $edi .= "SBR*P*18*{$claim['member_number']}*****CI\n";
        $edi .= "NM1*IL*1*{$claim['patient_data']['surname']}*{$claim['patient_data']['firstname']}****MI*{$claim['member_number']}\n";
        
        // Procedure lines
        foreach ($claim['procedures'] as $index => $proc) {
            $edi .= "LX*" . ($index + 1) . "\n";
            $edi .= "SV1*HC:{$proc['nrpl_code']}*{$proc['amount']}*UN*1***1\n";
            $edi .= "DTP*472*D8*{$proc['service_date']}\n";
        }
        
        $edi .= "SE*" . (substr_count($edi, "\n") + 1) . "*0001\n";
        $edi .= "GE*1*1\n";
        $edi .= "IEA*1*" . substr($claim['claim_number'], -9) . "\n";
        
        return $edi;
    }
    
    /**
     * Advanced pricing engine with dynamic tariff calculation
     */
    public function calculateDynamicPricing($procedureCode, $urgency, $timeOfDay, $patientType) {
        $basePrice = $this->nrplCodes[$procedureCode]['price'] ?? 0;
        if ($basePrice === 0) return 0;
        
        $multiplier = 1.0;
        
        // Urgency multiplier
        switch ($urgency) {
            case 'stat':
                $multiplier += 0.5; // 50% surcharge for STAT
                break;
            case 'urgent':
                $multiplier += 0.25; // 25% surcharge for urgent
                break;
        }
        
        // Time-based pricing
        $hour = (int)date('H', strtotime($timeOfDay));
        if ($hour >= 18 || $hour <= 6) {
            $multiplier += 0.3; // 30% after-hours surcharge
        }
        
        // Patient type adjustments
        switch ($patientType) {
            case 'private':
                $multiplier += 0.2; // 20% private patient premium
                break;
            case 'medical_aid':
                // Standard rate
                break;
            case 'cash':
                $multiplier -= 0.15; // 15% cash discount
                break;
        }
        
        return round($basePrice * $multiplier, 2);
    }
    
    /**
     * Generate comprehensive financial report
     */
    public function generateFinancialReport($startDate, $endDate, $reportType = 'summary') {
        $sql = "SELECT 
                    sr.medical_aid,
                    sr.billing_method,
                    sr.examination_type,
                    sr.urgency,
                    COUNT(*) as procedure_count,
                    SUM(sr.expected_cost) as total_revenue,
                    AVG(sr.expected_cost) as average_cost,
                    DATE(sr.date_completed) as procedure_date
                FROM form_sa_radiology sr 
                WHERE sr.date_completed BETWEEN ? AND ?
                AND sr.activity = 1
                GROUP BY sr.medical_aid, sr.billing_method, sr.examination_type, DATE(sr.date_completed)
                ORDER BY procedure_date DESC";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$startDate, $endDate]);
        $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        $report = [
            'period' => ['start' => $startDate, 'end' => $endDate],
            'summary' => [
                'total_procedures' => 0,
                'total_revenue' => 0,
                'average_procedure_value' => 0,
                'by_medical_aid' => [],
                'by_examination_type' => [],
                'by_urgency' => []
            ],
            'daily_breakdown' => [],
            'trends' => $this->calculateRevenueTrends($data)
        ];
        
        foreach ($data as $row) {
            $report['summary']['total_procedures'] += $row['procedure_count'];
            $report['summary']['total_revenue'] += $row['total_revenue'];
            
            // Group by medical aid
            if (!isset($report['summary']['by_medical_aid'][$row['medical_aid']])) {
                $report['summary']['by_medical_aid'][$row['medical_aid']] = [
                    'count' => 0, 'revenue' => 0
                ];
            }
            $report['summary']['by_medical_aid'][$row['medical_aid']]['count'] += $row['procedure_count'];
            $report['summary']['by_medical_aid'][$row['medical_aid']]['revenue'] += $row['total_revenue'];
            
            // Group by examination type
            if (!isset($report['summary']['by_examination_type'][$row['examination_type']])) {
                $report['summary']['by_examination_type'][$row['examination_type']] = [
                    'count' => 0, 'revenue' => 0
                ];
            }
            $report['summary']['by_examination_type'][$row['examination_type']]['count'] += $row['procedure_count'];
            $report['summary']['by_examination_type'][$row['examination_type']]['revenue'] += $row['total_revenue'];
            
            // Daily breakdown
            $report['daily_breakdown'][$row['procedure_date']] = [
                'procedures' => $row['procedure_count'],
                'revenue' => $row['total_revenue']
            ];
        }
        
        if ($report['summary']['total_procedures'] > 0) {
            $report['summary']['average_procedure_value'] = 
                $report['summary']['total_revenue'] / $report['summary']['total_procedures'];
        }
        
        return $report;
    }
    
    private function getSchemeRate($medicalAidScheme, $nrplCode) {
        // Mock implementation - in production this would query actual scheme rates
        $rates = [
            'discovery' => 100, // 100% of NRPL
            'momentum' => 95,   // 95% of NRPL
            'bonitas' => 90,    // 90% of NRPL
            'gems' => 100       // 100% of NRPL
        ];
        
        return $rates[$medicalAidScheme] ?? 80;
    }
    
    private function generateAuthorizationCode($medicalAidScheme, $nrplCode) {
        return strtoupper($medicalAidScheme) . date('ymd') . substr($nrplCode, -3) . rand(100, 999);
    }
    
    private function generateClaimNumber() {
        return 'CLM' . date('Ymd') . rand(10000, 99999);
    }
    
    private function applyBenefitsCalculation($quote, $medicalAidScheme, $memberNumber) {
        // Complex benefits calculation logic would go here
        // This is simplified for demonstration
        $quote['benefits_applied'] = true;
        $quote['savings_account_used'] = min($quote['patient_copay'], 5000); // Max R5000 from savings
        $quote['final_patient_amount'] = max(0, $quote['patient_copay'] - $quote['savings_account_used']);
        
        return $quote;
    }
    
    private function storeClaimSubmission($claim, $claimDocument) {
        $sql = "INSERT INTO sa_claims_submitted 
                (claim_number, medical_aid_scheme, member_number, total_amount, 
                 claim_document, submission_date, status) 
                VALUES (?, ?, ?, ?, ?, ?, 'submitted')";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $claim['claim_number'],
            $claim['medical_aid_scheme'],
            $claim['member_number'],
            $claim['total_amount'],
            $claimDocument,
            $claim['submission_date']
        ]);
    }
    
    private function calculateRevenueTrends($data) {
        // Advanced trend analysis would go here
        return [
            'growth_rate' => 0.15, // 15% growth
            'seasonal_factors' => [],
            'predicted_next_month' => 0
        ];
    }
}
