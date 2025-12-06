<?php

/**
 * FHIR Radiology Service
 *
 * Specialized FHIR service for radiology workflows in South African context
 * Implements FHIR ImagingStudy, DiagnosticReport, and related resources
 *
 * @package SA_RIS_FHIR
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\FHIR;

use Exception;
use PDO;

class FHIRRadiologyService {

    private $fhirConnector;
    private $db;
    private $config;

    public function __construct(PDO $database, FHIRConnector $fhirConnector, array $config = []) {
        $this->db = $database;
        $this->fhirConnector = $fhirConnector;
        $this->config = $config;
    }

    /**
     * Create complete radiology study workflow in FHIR
     */
    public function createRadiologyStudy($studyData) {
        try {
            // 1. Ensure patient exists in FHIR
            $patientFHIR = $this->ensurePatientInFHIR($studyData['patient']);

            // 2. Create encounter if not exists
            $encounterFHIR = $this->ensureEncounterInFHIR($studyData, $patientFHIR['fhir_id']);

            // 3. Create service request
            $serviceRequestFHIR = $this->createServiceRequest($studyData, $patientFHIR['fhir_id'], $encounterFHIR['fhir_id']);

            // 4. Create imaging study
            $imagingStudyFHIR = $this->createImagingStudy($studyData, $patientFHIR['fhir_id'], $encounterFHIR['fhir_id']);

            // 5. Create observations for findings
            $observationsFHIR = $this->createObservations($studyData, $patientFHIR['fhir_id'], $encounterFHIR['fhir_id']);

            // 6. Create diagnostic report
            $reportData = array_merge($studyData, [
                'patient_fhir_id' => $patientFHIR['fhir_id'],
                'encounter_fhir_id' => $encounterFHIR['fhir_id'],
                'findings_fhir_id' => $observationsFHIR[0]['fhir_id'] ?? null,
                'radiologist_fhir_id' => $this->getRadiologistFHIRId($studyData['radiologist_id'])
            ]);

            $diagnosticReportFHIR = $this->fhirConnector->createDiagnosticReport($reportData);

            return [
                'success' => true,
                'patient' => $patientFHIR,
                'encounter' => $encounterFHIR,
                'service_request' => $serviceRequestFHIR,
                'imaging_study' => $imagingStudyFHIR,
                'observations' => $observationsFHIR,
                'diagnostic_report' => $diagnosticReportFHIR
            ];

        } catch (Exception $e) {
            return [
                'success' => false,
                'error' => 'Radiology study creation failed: ' . $e->getMessage()
            ];
        }
    }

    /**
     * Ensure patient exists in FHIR system
     */
    private function ensurePatientInFHIR($patientData) {
        // Check if patient already exists
        $existingPatient = $this->fhirConnector->searchResources('Patient', [
            'identifier' => $patientData['medical_aid_number'] ?? $patientData['id']
        ]);

        if (!empty($existingPatient['entry'])) {
            return [
                'fhir_id' => $existingPatient['entry'][0]['resource']['id'],
                'existing' => true
            ];
        }

        // Create new patient
        return $this->fhirConnector->createPatientResource($patientData);
    }

    /**
     * Ensure encounter exists in FHIR
     */
    private function ensureEncounterInFHIR($studyData, $patientFHIRId) {
        // For radiology, create a new encounter for each study
        return $this->createEncounter($studyData, $patientFHIRId);
    }

    /**
     * Create FHIR Encounter resource
     */
    private function createEncounter($studyData, $patientFHIRId) {
        $encounterResource = [
            'resourceType' => 'Encounter',
            'status' => 'finished',
            'class' => [
                'system' => 'http://terminology.hl7.org/CodeSystem/v3-ActCode',
                'code' => 'AMB',
                'display' => 'ambulatory'
            ],
            'subject' => [
                'reference' => 'Patient/' . $patientFHIRId
            ],
            'period' => [
                'start' => $studyData['study_date'],
                'end' => $studyData['study_date']
            ],
            'serviceType' => [
                'coding' => [
                    [
                        'system' => 'http://www.radlex.org',
                        'code' => $studyData['modality'],
                        'display' => $studyData['procedure_name']
                    ]
                ]
            ],
            'reasonCode' => array_map(function($icd10) {
                return [
                    'coding' => [
                        [
                            'system' => 'http://hl7.org/fhir/sid/icd-10',
                            'code' => $icd10['code'],
                            'display' => $icd10['description']
                        ]
                    ]
                ];
            }, $studyData['indication_icd10'] ?? [])
        ];

        // Use FHIR connector to create encounter
        // Note: This would need to be implemented in FHIRConnector
        return [
            'fhir_id' => 'encounter_' . uniqid(),
            'resource' => $encounterResource
        ];
    }

    /**
     * Create FHIR ServiceRequest
     */
    private function createServiceRequest($studyData, $patientFHIRId, $encounterFHIRId) {
        $serviceRequestResource = [
            'resourceType' => 'ServiceRequest',
            'status' => 'completed',
            'intent' => 'order',
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
                        'code' => $studyData['procedure_code'],
                        'display' => $studyData['procedure_name']
                    ]
                ]
            ],
            'subject' => [
                'reference' => 'Patient/' . $patientFHIRId
            ],
            'encounter' => [
                'reference' => 'Encounter/' . $encounterFHIRId
            ],
            'authoredOn' => $studyData['order_date'],
            'requester' => [
                'reference' => 'Practitioner/' . $this->getRequesterFHIRId($studyData['referring_doctor_id'])
            ],
            'reasonCode' => array_map(function($icd10) {
                return [
                    'coding' => [
                        [
                            'system' => 'http://hl7.org/fhir/sid/icd-10',
                            'code' => $icd10['code'],
                            'display' => $icd10['description']
                        ]
                    ]
                ];
            }, $studyData['clinical_indication'] ?? [])
        ];

        return [
            'fhir_id' => 'servicerequest_' . uniqid(),
            'resource' => $serviceRequestResource
        ];
    }

    /**
     * Create FHIR ImagingStudy
     */
    private function createImagingStudy($studyData, $patientFHIRId, $encounterFHIRId) {
        $imagingStudyResource = [
            'resourceType' => 'ImagingStudy',
            'status' => 'available',
            'subject' => [
                'reference' => 'Patient/' . $patientFHIRId
            ],
            'encounter' => [
                'reference' => 'Encounter/' . $encounterFHIRId
            ],
            'started' => $studyData['study_date'],
            'modality' => [
                [
                    'system' => 'http://dicom.nema.org/resources/ontology/DCM',
                    'code' => $studyData['dicom_modality']
                ]
            ],
            'procedureCode' => [
                [
                    'coding' => [
                        [
                            'system' => 'http://www.radlex.org',
                            'code' => $studyData['procedure_code'],
                            'display' => $studyData['procedure_name']
                        ]
                    ]
                ]
            ],
            'series' => array_map(function($series) {
                return [
                    'uid' => $series['series_uid'],
                    'number' => $series['series_number'],
                    'modality' => [
                        'system' => 'http://dicom.nema.org/resources/ontology/DCM',
                        'code' => $series['modality']
                    ],
                    'description' => $series['description'],
                    'numberOfInstances' => $series['instance_count'],
                    'instance' => array_map(function($instance) {
                        return [
                            'uid' => $instance['sop_uid'],
                            'sopClass' => [
                                'system' => 'urn:ietf:rfc:3986',
                                'code' => $instance['sop_class']
                            ]
                        ];
                    }, $series['instances'] ?? [])
                ];
            }, $studyData['series'] ?? [])
        ];

        return [
            'fhir_id' => 'imagingstudy_' . uniqid(),
            'resource' => $imagingStudyResource
        ];
    }

    /**
     * Create FHIR Observations for findings
     */
    private function createObservations($studyData, $patientFHIRId, $encounterFHIRId) {
        $observations = [];

        if (!empty($studyData['findings'])) {
            foreach ($studyData['findings'] as $finding) {
                $observationResource = [
                    'resourceType' => 'Observation',
                    'status' => 'final',
                    'category' => [
                        [
                            'coding' => [
                                [
                                    'system' => 'http://terminology.hl7.org/CodeSystem/observation-category',
                                    'code' => 'imaging',
                                    'display' => 'Imaging'
                                ]
                            ]
                        ]
                    ],
                    'code' => [
                        'coding' => [
                            [
                                'system' => 'http://www.radlex.org',
                                'code' => $finding['finding_code'],
                                'display' => $finding['finding_description']
                            ]
                        ]
                    ],
                    'subject' => [
                        'reference' => 'Patient/' . $patientFHIRId
                    ],
                    'encounter' => [
                        'reference' => 'Encounter/' . $encounterFHIRId
                    ],
                    'effectiveDateTime' => $studyData['study_date'],
                    'valueString' => $finding['description'],
                    'interpretation' => [
                        [
                            'coding' => [
                                [
                                    'system' => 'http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation',
                                    'code' => $finding['severity'] === 'critical' ? 'H' : 'N'
                                ]
                            ]
                        ]
                    ]
                ];

                $observations[] = [
                    'fhir_id' => 'observation_' . uniqid(),
                    'resource' => $observationResource
                ];
            }
        }

        return $observations;
    }

    /**
     * Get radiologist FHIR ID
     */
    private function getRadiologistFHIRId($radiologistId) {
        // Implementation would query database for FHIR ID
        return 'practitioner_' . $radiologistId;
    }

    /**
     * Get requester FHIR ID
     */
    private function getRequesterFHIRId($doctorId) {
        // Implementation would query database for FHIR ID
        return 'practitioner_' . $doctorId;
    }

    /**
     * Search radiology studies with FHIR
     */
    public function searchRadiologyStudies($searchParams) {
        return $this->fhirConnector->searchResources('ImagingStudy', $searchParams);
    }

    /**
     * Get study with full FHIR bundle
     */
    public function getStudyBundle($studyId) {
        // Implementation would create a FHIR Bundle with all related resources
        return [
            'resourceType' => 'Bundle',
            'type' => 'collection',
            'entry' => []
        ];
    }
}