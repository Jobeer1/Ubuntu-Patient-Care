/**
 * 🇿🇦 SA Multi-Language Plugin for OHIF
 * 
 * Provides multi-language support for English, Afrikaans, and isiZulu
 */

const SA_LANGUAGE_PLUGIN = {
  id: '@sa-medical/extension-multi-language',
  version: '1.0.0',

  /**
   * Language Translations
   */
  translations: {
    en: {
      // Common UI Elements
      'common.loading': 'Loading...',
      'common.error': 'Error',
      'common.warning': 'Warning',
      'common.success': 'Success',
      'common.cancel': 'Cancel',
      'common.save': 'Save',
      'common.delete': 'Delete',
      'common.edit': 'Edit',
      'common.view': 'View',
      'common.close': 'Close',
      'common.next': 'Next',
      'common.previous': 'Previous',

      // Medical Viewer
      'viewer.title': 'DICOM Medical Viewer',
      'viewer.patient': 'Patient',
      'viewer.study': 'Study',
      'viewer.series': 'Series',
      'viewer.image': 'Image',
      'viewer.zoom': 'Zoom',
      'viewer.pan': 'Pan',
      'viewer.windowLevel': 'Window/Level',
      'viewer.measure': 'Measure',
      'viewer.annotate': 'Annotate',
      'viewer.reset': 'Reset',
      'viewer.fullscreen': 'Fullscreen',

      // Patient Information
      'patient.id': 'Patient ID',
      'patient.name': 'Patient Name',
      'patient.birthDate': 'Date of Birth',
      'patient.sex': 'Sex',
      'patient.age': 'Age',
      'patient.male': 'Male',
      'patient.female': 'Female',

      // Study Information
      'study.date': 'Study Date',
      'study.time': 'Study Time',
      'study.description': 'Study Description',
      'study.modality': 'Modality',
      'study.referringPhysician': 'Referring Physician',
      'study.accessionNumber': 'Accession Number',

      // HPCSA Compliance
      'hpcsa.title': 'HPCSA Compliance',
      'hpcsa.verification': 'HPCSA Number Verification',
      'hpcsa.number': 'HPCSA Registration Number',
      'hpcsa.verified': 'Verified Healthcare Professional',
      'hpcsa.sessionTimeout': 'Session will expire in',
      'hpcsa.sessionExpired': 'Session has expired for security',
      'hpcsa.auditLog': 'Access logged for HPCSA compliance',

      // POPIA Compliance
      'popia.title': 'POPIA Data Protection',
      'popia.consentRequired': 'Patient consent required for viewing',
      'popia.consentConfirm': 'I confirm proper consent has been obtained',
      'popia.dataMinimization': 'Data minimization applied',
      'popia.anonymized': 'Patient data anonymized for privacy',

      // Network & Mobile
      'network.quality': 'Image Quality',
      'network.lowQuality': 'Low Quality (3G Friendly)',
      'network.mediumQuality': 'Medium Quality (4G)',
      'network.highQuality': 'High Quality (WiFi)',
      'network.slowConnection': 'Slow connection detected',
      'network.offlineMode': 'Offline Mode - Limited functionality',
      'mobile.touchGestures': 'Touch gestures enabled',
      'mobile.pinchZoom': 'Pinch to zoom',
      'mobile.doubleTapFit': 'Double-tap to fit',

      // Errors and Warnings
      'error.loadingStudy': 'Error loading study',
      'error.networkTimeout': 'Network timeout',
      'error.unauthorized': 'Unauthorized access',
      'error.invalidHPCSA': 'Invalid HPCSA number',
      'warning.lowBandwidth': 'Low bandwidth detected - quality reduced',
      'warning.unsavedChanges': 'You have unsaved changes'
    },

    af: {
      // Common UI Elements
      'common.loading': 'Laai...',
      'common.error': 'Fout',
      'common.warning': 'Waarskuwing',
      'common.success': 'Sukses',
      'common.cancel': 'Kanselleer',
      'common.save': 'Stoor',
      'common.delete': 'Verwyder',
      'common.edit': 'Wysig',
      'common.view': 'Bekyk',
      'common.close': 'Sluit',
      'common.next': 'Volgende',
      'common.previous': 'Vorige',

      // Medical Viewer
      'viewer.title': 'DICOM Mediese Kyker',
      'viewer.patient': 'Pasiënt',
      'viewer.study': 'Studie',
      'viewer.series': 'Reeks',
      'viewer.image': 'Beeld',
      'viewer.zoom': 'Zoom',
      'viewer.pan': 'Pan',
      'viewer.windowLevel': 'Venster/Vlak',
      'viewer.measure': 'Meet',
      'viewer.annotate': 'Annoteer',
      'viewer.reset': 'Herstel',
      'viewer.fullscreen': 'Volskerm',

      // Patient Information
      'patient.id': 'Pasiënt ID',
      'patient.name': 'Pasiënt Naam',
      'patient.birthDate': 'Geboortedatum',
      'patient.sex': 'Geslag',
      'patient.age': 'Ouderdom',
      'patient.male': 'Manlik',
      'patient.female': 'Vroulik',

      // Study Information
      'study.date': 'Studie Datum',
      'study.time': 'Studie Tyd',
      'study.description': 'Studie Beskrywing',
      'study.modality': 'Modaliteit',
      'study.referringPhysician': 'Verwysende Dokter',
      'study.accessionNumber': 'Toegangsnommer',

      // HPCSA Compliance
      'hpcsa.title': 'HPCSA Nakoming',
      'hpcsa.verification': 'HPCSA Nommer Verifikasie',
      'hpcsa.number': 'HPCSA Registrasie Nommer',
      'hpcsa.verified': 'Geverifieerde Gesondheidswerker',
      'hpcsa.sessionTimeout': 'Sessie verval oor',
      'hpcsa.sessionExpired': 'Sessie het verval vir sekuriteit',
      'hpcsa.auditLog': 'Toegang geloggeer vir HPCSA nakoming',

      // POPIA Compliance
      'popia.title': 'POPIA Data Beskerming',
      'popia.consentRequired': 'Pasiënt toestemming vereis vir kyking',
      'popia.consentConfirm': 'Ek bevestig toepaslike toestemming is verkry',
      'popia.dataMinimization': 'Data minimalisering toegepas',
      'popia.anonymized': 'Pasiënt data geanonimiseer vir privaatheid',

      // Network & Mobile
      'network.quality': 'Beeld Kwaliteit',
      'network.lowQuality': 'Lae Kwaliteit (3G Vriendelik)',
      'network.mediumQuality': 'Medium Kwaliteit (4G)',
      'network.highQuality': 'Hoë Kwaliteit (WiFi)',
      'network.slowConnection': 'Stadige verbinding opgespoor',
      'network.offlineMode': 'Aflyn Modus - Beperkte funksionaliteit',
      'mobile.touchGestures': 'Raak gebare geaktiveer',
      'mobile.pinchZoom': 'Knyp om te zoom',
      'mobile.doubleTapFit': 'Dubbel-tik om te pas',

      // Errors and Warnings
      'error.loadingStudy': 'Fout met laai van studie',
      'error.networkTimeout': 'Netwerk tyduit',
      'error.unauthorized': 'Ongemagtigde toegang',
      'error.invalidHPCSA': 'Ongeldige HPCSA nommer',
      'warning.lowBandwidth': 'Lae bandwydte opgespoor - kwaliteit verminder',
      'warning.unsavedChanges': 'Jy het ongestoorde veranderinge'
    },

    zu: {
      // Common UI Elements
      'common.loading': 'Iyalayisha...',
      'common.error': 'Iphutha',
      'common.warning': 'Isexwayiso',
      'common.success': 'Impumelelo',
      'common.cancel': 'Khansela',
      'common.save': 'Londoloza',
      'common.delete': 'Susa',
      'common.edit': 'Hlela',
      'common.view': 'Buka',
      'common.close': 'Vala',
      'common.next': 'Okulandelayo',
      'common.previous': 'Okwangaphambili',

      // Medical Viewer
      'viewer.title': 'DICOM Isibuki Sezokwelapha',
      'viewer.patient': 'Isigulane',
      'viewer.study': 'Isifundo',
      'viewer.series': 'Uchungechunge',
      'viewer.image': 'Isithombe',
      'viewer.zoom': 'Khulisa',
      'viewer.pan': 'Nyakaza',
      'viewer.windowLevel': 'Ifasitela/Izinga',
      'viewer.measure': 'Kala',
      'viewer.annotate': 'Qopha',
      'viewer.reset': 'Setha kabusha',
      'viewer.fullscreen': 'Isikrini esigcwele',

      // Patient Information
      'patient.id': 'I-ID Yesigulane',
      'patient.name': 'Igama Lesigulane',
      'patient.birthDate': 'Usuku Lokuzalwa',
      'patient.sex': 'Ubulili',
      'patient.age': 'Iminyaka',
      'patient.male': 'Owesilisa',
      'patient.female': 'Owesifazane',

      // Study Information
      'study.date': 'Usuku Lwesifundo',
      'study.time': 'Isikhathi Sesifundo',
      'study.description': 'Incazelo Yesifundo',
      'study.modality': 'Indlela',
      'study.referringPhysician': 'Udokotela Othumayo',
      'study.accessionNumber': 'Inombolo Yokufinyelela',

      // HPCSA Compliance
      'hpcsa.title': 'Ukuthobela kwe-HPCSA',
      'hpcsa.verification': 'Ukuqinisekisa Inombolo ye-HPCSA',
      'hpcsa.number': 'Inombolo Yokubhalisa kwe-HPCSA',
      'hpcsa.verified': 'Uchwepheshe Wezempilo Oqinisekisiwe',
      'hpcsa.sessionTimeout': 'Isikhathi sizophela ngo',
      'hpcsa.sessionExpired': 'Isikhathi siphelelwe ngokuphepha',
      'hpcsa.auditLog': 'Ukufinyelela kufakwe ku-log yokuthobela i-HPCSA',

      // POPIA Compliance
      'popia.title': 'Ukuvikelwa Kwedatha ye-POPIA',
      'popia.consentRequired': 'Imvume yesigulane iyadingeka ukubuka',
      'popia.consentConfirm': 'Ngiqinisekisa ukuthi imvume efanele itholiwe',
      'popia.dataMinimization': 'Ukunciphisa idatha kusetshenzisiwe',
      'popia.anonymized': 'Idatha yesigulane ifihliwe ngobumfihlo',

      // Network & Mobile
      'network.quality': 'Ikhwalithi Yesithombe',
      'network.lowQuality': 'Ikhwalithi Ephansi (3G Enobungane)',
      'network.mediumQuality': 'Ikhwalithi Ephakathi (4G)',
      'network.highQuality': 'Ikhwalithi Ephezulu (WiFi)',
      'network.slowConnection': 'Ukuxhumana okuhamba kancane kutholiwe',
      'network.offlineMode': 'Imodi Yangaphandle - Ukusebenza okukhawulelwe',
      'mobile.touchGestures': 'Izimpawu zokuthinta zivuliwe',
      'mobile.pinchZoom': 'Cinezela ukuze ukhulise',
      'mobile.doubleTapFit': 'Thepha kabili ukuze kulingane',

      // Errors and Warnings
      'error.loadingStudy': 'Iphutha ekulayisheni isifundo',
      'error.networkTimeout': 'Isikhathi senethiwekhi siphele',
      'error.unauthorized': 'Ukufinyelela okungagunyaziwe',
      'error.invalidHPCSA': 'Inombolo ye-HPCSA engalungile',
      'warning.lowBandwidth': 'I-bandwidth ephansi itholiwe - ikhwalithi incishisiwe',
      'warning.unsavedChanges': 'Unezinguquko ezingalondoloziwe'
    }
  },

  /**
   * Language Management
   */
  languageManager: {
    currentLanguage: 'en',
    fallbackLanguage: 'en',

    /**
     * Initialize language system
     */
    initialize: () => {
      // Detect user's preferred language
      const browserLang = navigator.language.substr(0, 2);
      const supportedLangs = ['en', 'af', 'zu'];
      
      // Check localStorage for saved preference
      const savedLang = localStorage.getItem('sa-medical-language');
      
      if (savedLang && supportedLangs.includes(savedLang)) {
        this.currentLanguage = savedLang;
      } else if (supportedLangs.includes(browserLang)) {
        this.currentLanguage = browserLang;
      }
      
      this.createLanguageSelector();
      this.applyLanguage(this.currentLanguage);
    },

    /**
     * Create language selector UI
     */
    createLanguageSelector: () => {
      const selector = document.createElement('div');
      selector.className = 'sa-language-selector';
      selector.innerHTML = `
        <div class="language-dropdown">
          <button class="language-toggle" id="languageToggle">
            🌐 ${this.getLanguageName(this.currentLanguage)}
          </button>
          <div class="language-options" id="languageOptions">
            <div class="language-option" data-lang="en">
              🇬🇧 English
            </div>
            <div class="language-option" data-lang="af">
              🇿🇦 Afrikaans
            </div>
            <div class="language-option" data-lang="zu">
              🇿🇦 isiZulu
            </div>
          </div>
        </div>
      `;
      
      document.body.appendChild(selector);
      
      // Add event handlers
      document.getElementById('languageToggle').addEventListener('click', () => {
        const options = document.getElementById('languageOptions');
        options.style.display = options.style.display === 'block' ? 'none' : 'block';
      });
      
      document.querySelectorAll('.language-option').forEach(option => {
        option.addEventListener('click', (e) => {
          const lang = e.target.dataset.lang;
          this.switchLanguage(lang);
          document.getElementById('languageOptions').style.display = 'none';
        });
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.sa-language-selector')) {
          document.getElementById('languageOptions').style.display = 'none';
        }
      });
    },

    /**
     * Switch to a different language
     */
    switchLanguage: (lang) => {
      this.currentLanguage = lang;
      localStorage.setItem('sa-medical-language', lang);
      
      // Update toggle button
      document.getElementById('languageToggle').textContent = 
        `🌐 ${this.getLanguageName(lang)}`;
      
      // Apply new language
      this.applyLanguage(lang);
      
      // Refresh any dynamic content
      this.refreshUIElements();
    },

    /**
     * Apply language to all UI elements
     */
    applyLanguage: (lang) => {
      document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.dataset.i18n;
        const translation = this.translate(key, lang);
        
        if (element.tagName === 'INPUT' && element.type === 'button') {
          element.value = translation;
        } else if (element.tagName === 'INPUT' && element.placeholder) {
          element.placeholder = translation;
        } else {
          element.textContent = translation;
        }
      });
      
      // Update document title if available
      const titleElement = document.querySelector('[data-i18n="viewer.title"]');
      if (titleElement) {
        document.title = this.translate('viewer.title', lang);
      }
    },

    /**
     * Get language display name
     */
    getLanguageName: (lang) => {
      const names = {
        'en': 'English',
        'af': 'Afrikaans',
        'zu': 'isiZulu'
      };
      return names[lang] || names['en'];
    },

    /**
     * Translate a key to current language
     */
    translate: (key, lang = null) => {
      const targetLang = lang || this.currentLanguage;
      const translations = window.saLanguagePlugin.translations;
      
      if (translations[targetLang] && translations[targetLang][key]) {
        return translations[targetLang][key];
      }
      
      // Fallback to English
      if (translations[this.fallbackLanguage] && translations[this.fallbackLanguage][key]) {
        return translations[this.fallbackLanguage][key];
      }
      
      // Return key if no translation found
      return key;
    },

    /**
     * Refresh UI elements that may need language updates
     */
    refreshUIElements: () => {
      // Refresh any dynamically generated content
      const events = ['languageChanged'];
      events.forEach(eventName => {
        document.dispatchEvent(new CustomEvent(eventName, {
          detail: { language: this.currentLanguage }
        }));
      });
    }
  },

  /**
   * Utility functions for components
   */
  utils: {
    /**
     * Create internationalized text element
     */
    createI18nElement: (tag, i18nKey, className = '') => {
      const element = document.createElement(tag);
      element.dataset.i18n = i18nKey;
      element.textContent = this.languageManager.translate(i18nKey);
      if (className) {
        element.className = className;
      }
      return element;
    },

    /**
     * Format medical dates according to local preferences
     */
    formatMedicalDate: (dateString, lang = null) => {
      const targetLang = lang || this.languageManager.currentLanguage;
      const date = new Date(dateString);
      
      const locales = {
        'en': 'en-ZA',
        'af': 'af-ZA',
        'zu': 'en-ZA' // Use English format for isiZulu as locale support varies
      };
      
      return date.toLocaleDateString(locales[targetLang] || 'en-ZA', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    },

    /**
     * Format medical time according to local preferences
     */
    formatMedicalTime: (timeString, lang = null) => {
      const targetLang = lang || this.languageManager.currentLanguage;
      const date = new Date(`1970-01-01T${timeString}`);
      
      const locales = {
        'en': 'en-ZA',
        'af': 'af-ZA',
        'zu': 'en-ZA'
      };
      
      return date.toLocaleTimeString(locales[targetLang] || 'en-ZA', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }
  },

  /**
   * Plugin initialization
   */
  preRegistration: ({ servicesManager, configuration }) => {
    console.log('🇿🇦 SA Multi-Language Plugin initialized');
    
    // Initialize language system
    this.languageManager.initialize();
    
    // Export to global scope
    window.saLanguagePlugin = {
      translations: this.translations,
      manager: this.languageManager,
      utils: this.utils,
      t: this.languageManager.translate.bind(this.languageManager)
    };
    
    // Global translation function
    window.t = window.saLanguagePlugin.t;
  }
};

export default SA_LANGUAGE_PLUGIN;
