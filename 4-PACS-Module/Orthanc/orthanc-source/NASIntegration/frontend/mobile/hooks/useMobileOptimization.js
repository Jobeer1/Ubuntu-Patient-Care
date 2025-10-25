/**
 * Mobile Optimization Hook for South African Healthcare
 * Handles device detection, network conditions, and performance optimization
 */

import { useState, useEffect, useCallback } from 'react';

export const useMobileOptimization = () => {
    const [deviceInfo, setDeviceInfo] = useState({
        type: 'desktop',
        orientation: 'portrait',
        touchSupport: false,
        networkCondition: 'unknown',
        isOffline: false,
        isLowBandwidth: false,
        batteryLevel: null,
        isCharging: null
    });

    const [performanceMetrics, setPerformanceMetrics] = useState({
        memoryUsage: null,
        renderTime: null,
        networkLatency: null
    });

    // Detect device capabilities
    const detectDeviceCapabilities = useCallback(() => {
        const userAgent = navigator.userAgent.toLowerCase();
        const screenWidth = window.screen.width;
        const touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        let deviceType = 'desktop';
        if (userAgent.includes('mobile') || screenWidth < 768) {
            deviceType = 'mobile';
        } else if (userAgent.includes('tablet') || (screenWidth >= 768 && screenWidth < 1024)) {
            deviceType = 'tablet';
        }

        const orientation = window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
        const isOffline = !navigator.onLine;

        return {
            type: deviceType,
            orientation,
            touchSupport,
            isOffline,
            userAgent
        };
    }, []);

    // Detect network conditions
    const detectNetworkConditions = useCallback(() => {
        if ('connection' in navigator) {
            const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            const effectiveType = connection.effectiveType || 'unknown';
            const isLowBandwidth = effectiveType === '2g' || effectiveType === 'slow-2g';
            
            return {
                networkCondition: effectiveType,
                isLowBandwidth,
                downlink: connection.downlink,
                rtt: connection.rtt,
                saveData: connection.saveData
            };
        }
        
        return {
            networkCondition: 'unknown',
            isLowBandwidth: false,
            downlink: null,
            rtt: null,
            saveData: false
        };
    }, []);

    // Detect battery status
    const detectBatteryStatus = useCallback(async () => {
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                return {
                    batteryLevel: battery.level,
                    isCharging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            } catch (error) {
                console.warn('Battery API not available:', error);
            }
        }
        
        return {
            batteryLevel: null,
            isCharging: null,
            chargingTime: null,
            dischargingTime: null
        };
    }, []);

    // Measure performance metrics
    const measurePerformance = useCallback(() => {
        const metrics = {};
        
        // Memory usage (if available)
        if ('memory' in performance) {
            metrics.memoryUsage = {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            };
        }
        
        // Navigation timing
        if ('navigation' in performance) {
            const navTiming = performance.getEntriesByType('navigation')[0];
            if (navTiming) {
                metrics.renderTime = navTiming.loadEventEnd - navTiming.navigationStart;
                metrics.networkLatency = navTiming.responseStart - navTiming.requestStart;
            }
        }
        
        return metrics;
    }, []);

    // South African specific optimizations
    const applySAOptimizations = useCallback((deviceInfo) => {
        const optimizations = {
            language: 'en-ZA', // Default to South African English
            timezone: 'Africa/Johannesburg',
            currency: 'ZAR',
            dateFormat: 'DD/MM/YYYY',
            timeFormat: '24h'
        };

        // Detect preferred language
        const browserLang = navigator.language || navigator.userLanguage;
        if (browserLang.startsWith('af')) {
            optimizations.language = 'af';
        } else if (browserLang.startsWith('zu')) {
            optimizations.language = 'zu';
        }

        // Apply network optimizations for SA conditions
        if (deviceInfo.isLowBandwidth) {
            optimizations.imageQuality = 'low';
            optimizations.preloadImages = false;
            optimizations.enableCompression = true;
        } else {
            optimizations.imageQuality = 'high';
            optimizations.preloadImages = true;
            optimizations.enableCompression = false;
        }

        // Battery optimizations
        if (deviceInfo.batteryLevel && deviceInfo.batteryLevel < 0.2 && !deviceInfo.isCharging) {
            optimizations.powerSaveMode = true;
            optimizations.reduceAnimations = true;
            optimizations.lowerRefreshRate = true;
        }

        return optimizations;
    }, []);

    // Initialize device detection
    useEffect(() => {
        const updateDeviceInfo = async () => {
            const deviceCapabilities = detectDeviceCapabilities();
            const networkConditions = detectNetworkConditions();
            const batteryStatus = await detectBatteryStatus();
            const performance = measurePerformance();

            const newDeviceInfo = {
                ...deviceCapabilities,
                ...networkConditions,
                ...batteryStatus
            };

            setDeviceInfo(newDeviceInfo);
            setPerformanceMetrics(performance);

            // Apply SA-specific optimizations
            const saOptimizations = applySAOptimizations(newDeviceInfo);
            
            // Store optimizations in localStorage for persistence
            localStorage.setItem('sa-optimizations', JSON.stringify(saOptimizations));
            
            // Apply CSS classes for optimization
            document.body.className = document.body.className.replace(/device-\w+/g, '');
            document.body.classList.add(`device-${newDeviceInfo.type}`);
            
            if (newDeviceInfo.isLowBandwidth) {
                document.body.classList.add('low-bandwidth');
            }
            
            if (saOptimizations.powerSaveMode) {
                document.body.classList.add('power-save');
            }
        };

        updateDeviceInfo();

        // Set up event listeners
        const handleOrientationChange = () => {
            setDeviceInfo(prev => ({
                ...prev,
                orientation: window.innerHeight > window.innerWidth ? 'portrait' : 'landscape'
            }));
        };

        const handleOnlineStatusChange = () => {
            setDeviceInfo(prev => ({
                ...prev,
                isOffline: !navigator.onLine
            }));
        };

        const handleNetworkChange = () => {
            const networkConditions = detectNetworkConditions();
            setDeviceInfo(prev => ({
                ...prev,
                ...networkConditions
            }));
        };

        // Add event listeners
        window.addEventListener('orientationchange', handleOrientationChange);
        window.addEventListener('resize', handleOrientationChange);
        window.addEventListener('online', handleOnlineStatusChange);
        window.addEventListener('offline', handleOnlineStatusChange);

        if ('connection' in navigator) {
            navigator.connection.addEventListener('change', handleNetworkChange);
        }

        // Cleanup
        return () => {
            window.removeEventListener('orientationchange', handleOrientationChange);
            window.removeEventListener('resize', handleOrientationChange);
            window.removeEventListener('online', handleOnlineStatusChange);
            window.removeEventListener('offline', handleOnlineStatusChange);
            
            if ('connection' in navigator) {
                navigator.connection.removeEventListener('change', handleNetworkChange);
            }
        };
    }, [detectDeviceCapabilities, detectNetworkConditions, detectBatteryStatus, measurePerformance, applySAOptimizations]);

    // Optimization utilities
    const optimizeImageLoading = useCallback((imageUrl, options = {}) => {
        const { quality = 'auto', format = 'auto' } = options;
        
        if (deviceInfo.isLowBandwidth || deviceInfo.type === 'mobile') {
            // Return optimized image URL for low bandwidth
            const params = new URLSearchParams();
            params.append('quality', quality === 'auto' ? '60' : quality);
            params.append('format', format === 'auto' ? 'webp' : format);
            params.append('width', deviceInfo.type === 'mobile' ? '800' : '1200');
            
            return `${imageUrl}?${params.toString()}`;
        }
        
        return imageUrl;
    }, [deviceInfo]);

    const shouldPreloadContent = useCallback(() => {
        return !deviceInfo.isLowBandwidth && 
               !deviceInfo.isOffline && 
               (deviceInfo.batteryLevel === null || deviceInfo.batteryLevel > 0.3);
    }, [deviceInfo]);

    const getOptimalChunkSize = useCallback(() => {
        if (deviceInfo.isLowBandwidth) return 1024; // 1KB chunks
        if (deviceInfo.type === 'mobile') return 8192; // 8KB chunks
        return 32768; // 32KB chunks for desktop/tablet
    }, [deviceInfo]);

    // South African healthcare specific utilities
    const formatSAPhoneNumber = useCallback((phoneNumber) => {
        // Format to +27 format
        const cleaned = phoneNumber.replace(/\D/g, '');
        if (cleaned.startsWith('27')) {
            return `+${cleaned}`;
        } else if (cleaned.startsWith('0')) {
            return `+27${cleaned.substring(1)}`;
        }
        return `+27${cleaned}`;
    }, []);

    const formatSACurrency = useCallback((amount) => {
        return new Intl.NumberFormat('en-ZA', {
            style: 'currency',
            currency: 'ZAR'
        }).format(amount);
    }, []);

    const formatSADate = useCallback((date) => {
        return new Intl.DateTimeFormat('en-ZA', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            timeZone: 'Africa/Johannesburg'
        }).format(new Date(date));
    }, []);

    return {
        deviceInfo,
        performanceMetrics,
        optimizeImageLoading,
        shouldPreloadContent,
        getOptimalChunkSize,
        formatSAPhoneNumber,
        formatSACurrency,
        formatSADate,
        
        // Convenience getters
        isMobile: deviceInfo.type === 'mobile',
        isTablet: deviceInfo.type === 'tablet',
        isDesktop: deviceInfo.type === 'desktop',
        isTouchDevice: deviceInfo.touchSupport,
        isLowBandwidth: deviceInfo.isLowBandwidth,
        isOffline: deviceInfo.isOffline,
        isPortrait: deviceInfo.orientation === 'portrait',
        isLandscape: deviceInfo.orientation === 'landscape'
    };
};