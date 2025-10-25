/**
 * OHIF Configuration for South African Medical Imaging
 * Optimized for referring doctors and SA healthcare workflows
 */

export const createSAOHIFConfig = (options = {}) => {
    const {
        isReferringDoctor = false,
        isLowBandwidth = false,
        isMobile = false,
        language = 'en-ZA'
    } = options;

    return {
        routerBasename: '/sa-viewer',
        
        // SA-specific branding
        whiteLabeling: {
            createLogoComponentFn: () => {
                return React.createElement('div', {
                    className: 'sa-medical-logo',
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        color: '#007749', // SA Green
                        fontWeight: 'bold'
                    }
                }, [
                    React.createElement('span', { key: 'flag' }, '🇿🇦'),
                    React.createElement('span', { key: 'text' }, 'SA Medical Imaging')
                ]);
            }
        },

        // Performance optimizations for SA networks
        maxNumberOfWebWorkers: isLowBandwidth ? 2 : 4,
        maxCacheSize: isLowBandwidth ? '100MB' : '500MB',
        
        // Simplified UI for referring doctors
        showStudyList: !isReferringDoctor,
        showHeader: true,
        showLoadingIndicator: true,
        showWarningMessageForCrossOrigin: false,
        showCPUFallbackMessage: false,

        // Default viewport settings
        defaultViewportOptions: {
            viewportType: 'stack',
            toolGroupId: isReferringDoctor ? 'referring-doctor-tools' : 'default-tools',
            initialImageOptions: {
                preset: 'first',
                // SA medical standards
                interpolationType: 'LINEAR',
                decimate: isLowBandwidth ? 2 : 1
            }
        },

        // Cornerstone extension configuration
        cornerstoneExtensionConfig: {
            tools: {
                // Essential tools for referring doctors
                enabled: isReferringDoctor ? [
                    'WindowLevel',
                    'Pan',
                    'Zoom',
                    'StackScrollMouseWheel',
                    'Magnify',
                    'Length',
                    'Angle',
                    'Rectangle',
                    'Probe'
                ] : [
                    // Full tool set for radiologists
                    'WindowLevel',
                    'Pan',
                    'Zoom',
                    'StackScrollMouseWheel',
                    'Magnify',
                    'Length',
                    'Angle',
                    'Rectangle',
                    'Ellipse',
                    'Circle',
                    'Bidirectional',
                    'FreehandRoi',
                    'Crosshairs',
                    'ReferenceLines',
                    'Probe',
                    'CalibrationLine'
                ],
                
                // Disabled tools for simplified interface
                disabled: isReferringDoctor ? [
                    'Crosshairs',
                    'ReferenceLines',
                    'SegmentationDisplay',
                    'Brush',
                    'Scissors',
                    'ThresholdTool'
                ] : []
            },

            // SA-specific presets
            windowLevelPresets: {
                'CT': {
                    'Soft Tissue': { windowWidth: 400, windowCenter: 40 },
                    'Lung': { windowWidth: 1500, windowCenter: -600 },
                    'Bone': { windowWidth: 1800, windowCenter: 400 },
                    'Brain': { windowWidth: 80, windowCenter: 40 },
                    'Abdomen': { windowWidth: 350, windowCenter: 50 }
                },
                'MR': {
                    'Default': { windowWidth: 200, windowCenter: 100 },
                    'T1': { windowWidth: 250, windowCenter: 125 },
                    'T2': { windowWidth: 300, windowCenter: 150 }
                },
                'US': {
                    'Default': { windowWidth: 255, windowCenter: 128 }
                }
            }
        },

        // Internationalization for SA
        i18n: {
            lng: language,
            fallbackLng: 'en',
            debug: false,
            resources: {
                'en-ZA': {
                    translation: {
                        // Patient information
                        'Patient Name': 'Patient Name',
                        'Patient ID': 'Patient ID',
                        'Study Date': 'Study Date',
                        'Study Time': 'Study Time',
                        'Modality': 'Modality',
                        'Series Description': 'Series Description',
                        'Referring Physician': 'Referring Physician',
                        'Institution': 'Institution',
                        
                        // Tools
                        'Window Level': 'Window/Level',
                        'Pan': 'Pan',
                        'Zoom': 'Zoom',
                        'Length': 'Distance',
                        'Angle': 'Angle',
                        'Rectangle': 'Rectangle',
                        'Magnify': 'Magnify',
                        
                        // Actions
                        'Reset': 'Reset',
                        'Invert': 'Invert',
                        'Rotate Right': 'Rotate Right',
                        'Rotate Left': 'Rotate Left',
                        'Flip Horizontal': 'Flip Horizontal',
                        'Flip Vertical': 'Flip Vertical',
                        
                        // SA-specific terms
                        'Medical Aid': 'Medical Aid',
                        'Practice Number': 'Practice Number',
                        'HPCSA Number': 'HPCSA Number',
                        'Referring Doctor': 'Referring Doctor',
                        'Radiologist': 'Radiologist'
                    }
                },
                'af': {
                    translation: {
                        'Patient Name': 'Pasiënt Naam',
                        'Patient ID': 'Pasiënt ID',
                        'Study Date': 'Studie Datum',
                        'Modality': 'Modaliteit',
                        'Referring Physician': 'Verwysende Dokter'
                    }
                }
            }
        },

        // Mobile-specific configurations
        ...(isMobile && {
            viewport: {
                interactionType: 'touch',
                gestureSettings: {
                    pinchToZoom: true,
                    panGesture: true,
                    doubleTapZoom: true,
                    longPressDelay: 500
                }
            },
            
            // Mobile toolbar configuration
            toolbarButtons: {
                primary: ['WindowLevel', 'Pan', 'Zoom', 'Length'],
                secondary: ['Angle', 'Rectangle', 'Reset']
            }
        }),

        // Extensions configuration
        extensions: [
            '@ohif/extension-default',
            '@ohif/extension-cornerstone',
            '@ohif/extension-measurement-tracking',
            '@ohif/extension-cornerstone-dicom-sr',
            '@ohif/extension-cornerstone-dicom-seg'
        ],

        // Modes configuration
        modes: [
            '@ohif/mode-longitudinal',
            '@ohif/mode-basic-dev-mode'
        ],

        // Hanging protocols for SA medical workflows
        hangingProtocols: [
            {
                id: 'sa-chest-xray',
                name: 'SA Chest X-Ray',
                protocolMatchingRules: [
                    {
                        attribute: 'Modality',
                        constraint: {
                            equals: 'CR'
                        }
                    },
                    {
                        attribute: 'BodyPartExamined',
                        constraint: {
                            contains: 'CHEST'
                        }
                    }
                ],
                stages: [
                    {
                        name: 'Chest X-Ray Review',
                        viewportStructure: {
                            layoutType: 'grid',
                            properties: {
                                rows: 1,
                                columns: 1
                            }
                        },
                        viewports: [
                            {
                                viewportOptions: {
                                    toolGroupId: 'chest-xray-tools',
                                    initialImageOptions: {
                                        preset: 'first'
                                    }
                                }
                            }
                        ]
                    }
                ]
            },
            
            {
                id: 'sa-ct-comparison',
                name: 'SA CT Comparison',
                protocolMatchingRules: [
                    {
                        attribute: 'Modality',
                        constraint: {
                            equals: 'CT'
                        }
                    }
                ],
                stages: [
                    {
                        name: 'CT Comparison',
                        viewportStructure: {
                            layoutType: 'grid',
                            properties: {
                                rows: 1,
                                columns: 2
                            }
                        },
                        viewports: [
                            {
                                viewportOptions: {
                                    toolGroupId: 'ct-comparison-tools'
                                }
                            },
                            {
                                viewportOptions: {
                                    toolGroupId: 'ct-comparison-tools'
                                }
                            }
                        ]
                    }
                ]
            }
        ],

        // Custom context menu for SA workflows
        customizationService: {
            contextMenuItems: [
                {
                    id: 'sa-copy-measurements',
                    label: 'Copy Measurements',
                    action: 'copyMeasurements'
                },
                {
                    id: 'sa-export-image',
                    label: 'Export Image',
                    action: 'exportImage'
                },
                {
                    id: 'sa-print-image',
                    label: 'Print Image',
                    action: 'printImage'
                },
                {
                    id: 'sa-share-with-patient',
                    label: 'Share with Patient',
                    action: 'shareWithPatient',
                    condition: isReferringDoctor
                }
            ]
        },

        // Hotkeys optimized for SA medical workflows
        hotkeys: [
            {
                commandName: 'setToolActive',
                commandOptions: { toolName: 'WindowLevel' },
                keys: ['w']
            },
            {
                commandName: 'setToolActive',
                commandOptions: { toolName: 'Pan' },
                keys: ['p']
            },
            {
                commandName: 'setToolActive',
                commandOptions: { toolName: 'Zoom' },
                keys: ['z']
            },
            {
                commandName: 'setToolActive',
                commandOptions: { toolName: 'Length' },
                keys: ['l']
            },
            {
                commandName: 'resetViewport',
                keys: ['r']
            },
            {
                commandName: 'invertViewport',
                keys: ['i']
            },
            // SA-specific hotkeys
            {
                commandName: 'applyPreset',
                commandOptions: { preset: 'Soft Tissue' },
                keys: ['1']
            },
            {
                commandName: 'applyPreset',
                commandOptions: { preset: 'Lung' },
                keys: ['2']
            },
            {
                commandName: 'applyPreset',
                commandOptions: { preset: 'Bone' },
                keys: ['3']
            }
        ],

        // Study prefetching for SA network conditions
        studyPrefetchingRules: {
            enabled: !isLowBandwidth,
            maxConcurrentRequests: isLowBandwidth ? 2 : 6,
            preserveExistingPool: true,
            prefetchDisplaySetsTimeout: isLowBandwidth ? 300 : 200
        },

        // Image loading optimizations
        imageLoadingSettings: {
            maxConcurrentRequests: isLowBandwidth ? 3 : 8,
            requestTimeout: isLowBandwidth ? 30000 : 15000,
            enableWebWorkers: true,
            webWorkerTaskType: 'decode',
            decodeConfig: {
                convertTosRGB: false,
                targetBuffer: {
                    type: isLowBandwidth ? 'Uint8Array' : 'Float32Array'
                }
            }
        }
    };
};

// SA-specific OHIF plugins
export const saOHIFPlugins = [
    {
        name: 'sa-medical-standards',
        version: '1.0.0',
        description: 'South African medical imaging standards and compliance',
        
        // HPCSA compliance features
        hpcsaCompliance: {
            auditLogging: true,
            patientPrivacy: true,
            dataRetention: true,
            accessControl: true
        },
        
        // POPIA compliance
        popiaCompliance: {
            dataProtection: true,
            consentManagement: true,
            dataMinimization: true,
            rightToErasure: true
        }
    },
    
    {
        name: 'sa-network-optimization',
        version: '1.0.0',
        description: 'Network optimizations for South African internet conditions',
        
        features: {
            adaptiveQuality: true,
            progressiveLoading: true,
            offlineCaching: true,
            compressionOptimization: true
        }
    },
    
    {
        name: 'sa-referring-doctor-tools',
        version: '1.0.0',
        description: 'Specialized tools for referring doctors',
        
        tools: [
            'simplified-measurements',
            'patient-communication',
            'report-integration',
            'mobile-optimization'
        ]
    }
];

export default createSAOHIFConfig;