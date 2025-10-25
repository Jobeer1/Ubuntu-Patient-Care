/**
 * Mobile Framework for South African Medical Imaging System
 * Provides responsive design and touch optimization for clinical workflows
 */

class MobileFramework {
    constructor() {
        this.deviceType = this.detectDeviceType();
        this.networkCondition = 'unknown';
        this.orientation = 'portrait';
        this.touchSupport = 'ontouchstart' in window;
        this.isOffline = !navigator.onLine;
        
        this.init();
    }

    init() {
        this.setupViewportMeta();
        this.detectNetworkConditions();
        this.setupOrientationHandling();
        this.setupTouchOptimizations();
        this.setupOfflineHandling();
        this.setupSAOptimizations();
    }

    detectDeviceType() {
        const userAgent = navigator.userAgent.toLowerCase();
        const screenWidth = window.screen.width;
        
        if (userAgent.includes('mobile') || screenWidth < 768) {
            return 'mobile';
        } else if (userAgent.includes('tablet') || (screenWidth >= 768 && screenWidth < 1024)) {
            return 'tablet';
        }
        return 'desktop';
    }

    setupViewportMeta() {
        // Ensure proper mobile viewport
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes';
    }

    detectNetworkConditions() {
        // South African network optimization
        if ('connection' in navigator) {
            const connection = navigator.connection;
            this.networkCondition = connection.effectiveType || 'unknown';
            
            // Optimize for SA network conditions
            if (connection.effectiveType === '2g' || connection.effectiveType === 'slow-2g') {
                this.enableLowBandwidthMode();
            }
            
            connection.addEventListener('change', () => {
                this.networkCondition = connection.effectiveType;
                this.adjustForNetworkChange();
            });
        }
    }

    setupOrientationHandling() {
        const handleOrientationChange = () => {
            this.orientation = window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
            this.adjustLayoutForOrientation();
        };

        window.addEventListener('orientationchange', handleOrientationChange);
        window.addEventListener('resize', handleOrientationChange);
        handleOrientationChange(); // Initial call
    }

    setupTouchOptimizations() {
        if (!this.touchSupport) return;

        // Improve touch responsiveness
        document.addEventListener('touchstart', function() {}, { passive: true });
        
        // Prevent zoom on double-tap for medical precision
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(event) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        // Add touch-friendly classes
        document.body.classList.add('touch-device');
        document.body.classList.add(`device-${this.deviceType}`);
    }

    setupOfflineHandling() {
        window.addEventListener('online', () => {
            this.isOffline = false;
            this.handleOnlineStatus();
        });

        window.addEventListener('offline', () => {
            this.isOffline = true;
            this.handleOfflineStatus();
        });
    }

    setupSAOptimizations() {
        // South African specific optimizations
        this.setupLanguageDetection();
        this.setupLocalTimeZone();
        this.setupCurrencyFormat();
    }

    setupLanguageDetection() {
        const browserLang = navigator.language || navigator.userLanguage;
        const supportedLangs = ['en-ZA', 'af', 'zu'];
        
        let selectedLang = 'en-ZA'; // Default to South African English
        
        if (supportedLangs.includes(browserLang)) {
            selectedLang = browserLang;
        } else if (browserLang.startsWith('af')) {
            selectedLang = 'af';
        } else if (browserLang.startsWith('zu')) {
            selectedLang = 'zu';
        }
        
        document.documentElement.lang = selectedLang;
        localStorage.setItem('preferred-language', selectedLang);
    }

    setupLocalTimeZone() {
        // Set South African timezone (SAST - UTC+2)
        const timeZone = 'Africa/Johannesburg';
        localStorage.setItem('timezone', timeZone);
    }

    setupCurrencyFormat() {
        // South African Rand formatting
        localStorage.setItem('currency', 'ZAR');
        localStorage.setItem('currency-symbol', 'R');
    }

    enableLowBandwidthMode() {
        document.body.classList.add('low-bandwidth');
        
        // Reduce image quality
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (img.dataset.lowBandwidth) {
                img.src = img.dataset.lowBandwidth;
            }
        });
        
        // Disable non-essential animations
        document.body.classList.add('reduced-motion');
    }

    adjustForNetworkChange() {
        if (this.networkCondition === '2g' || this.networkCondition === 'slow-2g') {
            this.enableLowBandwidthMode();
        } else {
            document.body.classList.remove('low-bandwidth');
            document.body.classList.remove('reduced-motion');
        }
    }

    adjustLayoutForOrientation() {
        document.body.classList.remove('portrait', 'landscape');
        document.body.classList.add(this.orientation);
        
        // Trigger custom event for components to respond
        window.dispatchEvent(new CustomEvent('orientationChanged', {
            detail: { orientation: this.orientation }
        }));
    }

    handleOnlineStatus() {
        document.body.classList.remove('offline');
        document.body.classList.add('online');
        
        // Trigger sync for offline changes
        window.dispatchEvent(new CustomEvent('connectionRestored'));
    }

    handleOfflineStatus() {
        document.body.classList.remove('online');
        document.body.classList.add('offline');
        
        // Show offline indicator
        this.showOfflineNotification();
    }

    showOfflineNotification() {
        const notification = document.createElement('div');
        notification.className = 'offline-notification';
        notification.innerHTML = `
            <div class="offline-content">
                <span class="offline-icon">📡</span>
                <span class="offline-text">Working Offline</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove when back online
        window.addEventListener('online', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, { once: true });
    }

    // Utility methods for components
    isMobile() {
        return this.deviceType === 'mobile';
    }

    isTablet() {
        return this.deviceType === 'tablet';
    }

    isTouchDevice() {
        return this.touchSupport;
    }

    isLowBandwidth() {
        return this.networkCondition === '2g' || this.networkCondition === 'slow-2g';
    }

    getDeviceInfo() {
        return {
            type: this.deviceType,
            orientation: this.orientation,
            touchSupport: this.touchSupport,
            networkCondition: this.networkCondition,
            isOffline: this.isOffline
        };
    }
}

// Initialize mobile framework
const mobileFramework = new MobileFramework();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MobileFramework;
} else {
    window.MobileFramework = MobileFramework;
    window.mobileFramework = mobileFramework;
}