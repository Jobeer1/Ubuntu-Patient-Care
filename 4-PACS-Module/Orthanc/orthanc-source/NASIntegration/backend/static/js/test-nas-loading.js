/**
 * Test script to verify NAS configuration loading on page load
 * This should be included AFTER all other scripts
 */

console.log('🧪 NAS Loading Test - Checking modules...');

// Check if core dependencies are loaded
const checks = {
    'window.NASIntegration.core': typeof window?.NASIntegration?.core,
    'window.showNASConfigurationModal': typeof window.showNASConfigurationModal,
    'window.initializeNASConfigurationUI': typeof window.initializeNASConfigurationUI,
    'window.loadCurrentNASConfig': typeof window.loadCurrentNASConfig,
    'document.getElementById': typeof document.getElementById,
};

console.log('📋 Module availability checks:', checks);

// Check the HTML element exists
const nasElement = document.getElementById('dashboardNasDevices');
console.log('📍 NAS Dashboard Element found:', !!nasElement);
if (nasElement) {
    console.log('   Current content:', nasElement.textContent);
}

// Wait a bit for all modules to be fully loaded
setTimeout(() => {
    console.log('⏱️ Running deferred NAS config load after 2 seconds...');
    
    // Try to load current NAS config
    if (typeof window.loadCurrentNASConfig === 'function') {
        console.log('✅ loadCurrentNASConfig is available - calling it');
        try {
            window.loadCurrentNASConfig();
        } catch (e) {
            console.error('❌ Error calling loadCurrentNASConfig:', e);
        }
    } else if (typeof window.initializeNASConfigurationUI === 'function') {
        console.log('✅ initializeNASConfigurationUI is available - calling it');
        try {
            window.initializeNASConfigurationUI();
        } catch (e) {
            console.error('❌ Error calling initializeNASConfigurationUI:', e);
        }
    } else {
        console.warn('⚠️ NAS functions not available in window scope');
        const nasKeys = Object.keys(window).filter(k => k.toLowerCase().includes('nas'));
        console.warn('  Available NAS-related keys in window:', nasKeys);
    }
    
    // Try to refresh dashboard with NAS data
    if (typeof refreshDashboard === 'function') {
        console.log('✅ refreshDashboard is available - calling it');
        try {
            refreshDashboard();
        } catch (e) {
            console.error('❌ Error calling refreshDashboard:', e);
        }
    }
    
    // Show final status
    const nasElement2 = document.getElementById('dashboardNasDevices');
    if (nasElement2) {
        console.log('📍 NAS Dashboard content after load:', nasElement2.textContent);
    }
    
}, 2000);

console.log('✨ NAS Loading Test Complete - Check browser console for details');

