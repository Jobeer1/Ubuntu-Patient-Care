/**
 * 🇿🇦 South African Medical Imaging System - Localization Hook
 * 
 * Custom hook for South African multi-language support
 * Supports English, Afrikaans, and isiZulu
 */

import React, { useState, useCallback } from 'react';

type Language = 'en' | 'af' | 'zu';

interface Translations {
  [key: string]: {
    [lang in Language]: string;
  };
}

// South African medical imaging translations
const translations: Translations = {
  // UI Elements
  'ui.toggleStudyBrowser': {
    en: 'Toggle Study Browser',
    af: 'Wissel Studie Blaaier',
    zu: 'Guqula Isifundi Sebrowser'
  },
  'ui.toggleToolPanel': {
    en: 'Toggle Tool Panel',
    af: 'Wissel Gereedskap Paneel',
    zu: 'Guqula Iphaneli Yamathuluzi'
  },
  'ui.settings': {
    en: 'Settings',
    af: 'Instellings',
    zu: 'Izilungiselelo'
  },
  'ui.help': {
    en: 'Help',
    af: 'Hulp',
    zu: 'Usizo'
  },
  'ui.windowPresets': {
    en: 'Window Presets',
    af: 'Venster Voorinstellings',
    zu: 'Izilungiselelo Zefasitela'
  },

  // Layout
  'layout.single': {
    en: 'Single View',
    af: 'Enkele Aansig',
    zu: 'Ukubuka Okukodwa'
  },
  'layout.sideBySide': {
    en: 'Side by Side',
    af: 'Kant aan Kant',
    zu: 'Eceleni Kwelinye'
  },
  'layout.grid2x2': {
    en: '2x2 Grid',
    af: '2x2 Rooster',
    zu: 'Igridi ye-2x2'
  },

  // Window Presets (SA Medical Context)
  'presets.chest': {
    en: 'Chest (TB Screening)',
    af: 'Bors (TB Sifting)',
    zu: 'Isifuba (Ukuhlola i-TB)'
  },
  'presets.bone': {
    en: 'Bone (Fractures)',
    af: 'Been (Breuke)',
    zu: 'Ithambo (Ukwephuka)'
  },
  'presets.softTissue': {
    en: 'Soft Tissue',
    af: 'Sagte Weefsel',
    zu: 'Izicubu Ezithambile'
  },
  'presets.lung': {
    en: 'Lung (Respiratory)',
    af: 'Long (Respiratories)',
    zu: 'Amaphaphu (Ukuphefumula)'
  },
  'presets.brain': {
    en: 'Brain (Stroke/Trauma)',
    af: 'Brein (Beroerte/Trauma)',
    zu: 'Ubuchopho (Ukuphazamiseka/Ukulimala)'
  },
  'presets.abdomen': {
    en: 'Abdomen',
    af: 'Buik',
    zu: 'Isisu'
  },

  // Loading Messages
  'loading.studies': {
    en: 'Loading studies...',
    af: 'Laai studies...',
    zu: 'Kulayishwa izifundo...'
  },
  'loading.images': {
    en: 'Loading images...',
    af: 'Laai beelde...',
    zu: 'Kulayishwa izithombe...'
  },
  'loading.processing': {
    en: 'Processing...',
    af: 'Verwerk...',
    zu: 'Kuyacutshungulwa...'
  },

  // Error Messages
  'error.loadStudies': {
    en: 'Failed to load studies',
    af: 'Kon nie studies laai nie',
    zu: 'Kwehlulekile ukulayisha izifundo'
  },
  'error.loadImages': {
    en: 'Failed to load images',
    af: 'Kon nie beelde laai nie',
    zu: 'Kwehlulekile ukulayisha izithombe'
  },
  'error.network': {
    en: 'Network connection error',
    af: 'Netwerk verbinding fout',
    zu: 'Iphutha lokuxhumana kwenethiwekhi'
  },

  // Patient Information
  'patient.name': {
    en: 'Patient Name',
    af: 'Pasiënt Naam',
    zu: 'Igama Lesiguli'
  },
  'patient.id': {
    en: 'Patient ID',
    af: 'Pasiënt ID',
    zu: 'I-ID Yesiguli'
  },
  'patient.age': {
    en: 'Age',
    af: 'Ouderdom',
    zu: 'Iminyaka'
  },
  'patient.sex': {
    en: 'Sex',
    af: 'Geslag',
    zu: 'Ubulili'
  },
  'patient.saId': {
    en: 'SA ID Number',
    af: 'SA ID Nommer',
    zu: 'Inombolo Ye-ID Yase-SA'
  },
  'patient.medicalAid': {
    en: 'Medical Aid',
    af: 'Mediese Fonds',
    zu: 'Usizo Lwezempilo'
  },

  // Study Information
  'study.date': {
    en: 'Study Date',
    af: 'Studie Datum',
    zu: 'Usuku Lwesifundo'
  },
  'study.description': {
    en: 'Description',
    af: 'Beskrywing',
    zu: 'Incazelo'
  },
  'study.modality': {
    en: 'Modality',
    af: 'Modaliteit',
    zu: 'Indlela'
  },
  'study.bodyPart': {
    en: 'Body Part',
    af: 'Liggaamsdeel',
    zu: 'Ingxenye Yomzimba'
  },

  // Tools
  'tools.pan': {
    en: 'Pan',
    af: 'Skuif',
    zu: 'Susa'
  },
  'tools.zoom': {
    en: 'Zoom',
    af: 'Zoem',
    zu: 'Sondeza'
  },
  'tools.windowLevel': {
    en: 'Window/Level',
    af: 'Venster/Vlak',
    zu: 'Ifasitela/Izinga'
  },
  'tools.measure': {
    en: 'Measure',
    af: 'Meet',
    zu: 'Kala'
  },
  'tools.annotate': {
    en: 'Annotate',
    af: 'Annoteer',
    zu: 'Chaza'
  },
  'tools.reset': {
    en: 'Reset',
    af: 'Herstel',
    zu: 'Setha Kabusha'
  },

  // Measurements
  'measurement.length': {
    en: 'Length',
    af: 'Lengte',
    zu: 'Ubude'
  },
  'measurement.area': {
    en: 'Area',
    af: 'Area',
    zu: 'Indawo'
  },
  'measurement.angle': {
    en: 'Angle',
    af: 'Hoek',
    zu: 'I-engeli'
  },
  'measurement.volume': {
    en: 'Volume',
    af: 'Volume',
    zu: 'Ivolumu'
  },

  // Medical Conditions (SA Context)
  'condition.tuberculosis': {
    en: 'Tuberculosis (TB)',
    af: 'Tuberkulose (TB)',
    zu: 'Isifo Sefuba (TB)'
  },
  'condition.fracture': {
    en: 'Fracture',
    af: 'Breuk',
    zu: 'Ukwephuka'
  },
  'condition.pneumonia': {
    en: 'Pneumonia',
    af: 'Longontsteking',
    zu: 'Inyumoniya'
  },
  'condition.stroke': {
    en: 'Stroke',
    af: 'Beroerte',
    zu: 'Ukuphazamiseka Komzimba'
  },

  // Status Messages
  'status.ready': {
    en: 'Ready',
    af: 'Gereed',
    zu: 'Kulungile'
  },
  'status.loading': {
    en: 'Loading',
    af: 'Laai',
    zu: 'Kuyalayishwa'
  },
  'status.error': {
    en: 'Error',
    af: 'Fout',
    zu: 'Iphutha'
  },
  'status.connected': {
    en: 'Connected',
    af: 'Verbind',
    zu: 'Kuxhunyiwe'
  },
  'status.disconnected': {
    en: 'Disconnected',
    af: 'Ontkoppel',
    zu: 'Akuxhunyiwe'
  },

  // Additional UI Elements
  'ui.studyBrowser': {
    en: 'Study Browser',
    af: 'Studie Blaaier',
    zu: 'Isifundi Sebrowser'
  },
  'ui.studies': {
    en: 'studies',
    af: 'studies',
    zu: 'izifundo'
  },
  'ui.noStudies': {
    en: 'No studies available',
    af: 'Geen studies beskikbaar nie',
    zu: 'Azikho izifundo ezitholakalayo'
  },
  'ui.images': {
    en: 'images',
    af: 'beelde',
    zu: 'izithombe'
  },
  'ui.selectStudy': {
    en: 'Select a study to view images',
    af: 'Kies \'n studie om beelde te sien',
    zu: 'Khetha isifundo ukuze ubone izithombe'
  },
  'ui.retry': {
    en: 'Retry',
    af: 'Probeer weer',
    zu: 'Zama futhi'
  },
  'ui.basicTools': {
    en: 'Basic Tools',
    af: 'Basiese Gereedskap',
    zu: 'Amathuluzi Ayisisekelo'
  },
  'ui.saPresets': {
    en: 'SA Medical Presets',
    af: 'SA Mediese Voorinstellings',
    zu: 'Izilungiselelo Zezempilo Zase-SA'
  },
  'ui.actions': {
    en: 'Actions',
    af: 'Aksies',
    zu: 'Izenzo'
  },
  'ui.export': {
    en: 'Export',
    af: 'Uitvoer',
    zu: 'Thumela'
  },
  'ui.measurements': {
    en: 'Measurements',
    af: 'Metings',
    zu: 'Izilinganiso'
  },
  'ui.clearAll': {
    en: 'Clear All',
    af: 'Maak Alles Skoon',
    zu: 'Sula Konke'
  },
  'ui.noMeasurements': {
    en: 'No measurements taken',
    af: 'Geen metings geneem nie',
    zu: 'Azikho izilinganiso ezithathiwe'
  },
  'ui.aiDiagnosis': {
    en: 'AI Diagnosis',
    af: 'KI Diagnose',
    zu: 'Ukuxilonga Kwe-AI'
  },
  'ui.analyze': {
    en: 'Analyze',
    af: 'Ontleed',
    zu: 'Hlaziya'
  },
  'ui.saConditions': {
    en: 'SA Medical Conditions',
    af: 'SA Mediese Toestande',
    zu: 'Izimo Zezempilo Zase-SA'
  },
  'ui.aiResults': {
    en: 'AI Results',
    af: 'KI Resultate',
    zu: 'Imiphumela Ye-AI'
  },
  'ui.noAiResults': {
    en: 'No AI analysis results',
    af: 'Geen KI ontleding resultate nie',
    zu: 'Azikho imiphumela yokuhlaziya kwe-AI'
  },
  'ui.voiceDictation': {
    en: 'Voice Dictation',
    af: 'Stem Diktaat',
    zu: 'Ukushaya Ngezwi'
  },
  'ui.record': {
    en: 'Record',
    af: 'Neem op',
    zu: 'Rekhoda'
  },
  'ui.language': {
    en: 'Language',
    af: 'Taal',
    zu: 'Ulimi'
  },
  'ui.transcript': {
    en: 'Transcript',
    af: 'Transkripsie',
    zu: 'Umbhalo'
  },
  'ui.noTranscript': {
    en: 'No voice recording available',
    af: 'Geen stem opname beskikbaar nie',
    zu: 'Akukho ukurekhoda kwezwi okutholakalayo'
  },
  'ui.tools': {
    en: 'Tools',
    af: 'Gereedskap',
    zu: 'Amathuluzi'
  },
  'ui.voice': {
    en: 'Voice',
    af: 'Stem',
    zu: 'Izwi'
  }
};

export const useSALocalization = () => {
  const [currentLanguage, setCurrentLanguage] = useState<Language>('en');

  const t = useCallback((key: string): string => {
    const translation = translations[key];
    if (!translation) {
      console.warn(`Translation missing for key: ${key}`);
      return key;
    }
    return translation[currentLanguage] || translation.en || key;
  }, [currentLanguage]);

  const setLanguage = useCallback((language: Language) => {
    setCurrentLanguage(language);
    // Store preference in localStorage
    localStorage.setItem('sa-dicom-viewer-language', language);
  }, []);

  // Load saved language preference on mount
  React.useEffect(() => {
    const savedLanguage = localStorage.getItem('sa-dicom-viewer-language') as Language;
    if (savedLanguage && ['en', 'af', 'zu'].includes(savedLanguage)) {
      setCurrentLanguage(savedLanguage);
    }
  }, []);

  return {
    t,
    currentLanguage,
    setLanguage,
    availableLanguages: [
      { code: 'en', name: 'English', flag: '🇬🇧' },
      { code: 'af', name: 'Afrikaans', flag: '🇿🇦' },
      { code: 'zu', name: 'isiZulu', flag: '🇿🇦' }
    ] as const
  };
};