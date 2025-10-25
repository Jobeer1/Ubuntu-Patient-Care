<?php

/**
 * Healthbridge Clearing House Integration
 * 
 * This module handles all interactions with Healthbridge, the primary
 * clearing house for South African medical aid claims processing.
 * 
 * Features:
 * - Electronic claim submission
 * - Real-time status tracking
 * - Automated reconciliation
 * - Batch processing support
 * - Error handling and retry logic
 * 
 * @package SA_RIS_Healthbridge
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\Healthbridge;

use Exception;
use PDO;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class HealthbridgeConnector {
    
    private $apiClient;
    private $db;
    private $config;
    private $logger;
    
    public function __construct(PDO $database, array $config) {
        $this->db = $database;
        $this->config = $config;
        $this->initializeApiClient();
        $this->initializeLogger();
    }
    
    private function initializeApiClient() {
        $this->apiClient = new Client([
            'base_uri' => $this->config['healthbridge_api_url'],
            'timeout' => 30,
            'verify' => true,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
                'User-Agent' => 'SA-RIS-Healthbridge-Connector/1.0'
            ]
        ]);
    }
    
    private function initializeLogger() {
        // Initialize logging for Healthbridge transactions
        $this->logger = new \Monolog\Logger('healthbridge');
        $this->logger->pushHandler(new \Monolog\Handler\StreamHandler('/var/log/healthbridge/connector.log'));
    }
    
    /**
     * Authenticate with Healthbridge API
     */
    public function authenticate() {
        try {
            $response = $this->apiClient->post('/auth/token', [
                'json' => [
                    'client_id' => $this->config['client_id'],
                    'client_secret' => $this->config['client_secret'],
                    'grant_type' => 'client_credentials',
                    'scope' => 'claims:submit claims:status'
                ]
            ]);
            
            $data = json_decode($response->getBody(), true);
            
            if (isset($data['access_token'])) {
                $this->storeAccessToken($data);
                $this->logger->info('Healthbridge authentication successful');
                return [
                    'success' => true,
                    'access_token' => $data['access_token'],
                    'expires_in' => $data['expires_in']
                ];
            }
            
            throw new Exception('Invalid authentication response');
            
        } catch (RequestException $e) {
            $this->logger->error('Healthbridge authentication failed: ' . $e->getMessage());
            return [
                'success' => false,
                'error' => 'Authentication failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Submit single claim to Healthbridge
     */
    public function submitClaim($claimData) {
        try {
            // Ensure we have a valid access token
            $token = $this->getValidAccessToken();
            if (!$token) {
                $authResult = $this->authenticate();
                if (!$authResult['success']) {
                    return $authResult;
                }
                $token = $authResult['access_token'];
            }
            
            // Prepare claim data in Healthbridge format
            $healthbridgeData = $this->formatClaimForHealthbridge($claimData);
            
            // Validate claim data
            $validation = $this->validateClaimData($healthbridgeData);
            if (!$validation['valid']) {
                return [
                    'success' => false,
                    'error' => 'Claim validation failed',
                    'validation_errors' => $validation['errors']
                ];
            }
            
            // Submit claim
            $response = $this->apiClient->post('/claims/submit', [
                'headers' => [
                    'Authorization' => 'Bearer ' . $token
                ],
                'json' => $healthbridgeData
            ]);
            
            $result = json_decode($response->getBody(), true);
            
            // Store submission record
            $this->storeClaimSubmission($claimData, $result);
            
            $this->logger->info('Claim submitted successfully', [
                'claim_id' => $claimData['claim_id'],
                'healthbridge_ref' => $result['reference_number']
            ]);
            
            return [
                'success' => true,
                'healthbridge_reference' => $result['reference_number'],
                'submission_id' => $result['submission_id'],
                'status' => $result['status'],
                'estimated_processing_time' => $result['estimated_processing_days'] ?? 14
            ];
            
        } catch (RequestException $e) {
            $this->logger->error('Claim submission failed', [
                'claim_id' => $claimData['claim_id'],
                'error' => $e->getMessage()
            ]);
            
            return [
                'success' => false,
                'error' => 'Claim submission failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Submit batch of claims to Healthbridge
     */
    public function submitBatchClaims($claimsData) {
        try {
            $token = $this->getValidAccessToken();
            if (!$token) {
                $authResult = $this->authenticate();
                if (!$authResult['success']) {
                    return $authResult;
                }
                $token = $authResult['access_token'];
            }
            
            $batchData = [
                'batch_id' => 'BATCH_' . date('YmdHis') . '_' . uniqid(),
                'practice_code' => $this->config['practice_code'],
                'submission_date' => date('Y-m-d H:i:s'),
                'claims' => []
            ];
            
            $validClaims = 0;
            $invalidClaims = [];
            
            foreach ($claimsData as $index => $claimData) {
                $healthbridgeData = $this->formatClaimForHealthbridge($claimData);
                $validation = $this->validateClaimData($healthbridgeData);
                
                if ($validation['valid']) {
                    $batchData['claims'][] = $healthbridgeData;
                    $validClaims++;
                } else {
                    $invalidClaims[] = [
                        'index' => $index,
                        'claim_id' => $claimData['claim_id'],
                        'errors' => $validation['errors']
                    ];
                }
            }
            
            if ($validClaims === 0) {
                return [
                    'success' => false,
                    'error' => 'No valid claims in batch',
                    'invalid_claims' => $invalidClaims
                ];
            }
            
            // Submit batch
            $response = $this->apiClient->post('/claims/batch-submit', [
                'headers' => [
                    'Authorization' => 'Bearer ' . $token
                ],
                'json' => $batchData
            ]);
            
            $result = json_decode($response->getBody(), true);
            
            // Store batch submission record
            $this->storeBatchSubmission($batchData, $result);
            
            $this->logger->info('Batch claims submitted successfully', [
                'batch_id' => $batchData['batch_id'],
                'valid_claims' => $validClaims,
                'invalid_claims' => count($invalidClaims)
            ]);
            
            return [
                'success' => true,
                'batch_id' => $batchData['batch_id'],
                'healthbridge_batch_ref' => $result['batch_reference'],
                'valid_claims' => $validClaims,
                'invalid_claims' => $invalidClaims,
                'estimated_processing_time' => $result['estimated_processing_days'] ?? 14
            ];
            
        } catch (RequestException $e) {
            $this->logger->error('Batch submission failed', [
                'error' => $e->getMessage()
            ]);
            
            return [
                'success' => false,
                'error' => 'Batch submission failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Check status of submitted claims
     */
    public function checkClaimStatus($healthbridgeReference) {
        try {
            $token = $this->getValidAccessToken();
            if (!$token) {
                $authResult = $this->authenticate();
                if (!$authResult['success']) {
                    return $authResult;
                }
                $token = $authResult['access_token'];
            }
            
            $response = $this->apiClient->get("/claims/status/{$healthbridgeReference}", [
                'headers' => [
                    'Authorization' => 'Bearer ' . $token
                ]
            ]);
            
            $result = json_decode($response->getBody(), true);
            
            // Update local status
            $this->updateClaimStatus($healthbridgeReference, $result);
            
            return [
                'success' => true,
                'status' => $result['status'],
                'processing_date' => $result['processing_date'] ?? null,
                'payment_date' => $result['payment_date'] ?? null,
                'payment_amount' => $result['payment_amount'] ?? null,
                'rejection_reason' => $result['rejection_reason'] ?? null,
                'last_updated' => $result['last_updated']
            ];
            
        } catch (RequestException $e) {
            $this->logger->error('Status check failed', [
                'reference' => $healthbridgeReference,
                'error' => $e->getMessage()
            ]);
            
            return [
                'success' => false,
                'error' => 'Status check failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Get payment remittance advice
     */
    public function getRemittanceAdvice($paymentReference) {
        try {
            $token = $this->getValidAccessToken();
            if (!$token) {
                $authResult = $this->authenticate();
                if (!$authResult['success']) {
                    return $authResult;
                }
                $token = $authResult['access_token'];
            }
            
            $response = $this->apiClient->get("/payments/remittance/{$paymentReference}", [
                'headers' => [
                    'Authorization' => 'Bearer ' . $token
                ]
            ]);
            
            $result = json_decode($response->getBody(), true);
            
            return [
                'success' => true,
                'payment_reference' => $paymentReference,
                'payment_date' => $result['payment_date'],
                'total_amount' => $result['total_amount'],
                'claims' => $result['claims'],
                'bank_details' => $result['bank_details']
            ];
            
        } catch (RequestException $e) {
            return [
                'success' => false,
                'error' => 'Remittance retrieval failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Process automated reconciliation
     */
    public function processReconciliation($startDate, $endDate) {
        try {
            // Get all submitted claims in date range
            $submittedClaims = $this->getSubmittedClaimsInRange($startDate, $endDate);
            
            $reconciliationResults = [
                'total_claims' => count($submittedClaims),
                'processed_claims' => 0,
                'paid_claims' => 0,
                'rejected_claims' => 0,
                'pending_claims' => 0,
                'total_payments' => 0,
                'discrepancies' => []
            ];
            
            foreach ($submittedClaims as $claim) {
                $statusResult = $this->checkClaimStatus($claim['healthbridge_reference']);
                
                if ($statusResult['success']) {
                    $reconciliationResults['processed_claims']++;
                    
                    switch ($statusResult['status']) {
                        case 'paid':
                            $reconciliationResults['paid_claims']++;
                            $reconciliationResults['total_payments'] += $statusResult['payment_amount'];
                            break;
                        case 'rejected':
                            $reconciliationResults['rejected_claims']++;
                            break;
                        case 'pending':
                        case 'processing':
                            $reconciliationResults['pending_claims']++;
                            break;
                    }
                    
                    // Check for discrepancies
                    if ($statusResult['payment_amount'] && 
                        $statusResult['payment_amount'] != $claim['submitted_amount']) {
                        $reconciliationResults['discrepancies'][] = [
                            'claim_id' => $claim['claim_id'],
                            'submitted_amount' => $claim['submitted_amount'],
                            'paid_amount' => $statusResult['payment_amount'],
                            'difference' => $statusResult['payment_amount'] - $claim['submitted_amount']
                        ];
                    }
                }
                
                // Add small delay to avoid rate limiting
                usleep(100000); // 0.1 second
            }
            
            // Store reconciliation report
            $this->storeReconciliationReport($reconciliationResults, $startDate, $endDate);
            
            return [
                'success' => true,
                'reconciliation' => $reconciliationResults
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => 'Reconciliation failed: ' . $e->getMessage()
            ];
        }
    }
    
    /**
     * Format claim data for Healthbridge API
     */
    private function formatClaimForHealthbridge($claimData) {
        return [
            'claim_number' => $claimData['claim_number'],
            'practice_code' => $this->config['practice_code'],
            'provider_details' => [
                'practice_number' => $claimData['practice_number'],
                'provider_name' => $claimData['provider_name'],
                'contact_details' => $claimData['contact_details']
            ],
            'patient_details' => [
                'member_number' => $claimData['member_number'],
                'dependent_code' => $claimData['dependent_code'] ?? '00',
                'id_number' => $claimData['patient_id_number'],
                'first_name' => $claimData['patient_first_name'],
                'surname' => $claimData['patient_surname'],
                'date_of_birth' => $claimData['patient_dob']
            ],
            'medical_aid_details' => [
                'scheme_code' => $claimData['medical_aid_scheme_code'],
                'scheme_name' => $claimData['medical_aid_scheme_name']
            ],
            'service_details' => [
                'service_date' => $claimData['service_date'],
                'referring_doctor' => $claimData['referring_doctor'],
                'icd10_codes' => $claimData['icd10_codes'],
                'procedures' => array_map(function($proc) {
                    return [
                        'nrpl_code' => $proc['nrpl_code'],
                        'description' => $proc['description'],
                        'quantity' => $proc['quantity'] ?? 1,
                        'unit_price' => $proc['unit_price'],
                        'total_price' => $proc['total_price'],
                        'modifier' => $proc['modifier'] ?? null
                    ];
                }, $claimData['procedures'])
            ],
            'financial_details' => [
                'total_amount' => $claimData['total_amount'],
                'vat_amount' => $claimData['vat_amount'] ?? 0,
                'currency' => 'ZAR'
            ],
            'submission_metadata' => [
                'submission_date' => date('Y-m-d H:i:s'),
                'software_version' => 'SA-RIS-v1.0',
                'batch_number' => $claimData['batch_number'] ?? null
            ]
        ];
    }
    
    /**
     * Validate claim data before submission
     */
    private function validateClaimData($claimData) {
        $errors = [];
        
        // Required fields validation
        if (empty($claimData['claim_number'])) {
            $errors[] = 'Claim number is required';
        }
        
        if (empty($claimData['patient_details']['member_number'])) {
            $errors[] = 'Member number is required';
        }
        
        if (empty($claimData['patient_details']['id_number'])) {
            $errors[] = 'Patient ID number is required';
        }
        
        if (empty($claimData['service_details']['service_date'])) {
            $errors[] = 'Service date is required';
        }
        
        if (empty($claimData['service_details']['icd10_codes'])) {
            $errors[] = 'At least one ICD-10 diagnosis code is required';
        }
        
        if (empty($claimData['service_details']['procedures'])) {
            $errors[] = 'At least one procedure is required';
        }
        
        // Business rule validations
        if (!empty($claimData['service_details']['service_date'])) {
            $serviceDate = strtotime($claimData['service_details']['service_date']);
            $currentDate = time();
            $maxAge = 365 * 24 * 60 * 60; // 1 year
            
            if ($serviceDate > $currentDate) {
                $errors[] = 'Service date cannot be in the future';
            }
            
            if (($currentDate - $serviceDate) > $maxAge) {
                $errors[] = 'Service date is too old (maximum 1 year)';
            }
        }
        
        // Validate total amount
        if (isset($claimData['financial_details']['total_amount'])) {
            $calculatedTotal = array_sum(array_column($claimData['service_details']['procedures'], 'total_price'));
            if (abs($calculatedTotal - $claimData['financial_details']['total_amount']) > 0.01) {
                $errors[] = 'Total amount does not match sum of procedure amounts';
            }
        }
        
        return [
            'valid' => empty($errors),
            'errors' => $errors
        ];
    }
    
    // Database operations
    
    private function storeAccessToken($tokenData) {
        $sql = "INSERT INTO healthbridge_tokens (access_token, expires_at, created_at) 
                VALUES (?, ?, NOW()) 
                ON DUPLICATE KEY UPDATE 
                access_token = VALUES(access_token), 
                expires_at = VALUES(expires_at), 
                updated_at = NOW()";
        
        $expiresAt = date('Y-m-d H:i:s', time() + $tokenData['expires_in']);
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$tokenData['access_token'], $expiresAt]);
    }
    
    private function getValidAccessToken() {
        $sql = "SELECT access_token FROM healthbridge_tokens 
                WHERE expires_at > NOW() 
                ORDER BY created_at DESC LIMIT 1";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute();
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        
        return $result ? $result['access_token'] : null;
    }
    
    private function storeClaimSubmission($claimData, $result) {
        $sql = "INSERT INTO healthbridge_submissions 
                (claim_id, claim_number, healthbridge_reference, submission_id, 
                 status, submitted_amount, submission_date, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, NOW(), NOW())";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $claimData['claim_id'],
            $claimData['claim_number'],
            $result['reference_number'],
            $result['submission_id'],
            $result['status'],
            $claimData['total_amount']
        ]);
    }
    
    private function storeBatchSubmission($batchData, $result) {
        $sql = "INSERT INTO healthbridge_batch_submissions 
                (batch_id, healthbridge_batch_ref, claims_count, 
                 submission_date, status, created_at) 
                VALUES (?, ?, ?, NOW(), ?, NOW())";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $batchData['batch_id'],
            $result['batch_reference'],
            count($batchData['claims']),
            $result['status']
        ]);
    }
    
    private function updateClaimStatus($healthbridgeReference, $statusData) {
        $sql = "UPDATE healthbridge_submissions 
                SET status = ?, payment_date = ?, payment_amount = ?, 
                    rejection_reason = ?, last_status_check = NOW() 
                WHERE healthbridge_reference = ?";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $statusData['status'],
            $statusData['payment_date'] ?? null,
            $statusData['payment_amount'] ?? null,
            $statusData['rejection_reason'] ?? null,
            $healthbridgeReference
        ]);
    }
    
    private function getSubmittedClaimsInRange($startDate, $endDate) {
        $sql = "SELECT * FROM healthbridge_submissions 
                WHERE submission_date BETWEEN ? AND ? 
                ORDER BY submission_date";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$startDate, $endDate]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    private function storeReconciliationReport($results, $startDate, $endDate) {
        $sql = "INSERT INTO healthbridge_reconciliation_reports 
                (start_date, end_date, total_claims, processed_claims, 
                 paid_claims, rejected_claims, pending_claims, 
                 total_payments, discrepancies_count, report_data, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())";
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute([
            $startDate,
            $endDate,
            $results['total_claims'],
            $results['processed_claims'],
            $results['paid_claims'],
            $results['rejected_claims'],
            $results['pending_claims'],
            $results['total_payments'],
            count($results['discrepancies']),
            json_encode($results)
        ]);
    }
}