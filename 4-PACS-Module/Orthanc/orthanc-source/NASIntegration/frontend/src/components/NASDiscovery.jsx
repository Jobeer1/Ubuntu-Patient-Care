import React, { useState, useEffect } from 'react';
import { 
  HardDrive, 
  Search, 
  Wifi, 
  Server, 
  Shield, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  Folder,
  Network,
  Settings,
  Eye,
  EyeOff,
  Key,
  Clock,
  Database,
  Zap,
  Activity,
  Monitor
} from 'lucide-react';

const NASDiscovery = () => {
  const [discoveredDevices, setDiscoveredDevices] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanType, setScanType] = useState('comprehensive');
  const [ipRange, setIpRange] = useState('192.168.1.0/24');
  const [maxThreads, setMaxThreads] = useState(50);
  const [suggestions, setSuggestions] = useState(null);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showCredentials, setShowCredentials] = useState(false);
  const [credentials, setCredentials] = useState({
    username: '',
    password: '',
    domain: '',
    share_path: ''
  });
  const [testingCredentials, setTestingCredentials] = useState(false);
  const [deviceStats, setDeviceStats] = useState(null);

  useEffect(() => {
    loadSuggestions();
    loadDiscoveredDevices();
    loadDeviceStats();
  }, []);

  const loadDeviceStats = async () => {
    try {
      const response = await fetch('/api/devices/database/stats');
      const data = await response.json();
      if (data.success) {
        setDeviceStats(data.statistics);
      }
    } catch (error) {
      console.error('Error loading device statistics:', error);
    }
  };

  const loadSuggestions = async () => {
    try {
      const response = await fetch('/api/nas/suggestions');
      const data = await response.json();
      if (data.success) {
        setSuggestions(data.suggestions);
      }
    } catch (error) {
      console.error('Error loading suggestions:', error);
    }
  };

  const loadDiscoveredDevices = async () => {
    try {
      // Try to load from device database first
      const dbResponse = await fetch('/api/devices/database');
      const dbData = await dbResponse.json();
      
      if (dbData.success && dbData.devices.length > 0) {
        setDiscoveredDevices(dbData.devices);
        return;
      }
      
      // Fallback to NAS devices endpoint
      const nasResponse = await fetch('/api/nas/devices');
      const nasData = await nasResponse.json();
      if (nasData.success) {
        setDiscoveredDevices(nasData.devices);
      }
    } catch (error) {
      console.error('Error loading discovered devices:', error);
    }
  };

  const startNASDiscovery = async () => {
    setIsScanning(true);
    setScanProgress(0);
    
    try {
      const response = await fetch('/api/nas/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ip_range: ipRange,
          scan_type: scanType,
          max_threads: maxThreads
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setDiscoveredDevices(data.discovered_devices);
        setScanProgress(100);
        setTimeout(() => {
          setIsScanning(false);
          setScanProgress(0);
        }, 1000);
      } else {
        alert(`Discovery failed: ${data.error}`);
        setIsScanning(false);
      }
    } catch (error) {
      alert(`Discovery error: ${error.message}`);
      setIsScanning(false);
    }
  };

  const quickScan = async () => {
    setIsScanning(true);
    setScanProgress(0);
    
    try {
      const response = await fetch('/api/nas/quick-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();
      
      if (data.success) {
        setDiscoveredDevices(data.discovered_devices);
        setScanProgress(100);
        setTimeout(() => {
          setIsScanning(false);
          setScanProgress(0);
        }, 1000);
      } else {
        alert(`Quick scan failed: ${data.error}`);
        setIsScanning(false);
      }
    } catch (error) {
      alert(`Quick scan error: ${error.message}`);
      setIsScanning(false);
    }
  };

  const testCredentials = async () => {
    if (!selectedDevice) return;
    
    setTestingCredentials(true);
    
    try {
      const response = await fetch('/api/nas/test-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nas_id: selectedDevice.id,
          ...credentials
        })
      });

      const data = await response.json();
      
      if (data.success) {
        alert('✅ Credentials are valid!');
      } else {
        alert(`❌ Credential test failed: ${data.message}`);
      }
    } catch (error) {
      alert(`Credential test error: ${error.message}`);
    } finally {
      setTestingCredentials(false);
    }
  };

  const getNASTypeIcon = (nasType) => {
    switch (nasType) {
      case 'smb': return <Server className="h-5 w-5 text-blue-600" />;
      case 'nfs': return <Database className="h-5 w-5 text-green-600" />;
      case 'ftp': return <Folder className="h-5 w-5 text-orange-600" />;
      default: return <HardDrive className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'discovered': return 'text-blue-600 bg-blue-100';
      case 'configured': return 'text-green-600 bg-green-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const DiscoveryTab = () => (
    <div className="space-y-6">
      {/* Device Database Statistics */}
      {deviceStats && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <Database className="h-5 w-5 mr-2" />
            Device Database Statistics
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{deviceStats.total_devices || 0}</div>
              <div className="text-sm text-gray-500">Total Devices</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{deviceStats.online_devices || 0}</div>
              <div className="text-sm text-gray-500">Online Devices</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{deviceStats.medical_devices || 0}</div>
              <div className="text-sm text-gray-500">Medical Devices</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{deviceStats.unique_manufacturers || 0}</div>
              <div className="text-sm text-gray-500">Manufacturers</div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Last Updated:</span> {deviceStats.last_updated || 'Never'}
            </div>
          </div>
        </div>
      )}

      {/* Discovery Controls */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <Search className="h-5 w-5 mr-2" />
          NAS Discovery Settings
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              IP Range
            </label>
            <input
              type="text"
              value={ipRange}
              onChange={(e) => setIpRange(e.target.value)}
              placeholder="192.168.1.0/24"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Scan Type
            </label>
            <select
              value={scanType}
              onChange={(e) => setScanType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="quick">Quick Scan (1-2 min)</option>
              <option value="comprehensive">Comprehensive (3-5 min)</option>
              <option value="deep">Deep Scan (5-10 min)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Threads
            </label>
            <input
              type="number"
              value={maxThreads}
              onChange={(e) => setMaxThreads(parseInt(e.target.value))}
              min="1"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={startNASDiscovery}
            disabled={isScanning}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isScanning ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Scanning... {scanProgress}%
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Start Discovery
              </>
            )}
          </button>
          
          <button
            onClick={quickScan}
            disabled={isScanning}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            <Zap className="h-4 w-4 mr-2" />
            Quick Scan
          </button>
        </div>
        
        {isScanning && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${scanProgress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Discovery Results */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-medium text-gray-900 flex items-center">
            <HardDrive className="h-5 w-5 mr-2" />
            Discovered NAS Devices ({discoveredDevices.length})
          </h3>
        </div>
        
        <div className="p-6">
          {discoveredDevices.length === 0 ? (
            <div className="text-center py-8">
              <HardDrive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No NAS devices discovered yet</p>
              <p className="text-sm text-gray-400 mt-2">
                Click "Start Discovery" to scan your network for NAS devices
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {discoveredDevices.map(device => (
                <div 
                  key={device.ip_address || device.id} 
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => setSelectedDevice(device)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center">
                      <Server className="h-5 w-5 text-blue-600" />
                      <div className="ml-3">
                        <h4 className="font-medium text-gray-900">
                          {device.hostname || device.name || device.ip_address}
                        </h4>
                        <p className="text-sm text-gray-500">{device.ip_address}</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-1">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        device.reachable ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {device.reachable ? 'Online' : 'Offline'}
                      </span>
                      {device.confidence_score && (
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {device.confidence_score}% confidence
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="space-y-2 text-sm text-gray-600 mb-3">
                    <div className="flex items-center">
                      <Server className="h-4 w-4 mr-2" />
                      <span className="font-medium">{device.manufacturer || 'Unknown'}</span>
                      {device.device_type && (
                        <span className="ml-2 text-xs bg-gray-100 px-2 py-1 rounded">
                          {device.device_type.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                    
                    {device.os_fingerprint && device.os_fingerprint !== 'Unknown' && (
                      <div className="flex items-center">
                        <Shield className="h-4 w-4 mr-2" />
                        OS: {device.os_fingerprint}
                      </div>
                    )}
                    
                    <div className="flex items-center">
                      <Network className="h-4 w-4 mr-2" />
                      {device.open_ports?.length || 0} open ports
                      {device.services?.length > 0 && (
                        <span className="ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                          {device.services.length} services
                        </span>
                      )}
                    </div>
                    
                    {device.response_time && device.response_time !== 'N/A' && (
                      <div className="flex items-center">
                        <Clock className="h-4 w-4 mr-2" />
                        Response: {device.response_time}
                      </div>
                    )}
                    
                    {device.last_updated && (
                      <div className="flex items-center">
                        <Clock className="h-4 w-4 mr-2" />
                        Last seen: {new Date(device.last_updated).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                  
                  {/* Device Type Indicators */}
                  <div className="flex flex-wrap gap-1 mb-3">
                    {device.device_type === 'medical_device' && (
                      <span className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                        <Activity className="h-3 w-3 mr-1" />
                        Medical Device
                      </span>
                    )}
                    {device.dicom_capable && (
                      <span className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        <Monitor className="h-3 w-3 mr-1" />
                        DICOM Capable
                      </span>
                    )}
                    {device.open_ports?.some(port => port.port === 104) && (
                      <span className="inline-flex items-center px-2 py-1 text-xs bg-indigo-100 text-indigo-800 rounded-full">
                        <Network className="h-3 w-3 mr-1" />
                        DICOM Port Open
                      </span>
                    )}
                  </div>
                  
                  <div className="mt-3 flex space-x-2">
                    <button className="flex-1 px-3 py-2 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100 flex items-center justify-center">
                      <Settings className="h-3 w-3 mr-1" />
                      Configure
                    </button>
                    <button className="flex-1 px-3 py-2 text-xs bg-gray-50 text-gray-700 rounded hover:bg-gray-100 flex items-center justify-center">
                      <Zap className="h-3 w-3 mr-1" />
                      Test
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Suggestions */}
      {suggestions && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2 text-yellow-600" />
            Discovery Tips for South African Healthcare
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Common IP Ranges</h4>
              <div className="space-y-1">
                {suggestions.common_ip_ranges?.map(range => (
                  <button
                    key={range}
                    onClick={() => setIpRange(range)}
                    className="block w-full text-left px-3 py-1 text-sm bg-gray-50 hover:bg-gray-100 rounded"
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Healthcare Tips</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                {suggestions.healthcare_tips?.map((tip, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircle className="h-4 w-4 text-green-500 mr-2 mt-0.5 flex-shrink-0" />
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const DeviceDetailsTab = () => (
    <div className="space-y-6">
      {selectedDevice ? (
        <>
          {/* Device Information */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center">
                {getNASTypeIcon(selectedDevice.nas_type)}
                <div className="ml-3">
                  <h3 className="text-lg font-medium text-gray-900">{selectedDevice.name}</h3>
                  <p className="text-gray-500">{selectedDevice.hostname} • {selectedDevice.ip_address}</p>
                </div>
              </div>
              <span className={`px-3 py-1 text-sm rounded-full ${getStatusColor(selectedDevice.status)}`}>
                {selectedDevice.status}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Device Info</h4>
                <div className="space-y-1 text-sm text-gray-600">
                  <p><strong>Manufacturer:</strong> {selectedDevice.manufacturer}</p>
                  <p><strong>Model:</strong> {selectedDevice.model}</p>
                  <p><strong>Type:</strong> {selectedDevice.nas_type.toUpperCase()}</p>
                  <p><strong>Last Seen:</strong> {new Date(selectedDevice.last_seen).toLocaleString()}</p>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Network</h4>
                <div className="space-y-1 text-sm text-gray-600">
                  <p><strong>Open Ports:</strong> {selectedDevice.ports?.join(', ')}</p>
                  <p><strong>Services:</strong> {selectedDevice.services?.join(', ')}</p>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Storage</h4>
                <div className="space-y-1 text-sm text-gray-600">
                  <p><strong>Shares:</strong> {selectedDevice.shares?.length || 0}</p>
                  {selectedDevice.capacity_gb && (
                    <p><strong>Capacity:</strong> {selectedDevice.capacity_gb} GB</p>
                  )}
                  {selectedDevice.free_space_gb && (
                    <p><strong>Free Space:</strong> {selectedDevice.free_space_gb} GB</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Shares */}
          {selectedDevice.shares && selectedDevice.shares.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                <Folder className="h-5 w-5 mr-2" />
                Available Shares
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedDevice.shares.map((share, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900">{share.name}</h4>
                      <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                        {share.type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{share.description}</p>
                    <p className="text-xs text-gray-500 font-mono">{share.path}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Credentials Testing */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
              <Key className="h-5 w-5 mr-2" />
              Test Credentials
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={credentials.username}
                  onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showCredentials ? "text" : "password"}
                    value={credentials.password}
                    onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCredentials(!showCredentials)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showCredentials ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Domain (Optional)
                </label>
                <input
                  type="text"
                  value={credentials.domain}
                  onChange={(e) => setCredentials({...credentials, domain: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Share Path (Optional)
                </label>
                <input
                  type="text"
                  value={credentials.share_path}
                  onChange={(e) => setCredentials({...credentials, share_path: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <button
              onClick={testCredentials}
              disabled={testingCredentials || !credentials.username || !credentials.password}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {testingCredentials ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Testing...
                </>
              ) : (
                <>
                  <Shield className="h-4 w-4 mr-2" />
                  Test Credentials
                </>
              )}
            </button>
          </div>
        </>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="text-center py-8">
            <HardDrive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Select a NAS device to view details</p>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center">
          <HardDrive className="h-8 w-8 mr-3 text-blue-600" />
          NAS Discovery
        </h1>
        <p className="text-gray-600">
          Discover and configure Network Attached Storage devices for your South African healthcare facility
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'discovery', label: 'Discovery', icon: Search },
            { id: 'details', label: 'Device Details', icon: Settings }
          ].map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4 mr-2" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'discovery' && <DiscoveryTab />}
        {activeTab === 'details' && <DeviceDetailsTab />}
      </div>
    </div>
  );
};

export default NASDiscovery;