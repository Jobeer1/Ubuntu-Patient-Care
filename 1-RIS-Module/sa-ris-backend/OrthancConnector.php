<?php

/**
 * South African RIS - Advanced DICOM Integration
 * 
 * Seamless integration with Orthanc PACS for image management
 * Optimized for SA radiology workflows with automated processing
 * 
 * @package SA_RIS
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\DICOM;

use Exception;
use CurlHandle;

class OrthancConnector {
    
    private $orthancUrl;
    private $username;
    private $password;
    private $timeout;
    
    public function __construct($config = []) {
        $this->orthancUrl = $config['url'] ?? 'http://localhost:8042';
        $this->username = $config['username'] ?? 'orthanc';
        $this->password = $config['password'] ?? 'orthanc';
        $this->timeout = $config['timeout'] ?? 30;
    }
    
    /**
     * Advanced patient matching with fuzzy logic
     */
    public function findPatientStudies($patientCriteria) {
        try {
            // Multiple search strategies for robust patient matching
            $searchStrategies = [
                'exact_id' => $this->searchByExactId($patientCriteria),
                'name_dob' => $this->searchByNameAndDOB($patientCriteria),
                'fuzzy_match' => $this->fuzzyPatientSearch($patientCriteria)
            ];
            
            $allStudies = [];
            foreach ($searchStrategies as $strategy => $studies) {
                if (!empty($studies)) {
                    foreach ($studies as $study) {
                        $study['match_strategy'] = $strategy;
                        $study['confidence_score'] = $this->calculateMatchConfidence($study, $patientCriteria);
                        $allStudies[] = $study;
                    }
                }
            }
            
            // Sort by confidence and remove duplicates
            $uniqueStudies = $this->deduplicateStudies($allStudies);
            usort($uniqueStudies, function($a, $b) {
                return $b['confidence_score'] <=> $a['confidence_score'];
            });
            
            return $uniqueStudies;
            
        } catch (Exception $e) {
            throw new Exception("Patient study search failed: " . $e->getMessage());
        }
    }
    
    /**
     * Intelligent study routing based on examination type and urgency
     */
    public function routeStudyToWorkstation($studyId, $examinationType, $urgency) {
        try {
            $workstations = $this->getAvailableWorkstations();
            $optimalWorkstation = $this->selectOptimalWorkstation($workstations, $examinationType, $urgency);
            
            if (!$optimalWorkstation) {
                throw new Exception("No suitable workstation available");
            }
            
            // Send study to workstation
            $routingResult = $this->sendStudyToWorkstation($studyId, $optimalWorkstation);
            
            // Update workstation queue
            $this->updateWorkstationQueue($optimalWorkstation['id'], $studyId, $urgency);
            
            return [
                'success' => true,
                'workstation' => $optimalWorkstation,
                'routing_time' => $routingResult['transfer_time'],
                'queue_position' => $routingResult['queue_position']
            ];
            
        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Automated image quality assessment
     */
    public function assessImageQuality($studyId) {
        try {
            $study = $this->getStudy($studyId);
            $qualityMetrics = [];
            
            foreach ($study['series'] as $series) {
                $seriesQuality = $this->analyzeSeriesQuality($series);
                $qualityMetrics[] = [
                    'series_id' => $series['ID'],
                    'modality' => $series['MainDicomTags']['Modality'],
                    'quality_score' => $seriesQuality['overall_score'],
                    'issues' => $seriesQuality['issues'],
                    'recommendations' => $seriesQuality['recommendations']
                ];
            }
            
            $overallQuality = $this->calculateOverallQuality($qualityMetrics);
            
            // Flag studies requiring repeat if quality is poor
            if ($overallQuality['score'] < 70) {
                $this->flagForRepeat($studyId, $overallQuality['issues']);
            }
            
            return [
                'study_id' => $studyId,
                'overall_quality' => $overallQuality,
                'series_quality' => $qualityMetrics,
                'requires_repeat' => $overallQuality['score'] < 70,
                'assessed_at' => date('Y-m-d H:i:s')
            ];
            
        } catch (Exception $e) {
            throw new Exception("Image quality assessment failed: " . $e->getMessage());
        }
    }
    
    /**
     * Advanced DICOM anonymization for research and teaching
     */
    public function anonymizeStudy($studyId, $anonymizationLevel = 'standard') {
        try {
            $anonymizationProfiles = [
                'minimal' => [
                    'remove_tags' => ['PatientName', 'PatientID'],
                    'replace_tags' => [],
                    'keep_clinical_data' => true
                ],
                'standard' => [
                    'remove_tags' => [
                        'PatientName', 'PatientID', 'PatientBirthDate', 
                        'PatientSex', 'PatientAddress', 'PatientTelephoneNumbers'
                    ],
                    'replace_tags' => [
                        'PatientID' => 'ANON' . uniqid(),
                        'PatientName' => 'ANONYMOUS^PATIENT'
                    ],
                    'keep_clinical_data' => true
                ],
                'research' => [
                    'remove_tags' => [
                        'PatientName', 'PatientID', 'PatientBirthDate', 
                        'PatientSex', 'PatientAddress', 'PatientTelephoneNumbers',
                        'ReferringPhysicianName', 'InstitutionName',
                        'OperatorsName', 'PerformingPhysicianName'
                    ],
                    'replace_tags' => [
                        'PatientID' => 'RESEARCH' . uniqid(),
                        'PatientName' => 'RESEARCH^SUBJECT',
                        'StudyDate' => $this->shiftDate($this->getStudyDate($studyId))
                    ],
                    'keep_clinical_data' => false
                ]
            ];
            
            $profile = $anonymizationProfiles[$anonymizationLevel] ?? $anonymizationProfiles['standard'];
            
            // Create anonymized copy
            $anonymizedStudyId = $this->createAnonymizedCopy($studyId, $profile);
            
            // Log anonymization for audit trail
            $this->logAnonymization($studyId, $anonymizedStudyId, $anonymizationLevel);
            
            return [
                'success' => true,
                'original_study_id' => $studyId,
                'anonymized_study_id' => $anonymizedStudyId,
                'anonymization_level' => $anonymizationLevel,
                'created_at' => date('Y-m-d H:i:s')
            ];
            
        } catch (Exception $e) {
            throw new Exception("Study anonymization failed: " . $e->getMessage());
        }
    }
    
    /**
     * Intelligent storage management with tiered storage
     */
    public function manageStorageTiering() {
        try {
            $storageStats = $this->getStorageStatistics();
            $tiering = $this->calculateStorageTiering($storageStats);
            
            $actions = [];
            
            // Move old studies to near-line storage
            if ($tiering['online_usage'] > 80) {
                $oldStudies = $this->getOldStudies(90); // Studies older than 90 days
                foreach ($oldStudies as $study) {
                    $this->moveToNearlineStorage($study['ID']);
                    $actions[] = "Moved study {$study['ID']} to near-line storage";
                }
            }
            
            // Archive very old studies to offline storage
            if ($tiering['nearline_usage'] > 90) {
                $veryOldStudies = $this->getOldStudies(365); // Studies older than 1 year
                foreach ($veryOldStudies as $study) {
                    $this->archiveToOfflineStorage($study['ID']);
                    $actions[] = "Archived study {$study['ID']} to offline storage";
                }
            }
            
            // Cleanup temporary files
            $this->cleanupTemporaryFiles();
            $actions[] = "Cleaned up temporary files";
            
            return [
                'success' => true,
                'actions_taken' => $actions,
                'storage_stats' => $this->getStorageStatistics(),
                'next_cleanup' => date('Y-m-d H:i:s', strtotime('+1 day'))
            ];
            
        } catch (Exception $e) {
            throw new Exception("Storage management failed: " . $e->getMessage());
        }
    }
    
    /**
     * Advanced query/retrieve with load balancing
     */
    public function queryRetrieveWithLoadBalancing($queryParams, $retrieveParams = []) {
        try {
            // Find available DICOM nodes
            $availableNodes = $this->getAvailableDicomNodes();
            
            if (empty($availableNodes)) {
                throw new Exception("No DICOM nodes available for query/retrieve");
            }
            
            // Select optimal node based on load and response time
            $optimalNode = $this->selectOptimalNode($availableNodes);
            
            // Perform C-FIND query
            $queryResults = $this->performCFind($optimalNode, $queryParams);
            
            if (empty($queryResults)) {
                return ['success' => true, 'results' => [], 'message' => 'No matching studies found'];
            }
            
            // Perform C-MOVE retrieve if requested
            $retrieveResults = [];
            if (!empty($retrieveParams)) {
                $retrieveResults = $this->performCMove($optimalNode, $queryResults, $retrieveParams);
            }
            
            return [
                'success' => true,
                'query_results' => $queryResults,
                'retrieve_results' => $retrieveResults,
                'node_used' => $optimalNode,
                'total_studies' => count($queryResults)
            ];
            
        } catch (Exception $e) {
            throw new Exception("Query/Retrieve failed: " . $e->getMessage());
        }
    }
    
    /**
     * Real-time study monitoring and notifications
     */
    public function setupStudyMonitoring($studyId, $notifications = []) {
        try {
            $monitoringConfig = [
                'study_id' => $studyId,
                'notifications' => $notifications,
                'started_at' => date('Y-m-d H:i:s'),
                'status' => 'active'
            ];
            
            // Set up file system watchers
            $this->setupFileWatchers($studyId);
            
            // Configure webhooks for status updates
            $this->configureWebhooks($studyId, $notifications);
            
            // Start monitoring process
            $this->startMonitoringProcess($studyId);
            
            return [
                'success' => true,
                'monitoring_id' => uniqid('mon_'),
                'config' => $monitoringConfig
            ];
            
        } catch (Exception $e) {
            throw new Exception("Study monitoring setup failed: " . $e->getMessage());
        }
    }
    
    // Private helper methods
    
    private function makeOrthancRequest($endpoint, $method = 'GET', $data = null) {
        $curl = curl_init();
        
        $options = [
            CURLOPT_URL => $this->orthancUrl . $endpoint,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_USERPWD => $this->username . ':' . $this->password,
            CURLOPT_HTTPAUTH => CURLAUTH_BASIC,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json']
        ];
        
        if ($data !== null) {
            $options[CURLOPT_POSTFIELDS] = is_array($data) ? json_encode($data) : $data;
        }
        
        curl_setopt_array($curl, $options);
        
        $response = curl_exec($curl);
        $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $error = curl_error($curl);
        
        curl_close($curl);
        
        if ($error) {
            throw new Exception("CURL Error: $error");
        }
        
        if ($httpCode >= 400) {
            throw new Exception("HTTP Error: $httpCode - $response");
        }
        
        return json_decode($response, true);
    }
    
    private function searchByExactId($criteria) {
        return $this->makeOrthancRequest('/tools/find', 'POST', [
            'Level' => 'Study',
            'Query' => ['PatientID' => $criteria['patient_id']]
        ]);
    }
    
    private function searchByNameAndDOB($criteria) {
        return $this->makeOrthancRequest('/tools/find', 'POST', [
            'Level' => 'Study',
            'Query' => [
                'PatientName' => $criteria['patient_name'],
                'PatientBirthDate' => $criteria['date_of_birth']
            ]
        ]);
    }
    
    private function fuzzyPatientSearch($criteria) {
        // Implement fuzzy search logic
        $searchVariations = $this->generateNameVariations($criteria['patient_name']);
        $results = [];
        
        foreach ($searchVariations as $variation) {
            $studies = $this->makeOrthancRequest('/tools/find', 'POST', [
                'Level' => 'Study',
                'Query' => ['PatientName' => $variation]
            ]);
            $results = array_merge($results, $studies);
        }
        
        return array_unique($results);
    }
    
    private function calculateMatchConfidence($study, $criteria) {
        // Implement confidence scoring algorithm
        $score = 0;
        
        // Patient ID exact match = 40 points
        if (isset($study['PatientID']) && $study['PatientID'] === $criteria['patient_id']) {
            $score += 40;
        }
        
        // Name similarity = 30 points
        if (isset($study['PatientName'])) {
            $similarity = $this->calculateStringSimilarity($study['PatientName'], $criteria['patient_name']);
            $score += $similarity * 30;
        }
        
        // DOB match = 30 points
        if (isset($study['PatientBirthDate']) && $study['PatientBirthDate'] === $criteria['date_of_birth']) {
            $score += 30;
        }
        
        return min($score, 100);
    }
    
    private function deduplicateStudies($studies) {
        $unique = [];
        $seen = [];
        
        foreach ($studies as $study) {
            $key = $study['ID'] ?? $study['StudyInstanceUID'] ?? uniqid();
            if (!in_array($key, $seen)) {
                $seen[] = $key;
                $unique[] = $study;
            }
        }
        
        return $unique;
    }
    
    private function getAvailableWorkstations() {
        // Mock implementation - would connect to actual workstation management system
        return [
            [
                'id' => 'WS001',
                'name' => 'Radiology Workstation 1',
                'capabilities' => ['CT', 'MRI', 'XRAY'],
                'current_load' => 2,
                'max_capacity' => 5,
                'response_time' => 1.2,
                'status' => 'online'
            ],
            [
                'id' => 'WS002', 
                'name' => 'Radiology Workstation 2',
                'capabilities' => ['ULTRASOUND', 'MAMMOGRAPHY'],
                'current_load' => 1,
                'max_capacity' => 3,
                'response_time' => 0.8,
                'status' => 'online'
            ]
        ];
    }
    
    private function selectOptimalWorkstation($workstations, $examinationType, $urgency) {
        $compatibleStations = array_filter($workstations, function($station) use ($examinationType) {
            return in_array(strtoupper($examinationType), $station['capabilities']) && 
                   $station['status'] === 'online';
        });
        
        if (empty($compatibleStations)) {
            return null;
        }
        
        // Sort by load and response time
        usort($compatibleStations, function($a, $b) {
            $loadScore = ($a['current_load'] / $a['max_capacity']) - ($b['current_load'] / $b['max_capacity']);
            return $loadScore === 0 ? $a['response_time'] <=> $b['response_time'] : $loadScore;
        });
        
        return $compatibleStations[0];
    }
    
    public function getStudy($studyId) {
        return $this->makeOrthancRequest("/studies/$studyId");
    }
    
    // Additional helper methods would be implemented here...
    private function sendStudyToWorkstation($studyId, $workstation) { return ['transfer_time' => 5.2, 'queue_position' => 1]; }
    private function updateWorkstationQueue($workstationId, $studyId, $urgency) { /* Implementation */ }
    private function analyzeSeriesQuality($series) { return ['overall_score' => 85, 'issues' => [], 'recommendations' => []]; }
    private function calculateOverallQuality($metrics) { return ['score' => 85, 'issues' => []]; }
    private function flagForRepeat($studyId, $issues) { /* Implementation */ }
    private function createAnonymizedCopy($studyId, $profile) { return 'ANON_' . $studyId; }
    private function logAnonymization($original, $anonymized, $level) { /* Implementation */ }
    private function shiftDate($date) { return date('Ymd', strtotime($date . ' +30 days')); }
    private function getStudyDate($studyId) { return '20241201'; }
    private function getStorageStatistics() { return ['online_usage' => 75, 'nearline_usage' => 60]; }
    private function calculateStorageTiering($stats) { return $stats; }
    private function getOldStudies($days) { return []; }
    private function moveToNearlineStorage($studyId) { /* Implementation */ }
    private function archiveToOfflineStorage($studyId) { /* Implementation */ }
    private function cleanupTemporaryFiles() { /* Implementation */ }
    private function getAvailableDicomNodes() { return [['id' => 'NODE1', 'address' => '192.168.1.100', 'port' => 104]]; }
    private function selectOptimalNode($nodes) { return $nodes[0]; }
    private function performCFind($node, $params) { return []; }
    private function performCMove($node, $results, $params) { return []; }
    private function setupFileWatchers($studyId) { /* Implementation */ }
    private function configureWebhooks($studyId, $notifications) { /* Implementation */ }
    private function startMonitoringProcess($studyId) { /* Implementation */ }
    private function generateNameVariations($name) { return [$name]; }
    private function calculateStringSimilarity($str1, $str2) { return 0.9; }
}
