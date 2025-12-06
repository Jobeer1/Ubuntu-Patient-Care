<?php

/**
 * FHIR Radiology Service for SA-RIS
 *
 * Implements HL7 FHIR v4.0+ standards for radiology workflows
 * Integrates with DICOM studies and Orthanc PACS
 *
 * @package SA_RIS_FHIR
 * @author Ubuntu Patient Sorg Team
 * @copyright 2025
 */

namespace SA_RIS\FHIR;

use Exception;
use PDO;
use GuzzleHttp\Client;
use Monolog\Logger;
use Monolog\Handler\StreamHandler;

class FHIRRadiologyService {

    private $fhirClient;
    private $db;
    private $orthancConnector;
    private $config;
    private $logger;

    public function __construct(PDO $database, $orthancConnector, array $config = []) {
        $this->db = $database;
        $this->orthancConnector = $orthancConnector;
        $this->config = array_merge([
            'fhir_base_url' => 'https://fhir.sacoronavirus.co.za/r4',
            'fhir_timeout' => 30,
            'fhir_verify_ssl' => true
        ], $config);

        $this->initializeFHIRClient();
        $this->initializeLogger();
    }

    private function initializeFHIRClient() {
        $this->fhirClient = new Client([
            'base_uri' => $this->config['fhir_base_url'],
            'timeout' => $this->config['fhir_timeout'],
            'verify' => $this->config['fhir_verify_ssl'],
            'headers' => [
                'Content-Type' => 'application/fhir+json',
                'Accept' => 'application/fhir+json',
                'User-Agent' => 'SA-RIS-FHIR-Service/1.0'
            ]
        ]);
    }

    private function initializeLogger() {
        $this->logger = new Logger('fhir-radiology');
        $this->logger->pushHandler(new StreamHandler('/var/log/fhir/radiology.log'));
    }

    /**
     * Create FHIR ImagingStudy from DICOM study
     */
    public function createImagingStudy($studyId, $patientId) {
        try {
            // Get DICOM study from Orthanc
            $dicomStudy = $this->orthancConnector->getStudy($studyId);
            if (!$dicomStudy) {
                throw new Exception("DICOM study not found: $studyId");
            }

            // Get patient FHIR resource
            $patientResource = $this->getPatientResource($patientId);
            if (!$patientResource) {
                throw new Exception("Patient FHIR resource not found: $patientId");
            }

            // Create ImagingStudy resource
            $imagingStudy = [
                'resourceType' => 'ImagingStudy',
                'id' => 'imaging-study-' . $studyId,
                'status' => 'available',
                'subject' => [
                    'reference' => 'Patient/' . $patientResource['id']
                ],
                'started' => $dicomStudy['MainDicomTags']['StudyDate'] . 'T' . $dicomStudy['MainDicomTags']['StudyTime'],
                'numberOfSeries' => count($dicomStudy['Series']),
                'numberOfInstances' => $this->calculateTotalInstances($dicomStudy),
                'description' => $dicomStudy['MainDicomTags']['StudyDescription'] ?? 'Radiology Study',
                'series' => $this->createSeriesResources($dicomStudy['Series']),
                'identifier' => [
                    [
                        'system' => 'urn:dicom:uid',
                        'value' => $dicomStudy['MainDicomTags']['StudyInstanceUID']
                    ]
                ]
            ];

            // Store in FHIR server
            $response = $this->fhirClient->post('/ImagingStudy', [
                'json' => $imagingStudy
            ]);

            if ($response->getStatusCode() === 201) {
                $location = $response->getHeader('Location')[0];
                $fhirId = basename($location);

                // Store mapping in local database
                $this->storeFHIRMapping($studyId, $fhirId, 'ImagingStudy');

                $this->logger->info("Created FHIR ImagingStudy", [
                    'studyId' => $studyId,
                    'fhirId' => $fhirId
                ]);

                return $fhirId;
            }

        } catch (Exception $e) {
            $this->logger->error("Failed to create ImagingStudy", [
                'studyId' => $studyId,
                'error' => $e->getMessage()
            ]);
            throw $e;
        }
    }

    /**
     * Get patient FHIR resource
     */
    private function getPatientResource($patientId) {
        try {
            $response = $this->fhirClient->get("/Patient/$patientId");
            if ($response->getStatusCode() === 200) {
                return json_decode($response->getBody(), true);
            }
        } catch (Exception $e) {
            $this->logger->warning("Patient FHIR resource not found", [
                'patientId' => $patientId,
                'error' => $e->getMessage()
            ]);
        }
        return null;
    }

    /**
     * Create series resources for ImagingStudy
     */
    private function createSeriesResources($series) {
        $seriesResources = [];

        foreach ($series as $seriesData) {
            $seriesResources[] = [
                'uid' => $seriesData['MainDicomTags']['SeriesInstanceUID'],
                'number' => intval($seriesData['MainDicomTags']['SeriesNumber'] ?? 1),
                'modality' => [
                    'system' => 'http://dicom.nema.org/resources/ontology/DCM',
                    'code' => $seriesData['MainDicomTags']['Modality']
                ],
                'description' => $seriesData['MainDicomTags']['SeriesDescription'] ?? '',
                'numberOfInstances' => count($seriesData['Instances'] ?? []),
                'bodySite' => $this->mapBodySite($seriesData['MainDicomTags']),
                'instance' => $this->createInstanceResources($seriesData['Instances'] ?? [])
            ];
        }

        return $seriesResources;
    }

    /**
     * Create instance resources
     */
    private function createInstanceResources($instances) {
        $instanceResources = [];

        foreach ($instances as $instance) {
            $instanceResources[] = [
                'uid' => $instance['MainDicomTags']['SOPInstanceUID'],
                'number' => intval($instance['MainDicomTags']['InstanceNumber'] ?? 1),
                'title' => 'Instance ' . ($instance['MainDicomTags']['InstanceNumber'] ?? '1')
            ];
        }

        return $instanceResources;
    }

    /**
     * Map DICOM body site to FHIR
     */
    private function mapBodySite($dicomTags) {
        $bodyPart = $dicomTags['BodyPartExamined'] ?? '';

        $bodySiteMap = [
            'HEAD' => ['system' => 'http://snomed.info/sct', 'code' => '69536005', 'display' => 'Head'],
            'CHEST' => ['system' => 'http://snomed.info/sct', 'code' => '43799004', 'display' => 'Chest'],
            'ABDOMEN' => ['system' => 'http://snomed.info/sct', 'code' => '818981001', 'display' => 'Abdomen'],
            'PELVIS' => ['system' => 'http://snomed.info/sct', 'code' => '816092008', 'display' => 'Pelvis'],
            'EXTREMITY' => ['system' => 'http://snomed.info/sct', 'code' => '129154003', 'display' => 'Extremity']
        ];

        return $bodySiteMap[$bodyPart] ?? null;
    }

    /**
     * Calculate total instances in study
     */
    private function calculateTotalInstances($study) {
        $total = 0;
        foreach ($study['Series'] as $series) {
            $total += count($series['Instances'] ?? []);
        }
        return $total;
    }

    /**
     * Store FHIR resource mapping
     */
    private function storeFHIRMapping($localId, $fhirId, $resourceType) {
        $stmt = $this->db->prepare("
            INSERT INTO fhir_mappings (local_id, fhir_id, resource_type, created_at)
            VALUES (?, ?, ?, NOW())
            ON DUPLICATE KEY UPDATE fhir_id = VALUES(fhir_id)
        ");
        $stmt->execute([$localId, $fhirId, $resourceType]);
    }

    /**
     * Get FHIR resource by local ID
     */
    public function getFHIRResource($localId, $resourceType) {
        $stmt = $this->db->prepare("
            SELECT fhir_id FROM fhir_mappings
            WHERE local_id = ? AND resource_type = ?
        ");
        $stmt->execute([$localId, $resourceType]);
        $result = $stmt->fetch(PDO::FETCH_ASSOC);

        if ($result) {
            try {
                $response = $this->fhirClient->get("/$resourceType/" . $result['fhir_id']);
                if ($response->getStatusCode() === 200) {
                    return json_decode($response->getBody(), true);
                }
            } catch (Exception $e) {
                $this->logger->error("Failed to retrieve FHIR resource", [
                    'localId' => $localId,
                    'resourceType' => $resourceType,
                    'error' => $e->getMessage()
                ]);
            }
        }

        return null;
    }

    /**
     * Ensure patient exists in FHIR server
     */
    public function ensurePatientInFHIR($patientData) {
        try {
            // Check if patient already exists
            $existingPatient = $this->findPatientByIdentifier($patientData['id_number']);

            if ($existingPatient) {
                return $existingPatient['id'];
            }

            // Create new patient resource
            $patientResource = [
                'resourceType' => 'Patient',
                'identifier' => [
                    [
                        'system' => 'http://sa.gov.za/id',
                        'value' => $patientData['id_number']
                    ]
                ],
                'name' => [
                    [
                        'family' => $patientData['surname'],
                        'given' => [$patientData['first_name']],
                        'text' => $patientData['first_name'] . ' ' . $patientData['surname']
                    ]
                ],
                'gender' => strtolower($patientData['gender']),
                'birthDate' => $patientData['date_of_birth'],
                'address' => [
                    [
                        'country' => 'ZA',
                        'state' => $patientData['province'] ?? '',
                        'city' => $patientData['city'] ?? ''
                    ]
                ]
            ];

            $response = $this->fhirClient->post('/Patient', [
                'json' => $patientResource
            ]);

            if ($response->getStatusCode() === 201) {
                $location = $response->getHeader('Location')[0];
                $fhirId = basename($location);

                // Store mapping
                $this->storeFHIRMapping($patientData['id'], $fhirId, 'Patient');

                $this->logger->info("Created FHIR Patient", [
                    'patientId' => $patientData['id'],
                    'fhirId' => $fhirId
                ]);

                return $fhirId;
            }

        } catch (Exception $e) {
            $this->logger->error("Failed to create FHIR Patient", [
                'patientId' => $patientData['id'],
                'error' => $e->getMessage()
            ]);
            throw $e;
        }
    }

    /**
     * Find patient by identifier
     */
    private function findPatientByIdentifier($identifier) {
        try {
            $response = $this->fhirClient->get("/Patient?identifier=http://sa.gov.za/id|$identifier");
            if ($response->getStatusCode() === 200) {
                $bundle = json_decode($response->getBody(), true);
                if (isset($bundle['entry']) && count($bundle['entry']) > 0) {
                    return $bundle['entry'][0]['resource'];
                }
            }
        } catch (Exception $e) {
            // Patient not found
        }
        return null;
    }
}