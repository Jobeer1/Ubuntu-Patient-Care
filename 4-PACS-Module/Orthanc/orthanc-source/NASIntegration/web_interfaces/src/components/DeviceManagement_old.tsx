import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Activity, Monitor } from 'lucide-react';

interface Device {
  id: string;
  name: string;
  ip_address: string;
  mac_address?: string;
  modality_type: string;
  manufacturer: string;
  status: 'online' | 'offline' | 'unknown';
  open_ports?: number[];
  services?: Record<number, any>;
}

interface DiscoveredDevice {
  ip_address: string;
  mac_address?: string;
  hostname?: string;
  open_ports: number[];
  services: Record<number, any>;
  likely_medical_device?: boolean;
  dicom_capable?: boolean;
  confidence_score?: number;
  suspected_manufacturer?: string;
  mac_manufacturer?: string;
  dicom_echo_result?: {
    success: boolean;
    ae_title?: string;
    description?: string;
  };
  reachable: boolean;
  discovered_at?: string;
}

const DeviceManagement: React.FC = () => {
  const [discoveredDevices, setDiscoveredDevices] = useState<DiscoveredDevice[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [ipRange, setIpRange] = useState('192.168.1.0/24');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/devices');
      if (!response.ok) throw new Error('Failed to load devices');
      
      const data = await response.json();
      setDevices(data.devices || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const startNetworkScan = async () => {
    if (!ipRange.trim()) {
      setError('Please enter an IP range to scan');
      return;
    }

    try {
      setIsScanning(true);
      setError(null);
      setScanResults(null);
      setDiscoveredDevices([]);

      const response = await fetch('/api/devices/network/discovery-scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ip_range: ipRange,
          ports: [104, 11112, 8042, 80, 443, 22],
          max_threads: 50
        })
      });

      if (!response.ok) {
        throw new Error(`Scan failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        setDiscoveredDevices(result.discovered_devices || []);
        setScanResults(result);
      } else {
        throw new Error(result.error || 'Scan failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network scan failed');
    } finally {
      setIsScanning(false);
    }
  };

  const performDicomPing = async (device: DiscoveredDevice) => {
    try {
      const response = await fetch('/api/devices/network/test-dicom', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ip_address: device.ip_address,
          port: 104, // Standard DICOM port
          ae_title: 'PACS_TEST'
        })
      });

      if (!response.ok) throw new Error('DICOM ping failed');

      const result = await response.json();
      
      // Update the device with DICOM test results
      const updatedDevices = discoveredDevices.map(d => 
        d.ip_address === device.ip_address 
          ? { ...d, dicom_echo_result: result }
          : d
      );
      setDiscoveredDevices(updatedDevices);
      
    } catch (err) {
      console.error('DICOM ping error:', err);
    }
  };

  const calculateConfidenceScore = (device: DiscoveredDevice): number => {
    let score = 0;
    
    // DICOM ports (+40 points)
    if (device.open_ports.includes(104)) score += 40;
    if (device.open_ports.includes(11112)) score += 30;
    
    // Medical device indicators (+30 points)
    if (device.likely_medical_device) score += 30;
    if (device.dicom_capable) score += 25;
    
    // Manufacturer detection (+20 points)
    if (device.suspected_manufacturer && device.suspected_manufacturer !== 'Unknown') score += 20;
    if (device.mac_manufacturer && ['ge', 'philips', 'siemens', 'mindray', 'samsung'].some(vendor => 
        device.mac_manufacturer!.toLowerCase().includes(vendor))) score += 15;
    
    // DICOM echo test (+50 points if successful)
    if (device.dicom_echo_result?.success) score += 50;
    
    // Hostname analysis (+10 points)
    if (device.hostname && ['ge', 'philips', 'siemens', 'mindray', 'samsung'].some(vendor => 
        device.hostname!.toLowerCase().includes(vendor))) score += 10;
    
    return Math.min(score, 100); // Cap at 100%
  };

  const getConfidenceColor = (score: number): string => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    if (score >= 40) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };
    try {
      const deviceName = prompt('Enter device name:');
      if (!deviceName) return;

      const modalityType = prompt('Enter modality type (e.g., CT, MRI, X-RAY):');
      if (!modalityType) return;

      const response = await fetch('/api/devices/network/create-from-discovery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          discovered_device: discoveredDevice,
          additional_info: {
            name: deviceName,
            modality_type: modalityType.toUpperCase(),
            manufacturer: 'Unknown'
          }
        })
      });

      if (!response.ok) throw new Error('Failed to create device');

      const result = await response.json();
      if (result.success) {
        alert('Device created successfully!');
        loadDevices(); // Reload devices list
      } else {
        throw new Error(result.error || 'Failed to create device');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create device');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-600';
      case 'offline': return 'text-red-600';
      default: return 'text-yellow-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return <CheckCircle className="w-4 h-4" />;
      case 'offline': return <XCircle className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Device Management</h1>
              <p className="text-gray-600 mt-1">Manage medical imaging devices and equipment</p>
            </div>
            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 transition-colors">
              <Plus className="w-4 h-4" />
              Add Device
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-800 text-sm mt-2"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Network Scanner */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Wifi className="w-5 h-5" />
            Network Device Scanner
          </h2>
          
          <div className="flex gap-4 items-end mb-4">
            <div className="flex-1">
              <label htmlFor="ipRange" className="block text-sm font-medium text-gray-700 mb-2">
                IP Range to Scan
              </label>
              <input
                id="ipRange"
                type="text"
                value={ipRange}
                onChange={(e) => setIpRange(e.target.value)}
                placeholder="192.168.1.0/24 or 192.168.1.1-192.168.1.254"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isScanning}
              />
              <p className="text-sm text-gray-500 mt-1">
                Examples: 192.168.1.0/24, 10.0.0.1-10.0.0.100, or single IP: 192.168.1.50
              </p>
            </div>
            
            <button
              onClick={startNetworkScan}
              disabled={isScanning}
              className="bg-green-600 text-white px-6 py-2 rounded-lg flex items-center gap-2 hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isScanning ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Scanning...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Scan Network
                </>
              )}
            </button>
          </div>

          {/* Scan Results */}
          {scanResults && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-blue-900 mb-2">Scan Results</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="font-medium">Total Devices:</span> {scanResults.total_found}
                </div>
                <div>
                  <span className="font-medium">Medical Devices:</span> {scanResults.medical_found}
                </div>
                <div>
                  <span className="font-medium">IP Range:</span> {scanResults.scan_parameters?.ip_range}
                </div>
              </div>
            </div>
          )}

          {/* Discovered Devices */}
          {discoveredDevices.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Discovered Devices</h3>
              <div className="grid gap-4">
                {discoveredDevices.map((device, index) => {
                  const confidenceScore = calculateConfidenceScore(device);
                  const confidenceColorClass = getConfidenceColor(confidenceScore);
                  
                  return (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-4">
                            <div>
                              <p className="font-semibold text-gray-900">
                                {device.ip_address}
                                {device.hostname && (
                                  <span className="text-sm text-gray-500 ml-2">({device.hostname})</span>
                                )}
                              </p>
                              {device.mac_address && (
                                <p className="text-sm text-gray-600">MAC: {device.mac_address}</p>
                              )}
                              {device.mac_manufacturer && (
                                <p className="text-sm text-gray-600">Manufacturer: {device.mac_manufacturer}</p>
                              )}
                            </div>
                            
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${confidenceColorClass}`}>
                                {confidenceScore}% confidence
                              </span>
                              {device.likely_medical_device && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                  Medical Device
                                </span>
                              )}
                              {device.dicom_capable && (
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  DICOM Capable
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                        <div>
                          <span className="font-medium text-gray-700">Open Ports:</span>
                          <div className="mt-1">
                            {device.open_ports.map(port => (
                              <span 
                                key={port} 
                                className={`inline-block px-2 py-1 text-xs rounded mr-1 mb-1 ${
                                  port === 104 || port === 11112 
                                    ? 'bg-green-100 text-green-800' 
                                    : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {port}
                              </span>
                            ))}
                          </div>
                        </div>
                        
                        <div>
                          <span className="font-medium text-gray-700">Services:</span>
                          <div className="mt-1">
                            {device.services && Object.values(device.services).map((service: any, idx) => (
                              <span key={idx} className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded mr-1 mb-1">
                                {service.service} ({service.port})
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      {device.dicom_echo_result && (
                        <div className="mb-3">
                          <span className="font-medium text-gray-700">DICOM Test:</span>
                          <span className={`ml-2 px-2 py-1 rounded text-xs ${
                            device.dicom_echo_result.success 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {device.dicom_echo_result.success ? 'DICOM Echo Success' : 'DICOM Echo Failed'}
                          </span>
                          {device.dicom_echo_result.ae_title && (
                            <span className="ml-2 text-xs text-gray-600">
                              AE Title: {device.dicom_echo_result.ae_title}
                            </span>
                          )}
                        </div>
                      )}
                      
                      <div className="flex justify-between items-center pt-3 border-t">
                        <div className="text-xs text-gray-500">
                          Last seen: {new Date(device.last_seen).toLocaleString()}
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => performDicomPing(device)}
                            className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                          >
                            Test DICOM
                          </button>
                          <button
                            onClick={() => createDeviceFromDiscovery(device)}
                            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 transition-colors"
                          >
                            Add Device
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Registered Devices */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Registered Devices</h2>
            <p className="text-gray-600 mt-1">Currently configured medical imaging devices</p>
          </div>
          
          <div className="p-6">
            {devices.length === 0 ? (
              <div className="text-center py-8">
                <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No devices registered yet.</p>
                <p className="text-gray-400 text-sm">Use the network scanner above to discover devices.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {devices.map((device) => (
                  <div key={device.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`flex items-center gap-2 ${getStatusColor(device.status)}`}>
                          {getStatusIcon(device.status)}
                          <span className="font-medium capitalize">{device.status}</span>
                        </div>
                        
                        <div>
                          <h3 className="font-semibold text-gray-900">{device.name}</h3>
                          <p className="text-sm text-gray-600">
                            {device.modality_type} • {device.manufacturer}
                          </p>
                          <p className="text-sm text-gray-500">{device.ip_address}</p>
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <button className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors">
                          <Play className="w-3 h-3 inline mr-1" />
                          Test
                        </button>
                        <button className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700 transition-colors">
                          <Settings className="w-3 h-3 inline mr-1" />
                          Configure
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeviceManagement;
