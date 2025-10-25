/**
 * 🌐 Network Discovery Component for Device Management
 * Makes it EXTREMELY easy to discover and add medical devices to PACS
 */

import React, { useState, useEffect } from 'react';
import './NetworkDiscovery.css';

const NetworkDiscovery = ({ onDeviceAdded, onClose }) => {
    const [discoveryMethod, setDiscoveryMethod] = useState('arp'); // 'arp' or 'network'
    const [isScanning, setIsScanning] = useState(false);
    const [discoveredDevices, setDiscoveredDevices] = useState([]);
    const [medicalDevices, setMedicalDevices] = useState([]);
    const [scanResults, setScanResults] = useState(null);
    const [selectedDevices, setSelectedDevices] = useState(new Set());
    
    // Network scan settings
    const [ipRange, setIpRange] = useState('');
    const [customPorts, setCustomPorts] = useState('104,11112,8042,80,443');
    const [maxThreads, setMaxThreads] = useState(50);
    const [suggestions, setSuggestions] = useState(null);

    // Quick add settings
    const [quickAddIP, setQuickAddIP] = useState('');
    const [quickAddName, setQuickAddName] = useState('');
    const [quickAddModality, setQuickAddModality] = useState('other');

    useEffect(() => {
        loadDiscoverySuggestions();
    }, []);

    const loadDiscoverySuggestions = async () => {
        try {
            const response = await fetch('/api/devices/network/discovery-suggestions', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                setSuggestions(data.suggestions);
                
                // Set default IP range to current network
                if (data.suggestions.current_network) {
                    setIpRange(data.suggestions.current_network);
                }
            }
        } catch (error) {
            console.error('Failed to load discovery suggestions:', error);
        }
    };

    const performARPScan = async () => {
        setIsScanning(true);
        setScanResults(null);
        setDiscoveredDevices([]);
        setMedicalDevices([]);

        try {
            const response = await fetch('/api/devices/network/arp-scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                setDiscoveredDevices(data.discovered_devices || []);
                setMedicalDevices(data.medical_devices || []);
                setScanResults({
                    total: data.total_found,
                    medical: data.medical_found,
                    message: data.message
                });
            } else {
                const error = await response.json();
                alert(`ARP scan failed: ${error.error}`);
            }
        } catch (error) {
            console.error('ARP scan error:', error);
            alert('ARP scan failed. Please try again.');
        } finally {
            setIsScanning(false);
        }
    };

    const performNetworkScan = async () => {
        if (!ipRange.trim()) {
            alert('Please enter an IP range to scan');
            return;
        }

        setIsScanning(true);
        setScanResults(null);
        setDiscoveredDevices([]);
        setMedicalDevices([]);

        try {
            const ports = customPorts.split(',').map(p => parseInt(p.trim())).filter(p => p > 0 && p <= 65535);
            
            const response = await fetch('/api/devices/network/discovery-scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    ip_range: ipRange.trim(),
                    ports: ports,
                    max_threads: maxThreads
                })
            });

            if (response.ok) {
                const data = await response.json();
                setDiscoveredDevices(data.discovered_devices || []);
                setMedicalDevices(data.medical_devices || []);
                setScanResults({
                    total: data.total_found,
                    medical: data.medical_found,
                    message: data.message,
                    scan_parameters: data.scan_parameters
                });
            } else {
                const error = await response.json();
                alert(`Network scan failed: ${error.error}`);
            }
        } catch (error) {
            console.error('Network scan error:', error);
            alert('Network scan failed. Please try again.');
        } finally {
            setIsScanning(false);
        }
    };

    const quickAddDevice = async () => {
        if (!quickAddIP.trim()) {
            alert('Please enter an IP address');
            return;
        }

        setIsScanning(true);

        try {
            const response = await fetch('/api/devices/network/quick-add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    ip_address: quickAddIP.trim(),
                    name: quickAddName.trim() || `Device_${quickAddIP.replace(/\./g, '_')}`,
                    modality_type: quickAddModality,
                    manufacturer: 'Unknown',
                    model: 'Unknown',
                    ae_title: `DEV_${quickAddIP.replace(/\./g, '_')}`,
                    department: 'Radiology',
                    location: 'Main Hospital'
                })
            });

            if (response.ok) {
                const data = await response.json();
                alert(`Device added successfully!\n\nName: ${data.device.name}\nIP: ${data.device.ip_address}\nConnectivity: ${data.connectivity_test.message}`);
                
                // Clear form
                setQuickAddIP('');
                setQuickAddName('');
                setQuickAddModality('other');
                
                // Notify parent
                if (onDeviceAdded) {
                    onDeviceAdded(data.device);
                }
            } else {
                const error = await response.json();
                alert(`Quick add failed: ${error.error}`);
            }
        } catch (error) {
            console.error('Quick add error:', error);
            alert('Quick add failed. Please try again.');
        } finally {
            setIsScanning(false);
        }
    };

    const addSelectedDevices = async () => {
        if (selectedDevices.size === 0) {
            alert('Please select devices to add');
            return;
        }

        const devicesToAdd = discoveredDevices.filter((_, index) => selectedDevices.has(index));
        let successCount = 0;
        let errors = [];

        for (const device of devicesToAdd) {
            try {
                const response = await fetch('/api/devices/network/create-from-discovery', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        discovered_device: device,
                        additional_info: {
                            // Use defaults, admin can edit later
                        }
                    })
                });

                if (response.ok) {
                    successCount++;
                    const data = await response.json();
                    if (onDeviceAdded) {
                        onDeviceAdded(data.device);
                    }
                } else {
                    const error = await response.json();
                    errors.push(`${device.ip_address}: ${error.error}`);
                }
            } catch (error) {
                errors.push(`${device.ip_address}: ${error.message}`);
            }
        }

        // Show results
        let message = `Successfully added ${successCount} devices.`;
        if (errors.length > 0) {
            message += `\n\nErrors:\n${errors.join('\n')}`;
        }
        alert(message);

        // Clear selection
        setSelectedDevices(new Set());
    };

    const toggleDeviceSelection = (index) => {
        const newSelection = new Set(selectedDevices);
        if (newSelection.has(index)) {
            newSelection.delete(index);
        } else {
            newSelection.add(index);
        }
        setSelectedDevices(newSelection);
    };

    const selectAllMedicalDevices = () => {
        const medicalIndices = new Set();
        discoveredDevices.forEach((device, index) => {
            if (device.likely_medical_device || device.dicom_capable) {
                medicalIndices.add(index);
            }
        });
        setSelectedDevices(medicalIndices);
    };

    const renderDeviceCard = (device, index) => {
        const isSelected = selectedDevices.has(index);
        const isMedical = device.likely_medical_device || device.dicom_capable;

        return (
            <div 
                key={index} 
                className={`device-card ${isSelected ? 'selected' : ''} ${isMedical ? 'medical-device' : ''}`}
                onClick={() => toggleDeviceSelection(index)}
            >
                <div className="device-header">
                    <div className="device-ip">
                        <strong>{device.ip_address}</strong>
                        {isMedical && <span className="medical-badge">🏥 Medical</span>}
                    </div>
                    <input 
                        type="checkbox" 
                        checked={isSelected}
                        onChange={() => toggleDeviceSelection(index)}
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
                
                <div className="device-details">
                    {device.hostname && (
                        <div className="device-detail">
                            <span className="label">Hostname:</span>
                            <span className="value">{device.hostname}</span>
                        </div>
                    )}
                    
                    {device.mac_address && (
                        <div className="device-detail">
                            <span className="label">MAC:</span>
                            <span className="value">{device.mac_address}</span>
                        </div>
                    )}
                    
                    {device.mac_manufacturer && (
                        <div className="device-detail">
                            <span className="label">Manufacturer:</span>
                            <span className="value">{device.mac_manufacturer}</span>
                        </div>
                    )}
                    
                    {device.open_ports && device.open_ports.length > 0 && (
                        <div className="device-detail">
                            <span className="label">Open Ports:</span>
                            <span className="value">{device.open_ports.join(', ')}</span>
                        </div>
                    )}
                    
                    {device.services && Object.keys(device.services).length > 0 && (
                        <div className="device-detail">
                            <span className="label">Services:</span>
                            <div className="services-list">
                                {Object.entries(device.services).map(([port, service]) => (
                                    <span key={port} className="service-tag">
                                        {port}: {service.service}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="network-discovery">
            <div className="discovery-header">
                <h2>🌐 Network Device Discovery</h2>
                <p>Discover and add medical imaging devices to your PACS server</p>
                {onClose && (
                    <button className="close-btn" onClick={onClose}>✕</button>
                )}
            </div>

            {/* Discovery Method Tabs */}
            <div className="discovery-tabs">
                <button 
                    className={`tab-btn ${discoveryMethod === 'arp' ? 'active' : ''}`}
                    onClick={() => setDiscoveryMethod('arp')}
                >
                    🔍 ARP Table Scan
                </button>
                <button 
                    className={`tab-btn ${discoveryMethod === 'network' ? 'active' : ''}`}
                    onClick={() => setDiscoveryMethod('network')}
                >
                    🌐 Network Range Scan
                </button>
                <button 
                    className={`tab-btn ${discoveryMethod === 'quick' ? 'active' : ''}`}
                    onClick={() => setDiscoveryMethod('quick')}
                >
                    ⚡ Quick Add by IP
                </button>
            </div>

            {/* ARP Scan Tab */}
            {discoveryMethod === 'arp' && (
                <div className="discovery-content">
                    <div className="scan-section">
                        <h3>🔍 ARP Table Scan</h3>
                        <p>Scan the system's ARP table to find all devices that have recently communicated on the network.</p>
                        
                        <div className="scan-controls">
                            <button 
                                className="scan-btn primary"
                                onClick={performARPScan}
                                disabled={isScanning}
                            >
                                {isScanning ? '🔄 Scanning ARP Table...' : '🔍 Scan ARP Table'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Network Scan Tab */}
            {discoveryMethod === 'network' && (
                <div className="discovery-content">
                    <div className="scan-section">
                        <h3>🌐 Network Range Scan</h3>
                        <p>Scan a specific IP range to discover devices and check for open ports.</p>
                        
                        <div className="scan-form">
                            <div className="form-group">
                                <label>IP Range:</label>
                                <input
                                    type="text"
                                    value={ipRange}
                                    onChange={(e) => setIpRange(e.target.value)}
                                    placeholder="192.168.1.0/24 or 192.168.1.1-192.168.1.254"
                                    className="ip-range-input"
                                />
                                
                                {suggestions && suggestions.suggested_ranges && (
                                    <div className="suggestions">
                                        <span>Suggestions:</span>
                                        {suggestions.suggested_ranges.map((range, index) => (
                                            <button
                                                key={index}
                                                className="suggestion-btn"
                                                onClick={() => setIpRange(range)}
                                            >
                                                {range}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                            
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Ports to Scan:</label>
                                    <input
                                        type="text"
                                        value={customPorts}
                                        onChange={(e) => setCustomPorts(e.target.value)}
                                        placeholder="104,11112,8042,80,443"
                                    />
                                </div>
                                
                                <div className="form-group">
                                    <label>Max Threads:</label>
                                    <input
                                        type="number"
                                        value={maxThreads}
                                        onChange={(e) => setMaxThreads(parseInt(e.target.value) || 50)}
                                        min="1"
                                        max="200"
                                    />
                                </div>
                            </div>
                        </div>
                        
                        <div className="scan-controls">
                            <button 
                                className="scan-btn primary"
                                onClick={performNetworkScan}
                                disabled={isScanning || !ipRange.trim()}
                            >
                                {isScanning ? '🔄 Scanning Network...' : '🌐 Start Network Scan'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Quick Add Tab */}
            {discoveryMethod === 'quick' && (
                <div className="discovery-content">
                    <div className="scan-section">
                        <h3>⚡ Quick Add Device by IP</h3>
                        <p>Quickly add a device if you know its IP address.</p>
                        
                        <div className="quick-add-form">
                            <div className="form-group">
                                <label>IP Address:</label>
                                <input
                                    type="text"
                                    value={quickAddIP}
                                    onChange={(e) => setQuickAddIP(e.target.value)}
                                    placeholder="192.168.1.100"
                                    className="ip-input"
                                />
                            </div>
                            
                            <div className="form-group">
                                <label>Device Name (optional):</label>
                                <input
                                    type="text"
                                    value={quickAddName}
                                    onChange={(e) => setQuickAddName(e.target.value)}
                                    placeholder="GE Ultrasound Machine"
                                />
                            </div>
                            
                            <div className="form-group">
                                <label>Modality Type:</label>
                                <select
                                    value={quickAddModality}
                                    onChange={(e) => setQuickAddModality(e.target.value)}
                                >
                                    <option value="ultrasound">Ultrasound</option>
                                    <option value="xray">X-Ray</option>
                                    <option value="ct">CT Scan</option>
                                    <option value="mri">MRI</option>
                                    <option value="mammography">Mammography</option>
                                    <option value="bone_density">Bone Density</option>
                                    <option value="other">Other</option>
                                </select>
                            </div>
                        </div>
                        
                        <div className="scan-controls">
                            <button 
                                className="scan-btn primary"
                                onClick={quickAddDevice}
                                disabled={isScanning || !quickAddIP.trim()}
                            >
                                {isScanning ? '🔄 Adding Device...' : '⚡ Quick Add Device'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Scan Results */}
            {scanResults && (
                <div className="scan-results">
                    <div className="results-header">
                        <h3>📊 Scan Results</h3>
                        <div className="results-summary">
                            <span className="result-stat">
                                <strong>{scanResults.total}</strong> devices found
                            </span>
                            <span className="result-stat medical">
                                <strong>{scanResults.medical}</strong> likely medical devices
                            </span>
                        </div>
                    </div>
                    
                    {discoveredDevices.length > 0 && (
                        <div className="devices-section">
                            <div className="devices-controls">
                                <button 
                                    className="control-btn"
                                    onClick={selectAllMedicalDevices}
                                >
                                    🏥 Select All Medical Devices
                                </button>
                                
                                <button 
                                    className="control-btn primary"
                                    onClick={addSelectedDevices}
                                    disabled={selectedDevices.size === 0}
                                >
                                    ➕ Add Selected Devices ({selectedDevices.size})
                                </button>
                            </div>
                            
                            <div className="devices-grid">
                                {discoveredDevices.map((device, index) => renderDeviceCard(device, index))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* South African Context */}
            <div className="sa-context">
                <div className="sa-flag">🇿🇦</div>
                <div className="sa-info">
                    <strong>South African Medical Standards</strong>
                    <p>This tool helps you easily discover and add medical imaging equipment commonly used in SA healthcare facilities including GE, Philips, Siemens, Mindray, and Samsung devices.</p>
                </div>
            </div>
        </div>
    );
};

export default NetworkDiscovery;