/**
 * 🇿🇦 SA Medical Theme for OHIF
 * 
 * Custom styling and branding for South African healthcare environment
 */

const SA_MEDICAL_THEME = {
  id: '@sa-medical/theme-sa-healthcare',
  version: '1.0.0',

  /**
   * Color Palette - South African Healthcare Theme
   */
  colors: {
    // Primary - Professional medical blue with SA flag inspiration
    primary: {
      50: '#e3f2fd',
      100: '#bbdefb',
      200: '#90caf9',
      300: '#64b5f6',
      400: '#42a5f5',
      500: '#1e88e5', // Main primary
      600: '#1976d2',
      700: '#1565c0',
      800: '#0d47a1',
      900: '#0d47a1'
    },

    // Secondary - South African green
    secondary: {
      50: '#e8f5e8',
      100: '#c8e6c9',
      200: '#a5d6a7',
      300: '#81c784',
      400: '#66bb6a',
      500: '#4caf50', // Main secondary
      600: '#43a047',
      700: '#388e3c',
      800: '#2e7d32',
      900: '#1b5e20'
    },

    // Medical Red - for urgent/critical
    medical: {
      50: '#ffebee',
      100: '#ffcdd2',
      200: '#ef9a9a',
      300: '#e57373',
      400: '#ef5350',
      500: '#f44336', // Main medical red
      600: '#e53935',
      700: '#d32f2f',
      800: '#c62828',
      900: '#b71c1c'
    },

    // Neutral grays
    neutral: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#9e9e9e',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121'
    },

    // Background colors
    background: {
      default: '#fafafa',
      paper: '#ffffff',
      dark: '#121212',
      sidebar: '#f8f9fa'
    },

    // Text colors
    text: {
      primary: '#212121',
      secondary: '#757575',
      disabled: '#bdbdbd',
      hint: '#9e9e9e'
    }
  },

  /**
   * Typography - Medical document standards
   */
  typography: {
    fontFamily: {
      primary: '"Roboto", "Helvetica", "Arial", sans-serif',
      mono: '"Roboto Mono", "Courier New", monospace',
      medical: '"Source Sans Pro", "Roboto", sans-serif'
    },
    
    fontSize: {
      xs: '0.75rem',   // 12px
      sm: '0.875rem',  // 14px
      base: '1rem',    // 16px
      lg: '1.125rem',  // 18px
      xl: '1.25rem',   // 20px
      '2xl': '1.5rem', // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem'   // 36px
    },

    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },

    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.75
    }
  },

  /**
   * Component Styles
   */
  components: {
    // Medical Viewer Styles
    viewer: {
      background: '#000000',
      borderColor: '#333333',
      overlayColor: 'rgba(255, 255, 255, 0.8)',
      crosshairColor: '#00ff00',
      annotationColor: '#ffff00'
    },

    // Header/Navigation
    header: {
      background: 'linear-gradient(135deg, #1e88e5 0%, #1565c0 100%)',
      color: '#ffffff',
      height: '60px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },

    // Sidebar
    sidebar: {
      background: '#f8f9fa',
      borderColor: '#e0e0e0',
      width: '300px'
    },

    // Buttons
    button: {
      primary: {
        background: '#1e88e5',
        color: '#ffffff',
        hover: '#1565c0',
        active: '#0d47a1'
      },
      secondary: {
        background: '#4caf50',
        color: '#ffffff',
        hover: '#43a047',
        active: '#388e3c'
      },
      medical: {
        background: '#f44336',
        color: '#ffffff',
        hover: '#e53935',
        active: '#d32f2f'
      }
    },

    // Form Elements
    input: {
      background: '#ffffff',
      border: '1px solid #e0e0e0',
      borderRadius: '4px',
      focus: '#1e88e5'
    },

    // Cards/Panels
    card: {
      background: '#ffffff',
      border: '1px solid #e0e0e0',
      borderRadius: '8px',
      shadow: '0 2px 8px rgba(0,0,0,0.1)'
    }
  },

  /**
   * Mobile Responsive Breakpoints
   */
  breakpoints: {
    xs: '480px',
    sm: '768px',
    md: '1024px',
    lg: '1280px',
    xl: '1440px'
  },

  /**
   * Apply theme to OHIF viewer
   */
  applyTheme: () => {
    // Create CSS custom properties
    const cssVariables = `
      :root {
        /* Colors */
        --sa-primary-50: ${SA_MEDICAL_THEME.colors.primary[50]};
        --sa-primary-500: ${SA_MEDICAL_THEME.colors.primary[500]};
        --sa-primary-700: ${SA_MEDICAL_THEME.colors.primary[700]};
        --sa-secondary-500: ${SA_MEDICAL_THEME.colors.secondary[500]};
        --sa-medical-500: ${SA_MEDICAL_THEME.colors.medical[500]};
        --sa-neutral-100: ${SA_MEDICAL_THEME.colors.neutral[100]};
        --sa-neutral-800: ${SA_MEDICAL_THEME.colors.neutral[800]};
        --sa-background-default: ${SA_MEDICAL_THEME.colors.background.default};
        --sa-background-paper: ${SA_MEDICAL_THEME.colors.background.paper};
        --sa-text-primary: ${SA_MEDICAL_THEME.colors.text.primary};
        --sa-text-secondary: ${SA_MEDICAL_THEME.colors.text.secondary};

        /* Typography */
        --sa-font-family: ${SA_MEDICAL_THEME.typography.fontFamily.primary};
        --sa-font-family-mono: ${SA_MEDICAL_THEME.typography.fontFamily.mono};
        --sa-font-size-base: ${SA_MEDICAL_THEME.typography.fontSize.base};
        --sa-font-weight-normal: ${SA_MEDICAL_THEME.typography.fontWeight.normal};
        --sa-font-weight-bold: ${SA_MEDICAL_THEME.typography.fontWeight.bold};

        /* Components */
        --sa-header-height: ${SA_MEDICAL_THEME.components.header.height};
        --sa-sidebar-width: ${SA_MEDICAL_THEME.components.sidebar.width};
      }
    `;

    // Main theme styles
    const themeStyles = `
      /* Global Styles */
      body {
        font-family: var(--sa-font-family);
        background-color: var(--sa-background-default);
        color: var(--sa-text-primary);
        margin: 0;
        padding: 0;
      }

      /* Header/Navigation */
      .ohif-header,
      .sa-header {
        background: ${SA_MEDICAL_THEME.components.header.background};
        color: ${SA_MEDICAL_THEME.components.header.color};
        height: ${SA_MEDICAL_THEME.components.header.height};
        box-shadow: ${SA_MEDICAL_THEME.components.header.boxShadow};
        display: flex;
        align-items: center;
        padding: 0 20px;
        position: sticky;
        top: 0;
        z-index: 1000;
      }

      .sa-header .logo {
        height: 40px;
        margin-right: 20px;
      }

      .sa-header .title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-right: auto;
      }

      /* Sidebar */
      .ohif-sidebar,
      .sa-sidebar {
        background: ${SA_MEDICAL_THEME.components.sidebar.background};
        border-right: 1px solid ${SA_MEDICAL_THEME.components.sidebar.borderColor};
        width: ${SA_MEDICAL_THEME.components.sidebar.width};
        min-height: 100vh;
        overflow-y: auto;
      }

      /* Medical Viewer */
      .cornerstone-canvas,
      .sa-medical-viewer {
        background: ${SA_MEDICAL_THEME.components.viewer.background};
      }

      .viewport-overlay {
        color: ${SA_MEDICAL_THEME.components.viewer.overlayColor};
        font-family: var(--sa-font-family-mono);
        font-size: 12px;
      }

      /* Buttons */
      .btn-primary,
      .sa-btn-primary {
        background-color: ${SA_MEDICAL_THEME.components.button.primary.background};
        color: ${SA_MEDICAL_THEME.components.button.primary.color};
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s;
      }

      .btn-primary:hover,
      .sa-btn-primary:hover {
        background-color: ${SA_MEDICAL_THEME.components.button.primary.hover};
      }

      .btn-secondary,
      .sa-btn-secondary {
        background-color: ${SA_MEDICAL_THEME.components.button.secondary.background};
        color: ${SA_MEDICAL_THEME.components.button.secondary.color};
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s;
      }

      .btn-medical,
      .sa-btn-medical {
        background-color: ${SA_MEDICAL_THEME.components.button.medical.background};
        color: ${SA_MEDICAL_THEME.components.button.medical.color};
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s;
      }

      /* Form Elements */
      input,
      select,
      textarea {
        background: ${SA_MEDICAL_THEME.components.input.background};
        border: ${SA_MEDICAL_THEME.components.input.border};
        border-radius: ${SA_MEDICAL_THEME.components.input.borderRadius};
        padding: 8px 12px;
        font-family: var(--sa-font-family);
        font-size: var(--sa-font-size-base);
      }

      input:focus,
      select:focus,
      textarea:focus {
        outline: none;
        border-color: ${SA_MEDICAL_THEME.components.input.focus};
        box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.2);
      }

      /* Cards/Panels */
      .card,
      .panel,
      .sa-card {
        background: ${SA_MEDICAL_THEME.components.card.background};
        border: ${SA_MEDICAL_THEME.components.card.border};
        border-radius: ${SA_MEDICAL_THEME.components.card.borderRadius};
        box-shadow: ${SA_MEDICAL_THEME.components.card.shadow};
        padding: 16px;
        margin-bottom: 16px;
      }

      /* Patient Information Panel */
      .patient-info {
        background: var(--sa-background-paper);
        border-left: 4px solid var(--sa-primary-500);
        padding: 16px;
        margin-bottom: 16px;
      }

      .patient-info h3 {
        margin: 0 0 8px 0;
        color: var(--sa-primary-700);
        font-weight: 600;
      }

      .patient-info .info-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
      }

      .patient-info .label {
        font-weight: 500;
        color: var(--sa-text-secondary);
      }

      .patient-info .value {
        color: var(--sa-text-primary);
      }

      /* Compliance Indicators */
      .hpcsa-indicator {
        background: linear-gradient(45deg, #4caf50, #66bb6a);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        display: inline-block;
      }

      .popia-indicator {
        background: linear-gradient(45deg, #ff9800, #ffb74d);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        display: inline-block;
      }

      /* Mobile Tool Panel */
      .sa-mobile-tool-panel {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        border-radius: 25px;
        padding: 10px;
        display: flex;
        gap: 10px;
        z-index: 1000;
      }

      .sa-mobile-tool-panel .tool-btn {
        width: 40px;
        height: 40px;
        border: none;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        color: white;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
      }

      .sa-mobile-tool-panel .tool-btn:hover,
      .sa-mobile-tool-panel .tool-btn.active {
        background: var(--sa-primary-500);
        transform: scale(1.1);
      }

      /* Language Selector */
      .sa-language-selector {
        position: fixed;
        top: 70px;
        right: 20px;
        z-index: 1000;
      }

      .language-dropdown {
        position: relative;
      }

      .language-toggle {
        background: var(--sa-background-paper);
        border: 1px solid var(--sa-neutral-100);
        border-radius: 20px;
        padding: 6px 12px;
        font-size: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .language-options {
        position: absolute;
        top: 100%;
        right: 0;
        background: var(--sa-background-paper);
        border: 1px solid var(--sa-neutral-100);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        display: none;
        min-width: 150px;
      }

      .language-option {
        padding: 8px 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
      }

      .language-option:hover {
        background: var(--sa-primary-50);
      }

      /* Quality Toggle */
      .sa-quality-toggle {
        position: fixed;
        bottom: 80px;
        right: 20px;
        z-index: 1000;
      }

      .quality-selector {
        background: var(--sa-background-paper);
        border: 1px solid var(--sa-neutral-100);
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }

      .quality-label {
        font-weight: 500;
        margin-right: 8px;
      }

      #quality-select {
        border: none;
        background: transparent;
        font-size: 12px;
      }

      /* Connection Warning */
      .sa-connection-warning {
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: #ff9800;
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        z-index: 1000;
        max-width: 400px;
      }

      .warning-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      .warning-content button {
        background: none;
        border: none;
        color: white;
        font-size: 16px;
        cursor: pointer;
      }

      /* Offline Indicator */
      .sa-offline-indicator {
        position: fixed;
        top: 80px;
        left: 20px;
        background: #9e9e9e;
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 1000;
      }

      /* Responsive Design */
      @media (max-width: 768px) {
        .sa-header .title {
          font-size: 1rem;
        }
        
        .sa-sidebar {
          width: 100%;
          position: fixed;
          left: -100%;
          transition: left 0.3s;
          z-index: 999;
        }
        
        .sa-sidebar.open {
          left: 0;
        }
        
        .patient-info .info-row {
          flex-direction: column;
        }
        
        .sa-language-selector {
          top: 10px;
          right: 10px;
        }
        
        .sa-quality-toggle {
          bottom: 10px;
          right: 10px;
        }
      }

      /* South African Flag Accent */
      .sa-flag-accent {
        background: linear-gradient(
          to right,
          #007749 0%,
          #007749 16.66%,
          #ffffff 16.66%,
          #ffffff 33.33%,
          #de3831 33.33%,
          #de3831 50%,
          #ffffff 50%,
          #ffffff 66.66%,
          #001489 66.66%,
          #001489 83.33%,
          #ffb81c 83.33%,
          #ffb81c 100%
        );
        height: 4px;
        width: 100%;
      }
    `;

    // Inject styles
    const styleElement = document.createElement('style');
    styleElement.id = 'sa-medical-theme';
    styleElement.textContent = cssVariables + themeStyles;
    
    // Remove existing theme if present
    const existingTheme = document.getElementById('sa-medical-theme');
    if (existingTheme) {
      existingTheme.remove();
    }
    
    document.head.appendChild(styleElement);
    
    console.log('🇿🇦 SA Medical Theme applied');
  },

  /**
   * Create SA medical header
   */
  createHeader: () => {
    const header = document.createElement('div');
    header.className = 'sa-header';
    header.innerHTML = `
      <div class="sa-flag-accent"></div>
      <div style="display: flex; align-items: center; padding: 0 20px; height: 56px;">
        <div class="logo">🏥</div>
        <div class="title">SA Medical DICOM Viewer</div>
        <div style="margin-left: auto; display: flex; align-items: center; gap: 16px;">
          <span class="hpcsa-indicator">HPCSA Compliant</span>
          <span class="popia-indicator">POPIA Protected</span>
        </div>
      </div>
    `;
    
    // Insert at top of body
    document.body.insertBefore(header, document.body.firstChild);
  },

  /**
   * Plugin initialization
   */
  preRegistration: ({ servicesManager, configuration }) => {
    console.log('🇿🇦 SA Medical Theme initialized');
    
    // Apply theme immediately
    this.applyTheme();
    
    // Create header
    this.createHeader();
    
    // Export theme to global scope
    window.saMedicalTheme = SA_MEDICAL_THEME;
  }
};

export default SA_MEDICAL_THEME;
