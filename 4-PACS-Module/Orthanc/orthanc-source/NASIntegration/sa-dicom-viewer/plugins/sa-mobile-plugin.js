/**
 * 🇿🇦 SA Mobile Optimization Plugin for OHIF
 * 
 * Optimizes OHIF viewer for mobile devices and South African network conditions
 */

const SA_MOBILE_PLUGIN = {
  id: '@sa-medical/extension-mobile-optimization',
  version: '1.0.0',

  /**
   * Mobile Interface Optimizations
   */
  mobileInterface: {
    /**
     * Touch gesture handlers for medical image manipulation
     */
    touchGestures: {
      setupGestures: (element) => {
        let initialDistance = 0;
        let initialScale = 1;
        let lastTap = 0;
        let touchStartTime = 0;
        let touchStartPos = { x: 0, y: 0 };

        // Pinch to zoom
        element.addEventListener('touchstart', (e) => {
          touchStartTime = Date.now();
          
          if (e.touches.length === 2) {
            initialDistance = this.getDistance(e.touches[0], e.touches[1]);
            initialScale = this.getCurrentScale(element);
          } else if (e.touches.length === 1) {
            touchStartPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
          }
        });

        element.addEventListener('touchmove', (e) => {
          e.preventDefault(); // Prevent default mobile behaviors
          
          if (e.touches.length === 2) {
            // Pinch zoom
            const currentDistance = this.getDistance(e.touches[0], e.touches[1]);
            const scale = (currentDistance / initialDistance) * initialScale;
            this.applyZoom(element, scale);
          } else if (e.touches.length === 1) {
            // Pan gesture
            const deltaX = e.touches[0].clientX - touchStartPos.x;
            const deltaY = e.touches[0].clientY - touchStartPos.y;
            this.applyPan(element, deltaX, deltaY);
          }
        });

        // Double-tap to fit
        element.addEventListener('touchend', (e) => {
          const touchEndTime = Date.now();
          const touchDuration = touchEndTime - touchStartTime;
          
          if (touchDuration < 200 && e.changedTouches.length === 1) {
            const currentTime = Date.now();
            const tapDelay = currentTime - lastTap;
            
            if (tapDelay < 300 && tapDelay > 0) {
              // Double tap detected
              this.fitToWindow(element);
            }
            
            lastTap = currentTime;
          }
        });
      },

      getDistance: (touch1, touch2) => {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
      },

      getCurrentScale: (element) => {
        const transform = element.style.transform;
        const scaleMatch = transform.match(/scale\(([^)]+)\)/);
        return scaleMatch ? parseFloat(scaleMatch[1]) : 1;
      },

      applyZoom: (element, scale) => {
        element.style.transform = `scale(${Math.max(0.5, Math.min(5, scale))})`;
      },

      applyPan: (element, deltaX, deltaY) => {
        const currentTransform = element.style.transform;
        const translateMatch = currentTransform.match(/translate\(([^)]+)\)/);
        
        let currentX = 0, currentY = 0;
        if (translateMatch) {
          const values = translateMatch[1].split(',');
          currentX = parseFloat(values[0]) || 0;
          currentY = parseFloat(values[1]) || 0;
        }
        
        element.style.transform += ` translate(${currentX + deltaX}px, ${currentY + deltaY}px)`;
      },

      fitToWindow: (element) => {
        element.style.transform = 'scale(1) translate(0px, 0px)';
      }
    },

    /**
     * Mobile UI adaptations
     */
    mobileUI: {
      adaptLayout: () => {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
          // Hide less critical UI elements on mobile
          const elementsToHide = [
            '.ohif-sidebar',
            '.study-browser',
            '.measurement-panel'
          ];
          
          elementsToHide.forEach(selector => {
            const element = document.querySelector(selector);
            if (element) {
              element.style.display = 'none';
            }
          });

          // Add mobile-specific classes
          document.body.classList.add('sa-mobile-view');
          
          // Adjust tool panel for mobile
          this.createMobileToolPanel();
        }
      },

      createMobileToolPanel: () => {
        const toolPanel = document.createElement('div');
        toolPanel.className = 'sa-mobile-tool-panel';
        toolPanel.innerHTML = `
          <div class="mobile-tools">
            <button class="tool-btn" data-tool="zoom">🔍</button>
            <button class="tool-btn" data-tool="pan">✋</button>
            <button class="tool-btn" data-tool="wwwc">🎚️</button>
            <button class="tool-btn" data-tool="measure">📏</button>
            <button class="tool-btn" data-tool="annotate">✏️</button>
            <button class="tool-btn" data-tool="fullscreen">📱</button>
          </div>
        `;
        
        document.body.appendChild(toolPanel);
        
        // Add tool event handlers
        toolPanel.addEventListener('click', (e) => {
          if (e.target.classList.contains('tool-btn')) {
            const tool = e.target.dataset.tool;
            this.activateMobileTool(tool);
          }
        });
      },

      activateMobileTool: (tool) => {
        // Remove active class from all tools
        document.querySelectorAll('.tool-btn').forEach(btn => {
          btn.classList.remove('active');
        });
        
        // Add active class to selected tool
        document.querySelector(`[data-tool="${tool}"]`).classList.add('active');
        
        // Activate the tool in OHIF
        switch (tool) {
          case 'zoom':
            window.ohif?.tools?.setActiveTool('Zoom');
            break;
          case 'pan':
            window.ohif?.tools?.setActiveTool('Pan');
            break;
          case 'wwwc':
            window.ohif?.tools?.setActiveTool('Wwwc');
            break;
          case 'measure':
            window.ohif?.tools?.setActiveTool('Length');
            break;
          case 'annotate':
            window.ohif?.tools?.setActiveTool('ArrowAnnotate');
            break;
          case 'fullscreen':
            this.toggleFullscreen();
            break;
        }
      },

      toggleFullscreen: () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen();
        } else {
          document.exitFullscreen();
        }
      }
    }
  },

  /**
   * Network Optimization for SA Conditions
   */
  networkOptimization: {
    /**
     * Progressive image loading for 3G/4G networks
     */
    progressiveLoading: {
      setupProgressiveLoad: () => {
        // Detect connection speed
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        let quality = 'high';
        
        if (connection) {
          const effectiveType = connection.effectiveType;
          switch (effectiveType) {
            case 'slow-2g':
            case '2g':
              quality = 'low';
              break;
            case '3g':
              quality = 'medium';
              break;
            case '4g':
            default:
              quality = 'high';
              break;
          }
        }
        
        this.setImageQuality(quality);
        this.setupQualityToggle();
      },

      setImageQuality: (quality) => {
        const qualitySettings = {
          low: { resolution: 512, compression: 0.6 },
          medium: { resolution: 1024, compression: 0.8 },
          high: { resolution: 2048, compression: 1.0 }
        };
        
        const settings = qualitySettings[quality];
        
        // Apply to OHIF configuration
        if (window.ohif && window.ohif.configuration) {
          window.ohif.configuration.imageQuality = settings;
        }
        
        // Update UI indicator
        this.updateQualityIndicator(quality);
      },

      setupQualityToggle: () => {
        const qualityToggle = document.createElement('div');
        qualityToggle.className = 'sa-quality-toggle';
        qualityToggle.innerHTML = `
          <div class="quality-selector">
            <span class="quality-label">Quality:</span>
            <select id="quality-select">
              <option value="low">Low (512p) - 3G Friendly</option>
              <option value="medium">Medium (1024p) - 4G</option>
              <option value="high">High (2048p) - WiFi</option>
            </select>
          </div>
        `;
        
        document.body.appendChild(qualityToggle);
        
        document.getElementById('quality-select').addEventListener('change', (e) => {
          this.setImageQuality(e.target.value);
          this.reloadCurrentStudy();
        });
      },

      updateQualityIndicator: (quality) => {
        const colors = { low: '#ff6b6b', medium: '#ffd93d', high: '#51cf66' };
        const indicator = document.querySelector('.quality-selector');
        if (indicator) {
          indicator.style.borderLeft = `4px solid ${colors[quality]}`;
        }
      },

      reloadCurrentStudy: () => {
        // Trigger study reload with new quality settings
        if (window.ohif && window.ohif.viewer) {
          window.ohif.viewer.reload();
        }
      }
    },

    /**
     * Bandwidth monitoring and adaptive loading
     */
    bandwidthMonitoring: {
      startMonitoring: () => {
        setInterval(() => {
          this.measureBandwidth();
        }, 30000); // Check every 30 seconds
      },

      measureBandwidth: async () => {
        const startTime = Date.now();
        const testImage = new Image();
        const testSize = 50000; // 50KB test image
        
        testImage.onload = () => {
          const endTime = Date.now();
          const duration = (endTime - startTime) / 1000; // seconds
          const bitsLoaded = testSize * 8;
          const speedBps = bitsLoaded / duration;
          const speedKbps = speedBps / 1024;
          
          this.adaptToSpeed(speedKbps);
        };
        
        testImage.src = `/api/bandwidth-test?size=${testSize}&t=${Date.now()}`;
      },

      adaptToSpeed: (speedKbps) => {
        let newQuality;
        
        if (speedKbps < 100) { // Very slow
          newQuality = 'low';
          this.showSlowConnectionWarning();
        } else if (speedKbps < 500) { // Moderate
          newQuality = 'medium';
        } else { // Fast
          newQuality = 'high';
        }
        
        this.progressiveLoading.setImageQuality(newQuality);
      },

      showSlowConnectionWarning: () => {
        const warning = document.createElement('div');
        warning.className = 'sa-connection-warning';
        warning.innerHTML = `
          <div class="warning-content">
            ⚠️ Slow connection detected. Switching to low quality mode for better performance.
            <button onclick="this.parentElement.parentElement.remove()">✕</button>
          </div>
        `;
        
        document.body.appendChild(warning);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
          if (warning.parentElement) {
            warning.remove();
          }
        }, 5000);
      }
    }
  },

  /**
   * Offline Capabilities
   */
  offlineSupport: {
    setupOfflineStorage: () => {
      // Register service worker for offline caching
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw-sa-medical.js')
          .then(registration => {
            console.log('SA Medical SW registered:', registration);
          })
          .catch(error => {
            console.log('SA Medical SW registration failed:', error);
          });
      }
    },

    cacheCurrentStudy: async (studyData) => {
      if ('caches' in window) {
        const cache = await caches.open('sa-medical-studies');
        
        // Cache study metadata and images
        const studyKey = `study-${studyData.studyInstanceUID}`;
        await cache.put(studyKey, new Response(JSON.stringify(studyData)));
        
        // Cache image frames
        for (const series of studyData.series) {
          for (const instance of series.instances) {
            try {
              await cache.add(instance.imageUrl);
            } catch (error) {
              console.warn('Failed to cache image:', instance.imageUrl);
            }
          }
        }
      }
    },

    showOfflineIndicator: () => {
      const indicator = document.createElement('div');
      indicator.className = 'sa-offline-indicator';
      indicator.innerHTML = '📡 Offline Mode - Limited functionality';
      
      document.body.appendChild(indicator);
      
      window.addEventListener('online', () => {
        indicator.remove();
      });
    }
  },

  /**
   * Plugin initialization
   */
  preRegistration: ({ servicesManager, configuration }) => {
    console.log('🇿🇦 SA Mobile Optimization Plugin initialized');
    
    // Setup mobile optimizations
    this.mobileInterface.mobileUI.adaptLayout();
    
    // Setup network optimization
    this.networkOptimization.progressiveLoading.setupProgressiveLoad();
    this.networkOptimization.bandwidthMonitoring.startMonitoring();
    
    // Setup offline support
    this.offlineSupport.setupOfflineStorage();
    
    // Listen for network changes
    window.addEventListener('offline', () => {
      this.offlineSupport.showOfflineIndicator();
    });
    
    // Responsive layout adjustments
    window.addEventListener('resize', () => {
      this.mobileInterface.mobileUI.adaptLayout();
    });
    
    // Export to global scope for access
    window.saMobileOptimization = {
      interface: this.mobileInterface,
      network: this.networkOptimization,
      offline: this.offlineSupport
    };
  }
};

export default SA_MOBILE_PLUGIN;
