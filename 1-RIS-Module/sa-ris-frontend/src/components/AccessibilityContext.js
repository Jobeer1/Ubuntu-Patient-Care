import React, { createContext, useContext, useState, useEffect } from 'react';

// Accessibility and Localization Context
const AccessibilityContext = createContext();

// South African languages and locales
const saLocales = {
  en: {
    code: 'en',
    name: 'English',
    rtl: false,
    translations: {
      dashboard: 'Dashboard',
      patients: 'Patients',
      studies: 'Studies',
      reports: 'Reports',
      urgentCases: 'Urgent Cases',
      criticalFindings: 'Critical Findings',
      todayStudies: "Today's Studies",
      completedReports: 'Completed Reports',
      pendingCases: 'Pending Cases',
      view: 'View',
      refresh: 'Refresh',
      notifications: 'Notifications',
      search: 'Search',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      warning: 'Warning',
      close: 'Close',
      save: 'Save',
      cancel: 'Cancel',
      confirm: 'Confirm',
      yes: 'Yes',
      no: 'No'
    }
  },
  af: {
    code: 'af',
    name: 'Afrikaans',
    rtl: false,
    translations: {
      dashboard: 'Dashboard',
      patients: 'Pasiënte',
      studies: 'Studies',
      reports: 'Verslae',
      urgentCases: 'Dringende Gevalle',
      criticalFindings: 'Kritieke Bevindinge',
      todayStudies: 'Vandag se Studies',
      completedReports: 'Voltooide Verslae',
      pendingCases: 'Hangende Gevalle',
      view: 'Bekyk',
      refresh: 'Verfris',
      notifications: 'Kennisgewings',
      search: 'Soek',
      loading: 'Laai...',
      error: 'Fout',
      success: 'Sukses',
      warning: 'Waarskuwing',
      close: 'Sluit',
      save: 'Stoor',
      cancel: 'Kanselleer',
      confirm: 'Bevestig',
      yes: 'Ja',
      no: 'Nee'
    }
  },
  zu: {
    code: 'zu',
    name: 'isiZulu',
    rtl: false,
    translations: {
      dashboard: 'Ideshibhodi',
      patients: 'Iziguli',
      studies: 'Izifundo',
      reports: 'Imibiko',
      urgentCases: 'Amacala Aphuthumayo',
      criticalFindings: 'Ukutholakala Okubalulekile',
      todayStudies: 'Izifundo Zanamuhla',
      completedReports: 'Imibiko Eqediwe',
      pendingCases: 'Amacala Alindile',
      view: 'Buka',
      refresh: 'Vuselela',
      notifications: 'Izaziso',
      search: 'Sesha',
      loading: 'Iyalayisha...',
      error: 'Iphutha',
      success: 'Impumelelo',
      warning: 'Isixwayiso',
      close: 'Vala',
      save: 'Gcina',
      cancel: 'Khansela',
      confirm: 'Qinisekisa',
      yes: 'Yebo',
      no: 'Cha'
    }
  }
};

// Accessibility settings
const defaultAccessibilitySettings = {
  highContrast: false,
  largeText: false,
  reducedMotion: false,
  screenReader: false,
  keyboardNavigation: true,
  focusIndicators: true,
  colorBlindFriendly: false,
  fontSize: 'medium', // small, medium, large, xlarge
  theme: 'default' // default, high-contrast, color-blind
};

// South African color schemes for accessibility
const saColorSchemes = {
  default: {
    primary: '#002654',
    secondary: '#E03C31',
    accent: '#FFB612',
    success: '#007A33',
    warning: '#FF6B35',
    error: '#D52B1E',
    background: '#F8F9FA',
    surface: '#FFFFFF',
    text: '#2C3E50',
    textSecondary: '#6C757D'
  },
  highContrast: {
    primary: '#000000',
    secondary: '#FFFFFF',
    accent: '#FFFF00',
    success: '#00FF00',
    warning: '#FFA500',
    error: '#FF0000',
    background: '#FFFFFF',
    surface: '#FFFFFF',
    text: '#000000',
    textSecondary: '#333333'
  },
  colorBlind: {
    primary: '#002654',
    secondary: '#E03C31',
    accent: '#FFB612',
    success: '#007A33',
    warning: '#FF6B35',
    error: '#D52B1E',
    background: '#F8F9FA',
    surface: '#FFFFFF',
    text: '#2C3E50',
    textSecondary: '#6C757D'
  }
};

export const AccessibilityProvider = ({ children }) => {
  const [currentLocale, setCurrentLocale] = useState('en');
  const [accessibilitySettings, setAccessibilitySettings] = useState(defaultAccessibilitySettings);
  const [announcements, setAnnouncements] = useState([]);

  // Load settings from localStorage
  useEffect(() => {
    const savedLocale = localStorage.getItem('sa-ris-locale');
    const savedSettings = localStorage.getItem('sa-ris-accessibility');

    if (savedLocale && saLocales[savedLocale]) {
      setCurrentLocale(savedLocale);
    }

    if (savedSettings) {
      try {
        setAccessibilitySettings(JSON.parse(savedSettings));
      } catch (e) {
        console.warn('Failed to parse accessibility settings');
      }
    }

    // Detect system preferences
    detectSystemPreferences();
  }, []);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('sa-ris-locale', currentLocale);
  }, [currentLocale]);

  useEffect(() => {
    localStorage.setItem('sa-ris-accessibility', JSON.stringify(accessibilitySettings));
  }, [accessibilitySettings]);

  const detectSystemPreferences = () => {
    // Detect if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setAccessibilitySettings(prev => ({
        ...prev,
        reducedMotion: true
      }));
    }

    // Detect if user prefers high contrast
    const prefersHighContrast = window.matchMedia('(prefers-contrast: high)').matches;
    if (prefersHighContrast) {
      setAccessibilitySettings(prev => ({
        ...prev,
        highContrast: true,
        theme: 'high-contrast'
      }));
    }

    // Detect color scheme preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      // Could implement dark theme in the future
    }
  };

  const translate = (key, fallback = key) => {
    const locale = saLocales[currentLocale];
    return locale?.translations[key] || fallback;
  };

  const getCurrentColors = () => {
    return saColorSchemes[accessibilitySettings.theme] || saColorSchemes.default;
  };

  const announceToScreenReader = (message, priority = 'polite') => {
    const announcement = {
      id: Date.now(),
      message,
      priority,
      timestamp: new Date()
    };

    setAnnouncements(prev => [...prev, announcement]);

    // Remove announcement after it's been read
    setTimeout(() => {
      setAnnouncements(prev => prev.filter(a => a.id !== announcement.id));
    }, 1000);

    // Use browser's announcement API if available
    if ('speechSynthesis' in window && accessibilitySettings.screenReader) {
      const utterance = new SpeechSynthesisUtterance(message);
      window.speechSynthesis.speak(utterance);
    }
  };

  const updateAccessibilitySetting = (key, value) => {
    setAccessibilitySettings(prev => ({
      ...prev,
      [key]: value
    }));

    // Announce change to screen reader
    announceToScreenReader(`${key} ${value ? 'enabled' : 'disabled'}`, 'assertive');
  };

  const changeLocale = (localeCode) => {
    if (saLocales[localeCode]) {
      setCurrentLocale(localeCode);
      announceToScreenReader(`Language changed to ${saLocales[localeCode].name}`, 'assertive');

      // Reload page to apply new locale (in a real app, this would be handled by the routing system)
      // window.location.reload();
    }
  };

  const getFontSize = () => {
    const sizes = {
      small: '14px',
      medium: '16px',
      large: '18px',
      xlarge: '20px'
    };
    return sizes[accessibilitySettings.fontSize] || sizes.medium;
  };

  const getLineHeight = () => {
    const heights = {
      small: 1.4,
      medium: 1.5,
      large: 1.6,
      xlarge: 1.7
    };
    return heights[accessibilitySettings.fontSize] || heights.medium;
  };

  const value = {
    // Locale
    currentLocale,
    availableLocales: Object.values(saLocales),
    translate,
    changeLocale,

    // Accessibility
    accessibilitySettings,
    updateAccessibilitySetting,
    colors: getCurrentColors(),
    fontSize: getFontSize(),
    lineHeight: getLineHeight(),

    // Screen reader
    announceToScreenReader,
    announcements,

    // Utilities
    isHighContrast: accessibilitySettings.highContrast,
    isLargeText: accessibilitySettings.largeText,
    isReducedMotion: accessibilitySettings.reducedMotion,
    isScreenReaderEnabled: accessibilitySettings.screenReader,
    isKeyboardNavigationEnabled: accessibilitySettings.keyboardNavigation,
    isFocusIndicatorsEnabled: accessibilitySettings.focusIndicators,
    isColorBlindFriendly: accessibilitySettings.colorBlindFriendly
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
};

export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

// Higher-order component for accessibility
export const withAccessibility = (WrappedComponent) => {
  return (props) => {
    const accessibility = useAccessibility();
    return <WrappedComponent {...props} accessibility={accessibility} />;
  };
};

// Accessible Button Component
export const AccessibleButton = ({
  children,
  onClick,
  disabled,
  loading,
  type = 'default',
  size = 'medium',
  accessibility,
  ariaLabel,
  ariaDescribedBy,
  ...props
}) => {
  const handleClick = (e) => {
    if (onClick) {
      onClick(e);
      accessibility.announceToScreenReader(`${children} button clicked`);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(e);
    }
  };

  return (
    <button
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={disabled || loading}
      aria-label={ariaLabel || children}
      aria-describedby={ariaDescribedBy}
      aria-pressed={type === 'primary'}
      role="button"
      tabIndex={disabled ? -1 : 0}
      style={{
        fontSize: accessibility.fontSize,
        lineHeight: accessibility.lineHeight,
        minHeight: size === 'large' ? '44px' : '36px',
        padding: size === 'large' ? '12px 24px' : '8px 16px',
        border: `2px solid ${accessibility.colors.primary}`,
        borderRadius: '4px',
        backgroundColor: type === 'primary' ? accessibility.colors.primary : 'transparent',
        color: type === 'primary' ? 'white' : accessibility.colors.primary,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: accessibility.isReducedMotion ? 'none' : 'all 0.2s ease',
        outline: 'none',
        ...props.style
      }}
      {...props}
    >
      {loading ? accessibility.translate('loading') : children}
    </button>
  );
};

// Accessible Modal Component
export const AccessibleModal = ({
  visible,
  onClose,
  title,
  children,
  accessibility,
  size = 'medium'
}) => {
  useEffect(() => {
    if (visible) {
      accessibility.announceToScreenReader(`${title} dialog opened`);
      // Focus trap implementation would go here
    }
  }, [visible, title, accessibility]);

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!visible) return null;

  const sizes = {
    small: { width: '400px', height: '300px' },
    medium: { width: '600px', height: '400px' },
    large: { width: '800px', height: '600px' }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-content"
      onKeyDown={handleKeyDown}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
    >
      <div
        style={{
          backgroundColor: accessibility.colors.surface,
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
          width: sizes[size].width,
          maxHeight: sizes[size].height,
          overflow: 'auto',
          padding: '24px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2
            id="modal-title"
            style={{
              margin: 0,
              color: accessibility.colors.text,
              fontSize: accessibility.fontSize
            }}
          >
            {title}
          </h2>
          <AccessibleButton
            onClick={onClose}
            accessibility={accessibility}
            ariaLabel={accessibility.translate('close')}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer'
            }}
          >
            ×
          </AccessibleButton>
        </div>
        <div id="modal-content">
          {children}
        </div>
      </div>
    </div>
  );
};

// Language Switcher Component
export const LanguageSwitcher = () => {
  const accessibility = useAccessibility();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={accessibility.translate('changeLanguage')}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        style={{
          fontSize: accessibility.fontSize,
          lineHeight: accessibility.lineHeight,
          minHeight: '36px',
          padding: '8px 16px',
          border: `2px solid ${accessibility.colors.primary}`,
          borderRadius: '4px',
          backgroundColor: 'transparent',
          color: accessibility.colors.primary,
          cursor: 'pointer',
          transition: accessibility.isReducedMotion ? 'none' : 'all 0.2s ease',
          outline: 'none'
        }}
      >
        {saLocales[accessibility.currentLocale].name} ▼
      </button>

      {isOpen && (
        <ul
          role="listbox"
          aria-label={accessibility.translate('selectLanguage')}
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            backgroundColor: accessibility.colors.surface,
            border: `1px solid ${accessibility.colors.primary}`,
            borderRadius: '4px',
            listStyle: 'none',
            margin: 0,
            padding: 0,
            zIndex: 100
          }}
        >
          {Object.values(saLocales).map((locale) => (
            <li key={locale.code}>
              <button
                onClick={() => {
                  accessibility.changeLocale(locale.code);
                  setIsOpen(false);
                }}
                aria-selected={accessibility.currentLocale === locale.code}
                role="option"
                style={{
                  width: '100%',
                  textAlign: 'left',
                  border: 'none',
                  borderRadius: 0,
                  padding: '8px 16px',
                  fontSize: accessibility.fontSize,
                  cursor: 'pointer',
                  background: accessibility.currentLocale === locale.code ? accessibility.colors.primary : 'transparent',
                  color: accessibility.currentLocale === locale.code ? 'white' : accessibility.colors.text
                }}
              >
                {locale.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// Accessibility Settings Panel
export const AccessibilitySettings = () => {
  const accessibility = useAccessibility();
  
  return (
    <div style={{ padding: '24px', backgroundColor: accessibility.colors.surface }}>
      <h2 style={{ color: accessibility.colors.text, marginBottom: '24px' }}>
        Accessibility Settings
      </h2>

      <div style={{ display: 'grid', gap: '16px' }}>
        {/* Font Size */}
        <div>
          <label style={{ display: 'block', marginBottom: '8px', color: accessibility.colors.text }}>
            Font Size
          </label>
          <select
            value={accessibility.accessibilitySettings.fontSize}
            onChange={(e) => accessibility.updateAccessibilitySetting('fontSize', e.target.value)}
            style={{
              width: '100%',
              padding: '8px',
              border: `1px solid ${accessibility.colors.primary}`,
              borderRadius: '4px'
            }}
          >
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
            <option value="xlarge">Extra Large</option>
          </select>
        </div>

        {/* Theme */}
        <div>
          <label style={{ display: 'block', marginBottom: '8px', color: accessibility.colors.text }}>
            Theme
          </label>
          <select
            value={accessibility.accessibilitySettings.theme}
            onChange={(e) => accessibility.updateAccessibilitySetting('theme', e.target.value)}
            style={{
              width: '100%',
              padding: '8px',
              border: `1px solid ${accessibility.colors.primary}`,
              borderRadius: '4px'
            }}
          >
            <option value="default">Default</option>
            <option value="high-contrast">High Contrast</option>
            <option value="color-blind">Color Blind Friendly</option>
          </select>
        </div>

        {/* Checkboxes for other settings */}
        {[
          { key: 'highContrast', label: 'High Contrast' },
          { key: 'largeText', label: 'Large Text' },
          { key: 'reducedMotion', label: 'Reduced Motion' },
          { key: 'screenReader', label: 'Screen Reader Support' },
          { key: 'keyboardNavigation', label: 'Keyboard Navigation' },
          { key: 'focusIndicators', label: 'Focus Indicators' },
          { key: 'colorBlindFriendly', label: 'Color Blind Friendly' }
        ].map(({ key, label }) => (
          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: accessibility.colors.text }}>
            <input
              type="checkbox"
              checked={accessibility.accessibilitySettings[key]}
              onChange={(e) => accessibility.updateAccessibilitySetting(key, e.target.checked)}
            />
            {label}
          </label>
        ))}
      </div>
    </div>
  );
};

export default {
  AccessibilityProvider,
  useAccessibility,
  withAccessibility,
  AccessibleButton,
  AccessibleModal,
  LanguageSwitcher,
  AccessibilitySettings,
  saLocales,
  saColorSchemes
};