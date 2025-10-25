import React, { useState } from 'react';
import { 
  Wifi, 
  WifiOff, 
  Monitor, 
  Activity, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Plus,
  TestTube,
  Zap,
  Network,
  Clock,
  Shield,
  Info
} from 'lucide-react';

const DeviceDiscoveryResults = ({ 
  discoveryResults, 
  scanType, 
  onAddDevice, 
  onTestDicom,
  isLoading = false 
}) => {
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [testingDevice, setTestingDevice] = useState(null);
  const [showDetails, setShowDetails] = useState({});

  const getConfidenceColor = (score) => {
    if (score >= 70) return 'text-green-600 bg-green-100';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getDeviceTypeIcon = (deviceType, dicomCapable) => {
    if (dicomCapable) return <Monitor className="h-5 w-5 text-blue-600" />;
    if (deviceType === 'medical_device') return <Activity className="h-5 w-5 text-green-600" />;
    if (deviceType === 'pacs_server') return <Network className="h-5 w-5 text-purple-600" />;
    return <Wifi className="h-5 w-5 text-gray-600" />;
  };

  const handleTestDicom = async (device) => {
    setTestingDevice(device.ip_address);
    try {
      await onTestDicom(device);
    } finally {
      setTestingDevice(null);
    }
  };

  const toggleDetails = (deviceId) => {
    setShowDetails(prev => ({
      ...prev,
      [deviceId]: !prev[deviceId]
    }));
  };

  const ConnectivityTests = ({ tests }) => {
    if (!tests || Object.keys(tests).length === 0) return null;

    return (
      <div className="mt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Connectivity Tests</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {Object.entries(tests).map(([testName, result]) => (
            <div key={testName} className="flex items-center space-x-2 text-xs">
              {result.success ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : (
                <XCircle className="h-3 w-3 text-red-500" />
              )}
              <span className="font-medium">{testName.replace('_', ' ')}</span>
              {result.response_time_ms && (
                <span className="text-gray-500">({result.response_time_ms}ms)</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const DeviceCard = ({ device, index }) => {
    const deviceId = `${device.ip_address}_${index}`;
    const isDetailsOpen = showDetails[deviceId];

    return (
      <div className="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow">
        <div className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-3">
              {getDeviceTypeIcon(device.device_type, device.dicom_capable)}
              <div>
                <h3 className="font-medium text-gray-900">
                  {device.hostname || `Device ${device.ip_address}`}
                </h3>
                <p className="text-sm text-gray-500">{device.ip_address}</p>
              </div>
            </div>
            
            {device.confidence_score !== undefined && (
              <span className={`px-2 py-1 text-xs rounded-full font-medium ${getConfidenceColor(device.confidence_score)}`}>
                {device.confidence_score}% confidence
              </span>
            )}
          </div>

          {/* Device Info */}
          <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
            <div>
              <span className="text-gray-500">Manufacturer:</span>
              <span className="ml-2 font-medium">{device.manufacturer || 'Unknown'}</span>
            </div>
            <div>
              <span className="text-gray-500">Type:</span>
              <span className="ml-2 font-medium capitalize">
                {device.device_type?.replace('_', ' ') || 'Unknown'}
              </span>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex flex-wrap gap-2 mb-3">
            {device.likely_medical_device && (
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
            {device.open_ports && device.open_ports.length > 0 && (
              <span className="inline-flex items-center px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                <Network className="h-3 w-3 mr-1" />
                {device.open_ports.length} Open Ports
              </span>
            )}
          </div>

          {/* Open Ports */}
          {device.open_ports && device.open_ports.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-gray-500">Open Ports: </span>
              <span className="text-xs font-mono">
                {device.open_ports.join(', ')}
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onAddDevice(device)}
              className="flex items-center px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="h-3 w-3 mr-1" />
              Add Device
            </button>
            
            {device.dicom_capable && (
              <button
                onClick={() => handleTestDicom(device)}
                disabled={testingDevice === device.ip_address}
                className="flex items-center px-3 py-1 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {testingDevice === device.ip_address ? (
                  <Clock className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <TestTube className="h-3 w-3 mr-1" />
                )}
                Test DICOM
              </button>
            )}
            
            <button
              onClick={() => toggleDetails(deviceId)}
              className="flex items-center px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              <Info className="h-3 w-3 mr-1" />
              {isDetailsOpen ? 'Hide' : 'Show'} Details
            </button>
          </div>

          {/* Detailed Information */}
          {isDetailsOpen && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Device Information</h4>
                  <div className="space-y-1">
                    <div><span className="text-gray-500">IP Address:</span> <span className="font-mono">{device.ip_address}</span></div>
                    <div><span className="text-gray-500">Hostname:</span> <span className="font-mono">{device.hostname}</span></div>
                    {device.mac_address && (
                      <div><span className="text-gray-500">MAC Address:</span> <span className="font-mono">{device.mac_address}</span></div>
                    )}
                    <div><span className="text-gray-500">Source:</span> <span className="capitalize">{device.source?.replace('_', ' ')}</span></div>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Detection Results</h4>
                  <div className="space-y-1">
                    <div><span className="text-gray-500">Confidence Score:</span> <span className="font-medium">{device.confidence_score}%</span></div>
                    <div><span className="text-gray-500">Device Type:</span> <span className="capitalize">{device.device_type?.replace('_', ' ')}</span></div>
                    <div><span className="text-gray-500">Medical Device:</span> 
                      <span className={`ml-2 ${device.likely_medical_device ? 'text-green-600' : 'text-red-600'}`}>
                        {device.likely_medical_device ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div><span className="text-gray-500">DICOM Capable:</span> 
                      <span className={`ml-2 ${device.dicom_capable ? 'text-green-600' : 'text-red-600'}`}>
                        {device.dicom_capable ? 'Yes' : 'No'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Connectivity Tests */}
              <ConnectivityTests tests={device.connectivity_tests} />
            </div>
          )}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Scanning network...</span>
      </div>
    );
  }

  if (!discoveryResults || !discoveryResults.length) {
    return (
      <div className="text-center py-12">
        <WifiOff className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Devices Found</h3>
        <p className="text-gray-600">
          No devices were discovered in the specified range. Try expanding your search range or checking network connectivity.
        </p>
      </div>
    );
  }

  // Categorize devices
  const medicalDevices = discoveryResults.filter(d => d.likely_medical_device);
  const dicomDevices = discoveryResults.filter(d => d.dicom_capable);
  const highConfidenceDevices = discoveryResults.filter(d => d.confidence_score >= 50);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-lg font-medium text-blue-900 mb-2">
          🔍 {scanType === 'arp' ? 'ARP Scan' : 'Network Discovery'} Results
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{discoveryResults.length}</div>
            <div className="text-blue-700">Total Devices</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{medicalDevices.length}</div>
            <div className="text-green-700">Medical Devices</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{dicomDevices.length}</div>
            <div className="text-purple-700">DICOM Capable</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{highConfidenceDevices.length}</div>
            <div className="text-orange-700">High Confidence</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button className="border-b-2 border-blue-500 text-blue-600 py-2 px-1 text-sm font-medium">
            All Devices ({discoveryResults.length})
          </button>
          {medicalDevices.length > 0 && (
            <button className="border-b-2 border-transparent text-gray-500 hover:text-gray-700 py-2 px-1 text-sm font-medium">
              Medical Devices ({medicalDevices.length})
            </button>
          )}
          {dicomDevices.length > 0 && (
            <button className="border-b-2 border-transparent text-gray-500 hover:text-gray-700 py-2 px-1 text-sm font-medium">
              DICOM Capable ({dicomDevices.length})
            </button>
          )}
        </nav>
      </div>

      {/* Device Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {discoveryResults.map((device, index) => (
          <DeviceCard key={`${device.ip_address}_${index}`} device={device} index={index} />
        ))}
      </div>

      {/* Recommendations */}
      {medicalDevices.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 mr-3" />
            <div>
              <h4 className="text-sm font-medium text-green-900">Medical Devices Detected</h4>
              <p className="text-sm text-green-700 mt-1">
                Found {medicalDevices.length} potential medical device(s). These devices have high confidence scores and should be reviewed for addition to your PACS system.
              </p>
            </div>
          </div>
        </div>
      )}

      {dicomDevices.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <Monitor className="h-5 w-5 text-blue-600 mt-0.5 mr-3" />
            <div>
              <h4 className="text-sm font-medium text-blue-900">DICOM Devices Found</h4>
              <p className="text-sm text-blue-700 mt-1">
                Found {dicomDevices.length} device(s) with DICOM port (104) open. These are likely imaging devices that can be integrated with your PACS system.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeviceDiscoveryResults;