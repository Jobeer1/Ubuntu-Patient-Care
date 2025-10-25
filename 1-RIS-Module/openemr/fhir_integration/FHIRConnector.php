<?php

/**
 * HL7 FHIR R4 Integration Module for SA-RIS
 *
 * Implements modern HL7 FHIR v4.0+ standards for clinical data exchange
 * Optimized for South African healthcare workflows and compliance
 *
 * @package SA_RIS_FHIR
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\FHIR;

use Exception;
use PDO;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class FHIRConnector {

    private $fhirServerUrl;
    private $apiClient;
    private $db;
    private $config;
    private $logger;

    public function __construct(PDO $database, array $config) {
        $this->db = $database;
        $this->config = $config;
        $this->fhirServerUrl = $config['fhir_server_url'] ?? 'https://fhir.sacoronavirus.co.za/r4';
        $this->initializeApiClient();
        $this->initializeLogger();
    }

    private function initializeApiClient() {
        $this->apiClient = new Client([
            'base_uri' => $this->fhirServerUrl,
            'timeout' => 30,
            'verify' => true,
            'headers' => [
                'Content-Type' => 'application/fhir+json',
                'Accept' => 'application/fhir+json',
                'User-Agent' => 'SA-RIS-FHIR-Connector/1.0'
            ]
        ]);
    }

    private function initializeLogger() {
        $this->logger = new \Monolog\Logger('fhir');
        $this->logger->pushHandler(new \Monolog\Handler\StreamHandler('/var/log/fhir/connector.log'));
    }

    /**
     * Create FHIR Patient Resource
     */
    public function createPatientResource($patientData) {
        try {
            $fhirPatient = $this->mapToFHIRPatient($patientData);

            $response = $this->apiClient->post('/Patient', [
                'json' => $fhirPatient
            ]);

            $result = json_decode($response->getBody(), true);

            $this->logger->info('FHIR Patient created', [
                'patient_id' => $patientData['id'],
                'fhir_id' => $result['id']
            ]);

            return [
                'success' => true,
                'fhir_id' => $result['id'],
                'resource' => $result
            ];

        } catch (RequestException $e) {
            $this->logger->error('FHIR Patient creation failed: ' . $e->getMessage());
            return [
                'success' => false,
                'error' => 'Patient creation failed: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Map SA patient data to FHIR Patient resource
     */
    private function mapToFHIRPatient($patientData) {
        return [
            'resourceType' => 'Patient',
            'identifier' => [
                [
                    'system' => 'http://www.samedicalaid.co.za',
                    'value' => $patientData['medical_aid_number'] ?? $patientData['id']
                ]
            ],
            'name' => [
                [
                    'family' => $patientData['surname'],
                    'given' => [$patientData['first_name']],
                    'prefix' => $patientData['title'] ? [$patientData['title']] : []
                ]
            ],
            'gender' => $this->mapGender($patientData['gender']),
            'birthDate' => $patientData['date_of_birth'],
            'address' => [
                [
                    'country' => 'ZA',
                    'state' => $patientData['province'],
                    'city' => $patientData['city'],
                    'postalCode' => $patientData['postal_code'],
                    'line' => [$patientData['address_line_1']]
                ]
            ],
            'telecom' => [
                [
                    'system' => 'phone',
                    'value' => $patientData['phone'],
                    'use' => 'home'
                ],
                [
                    'system' => 'email',
                    'value' => $patientData['email']
                ]
            ],
            'extension' => [
                [
                    'url' => 'http://hl7.org/fhir/StructureDefinition/patient-nationality',
                    'valueCodeableConcept' => [
                        'coding' => [
                            [
                                'system' => 'urn:iso:std:iso:3166',
                                'code' => 'ZA',
                                'display' => 'South Africa'
                            ]
                        ]
                    ]
                ]
            ]
        ];
    }

    /**
     * Map gender to FHIR codes
     */
    private function mapGender($gender) {
        $genderMap = [
            'M' => 'male',
            'F' => 'female',
            'O' => 'other',
            'U' => 'unknown'
        ];
        return $genderMap[$gender] ?? 'unknown';
    }

    /**
     * Create FHIR DiagnosticReport for radiology results
     */
    public function createDiagnosticReport($reportData) {
        try {
            $fhirReport = $this->mapToFHIRDiagnosticReport($reportData);

            $response = $this->apiClient->post('/DiagnosticReport', [
                'json' => $fhirReport
            ]);

            $result = json_decode($response->getBody(), true);

            return [
                'success' => true,
                'fhir_id' => $result['id'],
                'resource' => $result
            ];

        } catch (RequestException $e) {
            return [
                'success' => false,
                'error' => 'DiagnosticReport creation failed: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Map radiology report to FHIR DiagnosticReport
     */
    private function mapToFHIRDiagnosticReport($reportData) {
        return [
            'resourceType' => 'DiagnosticReport',
            'status' => 'final',
            'category' => [
                [
                    'coding' => [
                        [
                            'system' => 'http://terminology.hl7.org/CodeSystem/v2-0074',
                            'code' => 'RAD',
                            'display' => 'Radiology'
                        ]
                    ]
                ]
            ],
            'code' => [
                'coding' => [
                    [
                        'system' => 'http://www.radlex.org',
                        'code' => $reportData['procedure_code'],
                        'display' => $reportData['procedure_name']
                    ]
                ]
            ],
            'subject' => [
                'reference' => 'Patient/' . $reportData['patient_fhir_id']
            ],
            'encounter' => [
                'reference' => 'Encounter/' . $reportData['encounter_fhir_id']
            ],
            'effectiveDateTime' => $reportData['study_date'],
            'issued' => $reportData['report_date'],
            'performer' => [
                [
                    'reference' => 'Practitioner/' . $reportData['radiologist_fhir_id']
                ]
            ],
            'result' => [
                [
                    'reference' => 'Observation/' . $reportData['findings_fhir_id']
                ]
            ],
            'conclusion' => $reportData['conclusion'],
            'codedDiagnosis' => array_map(function($icd10) {
                return [
                    'coding' => [
                        [
                            'system' => 'http://hl7.org/fhir/sid/icd-10',
                            'code' => $icd10['code'],
                            'display' => $icd10['description']
                        ]
                    ]
                ];
            }, $reportData['icd10_codes'] ?? [])
        ];
    }

    /**
     * Search FHIR resources with advanced querying
     */
    public function searchResources($resourceType, $searchParams) {
        try {
            $queryString = http_build_query($searchParams);
            $response = $this->apiClient->get("/$resourceType?$queryString");

            return json_decode($response->getBody(), true);

        } catch (RequestException $e) {
            return [
                'success' => false,
                'error' => 'Search failed: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Get resource by ID
     */
    public function getResource($resourceType, $id) {
        try {
            $response = $this->apiClient->get("/$resourceType/$id");
            return json_decode($response->getBody(), true);

        } catch (RequestException $e) {
            return null;
        }
    }

    /**
     * Update FHIR resource
     */
    public function updateResource($resourceType, $id, $resourceData) {
        try {
            $response = $this->apiClient->put("/$resourceType/$id", [
                'json' => $resourceData
            ]);

            return [
                'success' => true,
                'resource' => json_decode($response->getBody(), true)
            ];

        } catch (RequestException $e) {
            return [
                'success' => false,
                'error' => 'Update failed: ' . $e->getMessage()
            ];
        }
    }
}