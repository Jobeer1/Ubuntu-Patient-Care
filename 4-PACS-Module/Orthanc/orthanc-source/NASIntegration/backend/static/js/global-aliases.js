/* 🇿🇦 Global Function Aliases - Backward Compatibility Layer */

// This file provides global function aliases for backward compatibility
// with existing HTML onclick handlers and function calls

// Initialize the page when all modules are loaded
document.addEventListener('DOMContentLoaded', function() {
    // Ensure NASIntegration object exists
    if (typeof window.NASIntegration !== 'undefined') {
        console.log('🏥 NAS Medical Image Management System Loaded - All Modules Ready');
        
        // Initialize page if core module is available
        if (window.NASIntegration.core && window.NASIntegration.core.initializePage) {
            window.NASIntegration.core.initializePage();
        }
        
        // Load network settings if available
        if (window.NASIntegration.network && window.NASIntegration.network.loadNetworkSettings) {
            window.NASIntegration.network.loadNetworkSettings();
        }
    }
});

// Global function aliases for backward compatibility with HTML onclick handlers

// Orthanc functions
function connectToOrthanc() { return window.NASIntegration.orthanc?.connectToOrthanc(); }
function testOrthancConnection() { return window.NASIntegration.orthanc?.checkOrthancStatus(); }
function connectOrthanc() { return window.NASIntegration.orthanc?.connectToOrthanc(); }

// Indexing functions
function startIndexing() { return window.NASIntegration.orthanc?.startIndexing(); }
function getIndexStatus() { return window.NASIntegration.orthanc?.checkIndexStatus(); }
function stopIndexing() { return window.NASIntegration.orthanc?.stopIndexing(); }

// Patient search functions
function searchPatients() { return window.NASIntegration.orthanc?.searchPatients(); }
function clearSearchForm() { return window.NASIntegration.orthanc?.clearSearchForm(); }
function generateShareLink() { return window.NASIntegration.orthanc?.generateShareLink(); }

// Network discovery functions
function getArpTable() { return window.NASIntegration.network?.getArpTable(); }
function refreshArpTable() { return window.NASIntegration.network?.refreshArpTable(); }
function pingRange() { return window.NASIntegration.network?.pingRange(); }
function pingSingleDevice() { return window.NASIntegration.network?.pingSingleDevice(); }
function enhancedDiscover() { return window.NASIntegration.network?.enhancedDiscover(); }
function startNetworkScan() { return window.NASIntegration.network?.startNetworkScan(); }

// Storage functions
function configureStorage() { return window.NASIntegration.network?.configureStorage(); }
function testStoragePaths() { return window.NASIntegration.network?.testStoragePaths(); }

// Device management functions
function renameDevice(ip, hostname) { return window.NASIntegration.devices?.renameDevice(ip, hostname); }
function pingDevice(ip) { return window.NASIntegration.devices?.pingDevice(ip); }
function connectToDevice(ip) { return window.NASIntegration.devices?.connectToDevice(ip); }
function removeDevice(ip, hostname) { return window.NASIntegration.devices?.removeDevice(ip, hostname); }
function testDeviceConnectivity(ip) { return window.NASIntegration.devices?.testDeviceConnectivity(ip); }

// Settings functions
function saveNetworkSettings() { return window.NASIntegration.network?.saveNetworkSettings(); }

// UI functions (these are now handled by the modular system but keep aliases for any remaining references)
function showLoading(show, message) { return window.NASIntegration.core?.showLoading(show, message); }
function showMessage(message, type) { return window.NASIntegration.core?.showMessage(message, type); }
function toggleOfflineDevices() { return window.NASIntegration.ui?.toggleOfflineDevices(); }

console.log('✅ Global function aliases loaded for backward compatibility');
