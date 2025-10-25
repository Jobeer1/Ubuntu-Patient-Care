import React, { useState, useEffect } from 'react';
import { 
  Server, 
  Play, 
  Square, 
  RotateCcw, 
  Settings, 
  Users, 
  Share2, 
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Database,
  Wifi,
  WifiOff
} from 'lucide-react';

const OrthancManager = () => {
  const [serverStatus, setServerStatus] = useState(null);
  const [quickStats, setQuickStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    fetchServerStatus();
    fetchQuickStats();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchServerStatus();
      fetchQuickStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchServerStatus = async () => {
    try {
      const response = await fetch('/api/orthanc/status', {
        credentials: 'include'
      });
      const data = await response.json();
      if (data.success) {
        setServerStatus(data.status);
      }
    } catch (error) {
      console.error('Error fetching server status:', error);
    }
  };

  const fetchQuickStats = async () => {
    try {
      const response = await fetch('/api/orthanc/quick-stats', {
        credentials: 'include'
      });
      const data = await response.json();
      if (data.success) {
        setQuickStats(data.stats);
      }
    } catch (error) {
      console.error('Error fetching quick stats:', error);
    }
  };

  const handleServerAction = async (action) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/orthanc/${action}`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        // Refresh status after action
        setTimeout(() => {
          fetchServerStatus();
          fetchQuickStats();
        }, 2000);
      } else {
        alert(`Error: ${data.message || data.error}`);
      }
    } catch (error) {
      console.error(`Error ${action} server:`, error);
      alert(`Error ${action} server: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'text-green-600 bg-green-100';
      case 'stopped': return 'text-red-600 bg-red-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running': return <CheckCircle className="h-5 w-5" />;
      case 'stopped': return <AlertCircle className="h-5 w-5" />;
      default: return <Clock className="h-5 w-5" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Server className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <h1 className="text-2xl font-bold text-gray-900">Orthanc PACS Server</h1>
              <p className="text-gray-600">Simple medical imaging server management</p>
            </div>
          </div>
          
          {/* Server Status Badge */}
          {serverStatus && (
            <div className={`flex items-center px-3 py-2 rounded-full ${getStatusColor(serverStatus.status)}`}>
              {getStatusIcon(serverStatus.status)}
              <span className="ml-2 font-medium capitalize">
                {serverStatus.status === 'running' ? 'Online' : 
                 serverStatus.status === 'stopped' ? 'Offline' : 
                 serverStatus.status}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      {quickStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <StatCard
            title="Server Status"
            value={quickStats.server_status === 'running' ? 'Online' : 'Offline'}
            icon={quickStats.server_status === 'running' ? Wifi : WifiOff}
            color={quickStats.server_status === 'running' ? 'green' : 'red'}
          />
          <StatCard
            title="Studies Stored"
            value={quickStats.studies_count.toLocaleString()}
            icon={Database}
            color="blue"
          />
          <StatCard
            title="Storage Used"
            value={`${(quickStats.storage_used_mb / 1024).toFixed(1)} GB`}
            icon={Server}
            color="purple"
          />
          <StatCard
            title="Active Shares"
            value={quickStats.active_shares}
            icon={Share2}
            color="orange"
          />
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'dashboard', name: 'Server Control', icon: Activity },
              { id: 'config', name: 'Settings', icon: Settings },
              { id: 'shares', name: 'Patient Sharing', icon: Share2 },
              { id: 'doctors', name: 'Referring Doctors', icon: Users }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-5 w-5 mr-2" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'dashboard' && (
            <ServerControlPanel 
              serverStatus={serverStatus}
              onServerAction={handleServerAction}
              loading={loading}
            />
          )}
          {activeTab === 'config' && <ConfigurationPanel />}
          {activeTab === 'shares' && <PatientSharingPanel />}
          {activeTab === 'doctors' && <ReferringDoctorsPanel />}
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon: Icon, color }) => {
  const colorClasses = {
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600'
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
};

const ServerControlPanel = ({ serverStatus, onServerAction, loading }) => {
  const isRunning = serverStatus?.status === 'running';

  return (
    <div className="space-y-6">
      {/* Server Status */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Server Status</h3>
        
        {serverStatus ? (
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${isRunning ? 'text-green-600' : 'text-red-600'}`}>
                {isRunning ? 'Running' : 'Stopped'}
              </span>
            </div>
            
            {isRunning && (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600">Web Interface:</span>
                  <a 
                    href={serverStatus.web_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800"
                  >
                    {serverStatus.web_url}
                  </a>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">DICOM Port:</span>
                  <span className="font-medium">{serverStatus.dicom_port}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Uptime:</span>
                  <span className="font-medium">{serverStatus.uptime}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Version:</span>
                  <span className="font-medium">{serverStatus.version}</span>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="text-gray-500">Loading server status...</div>
        )}
      </div>

      {/* Server Controls */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Server Controls</h3>
        
        <div className="flex space-x-4">
          <button
            onClick={() => onServerAction('start')}
            disabled={loading || isRunning}
            className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="h-4 w-4 mr-2" />
            Start Server
          </button>
          
          <button
            onClick={() => onServerAction('stop')}
            disabled={loading || !isRunning}
            className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Square className="h-4 w-4 mr-2" />
            Stop Server
          </button>
          
          <button
            onClick={() => onServerAction('restart')}
            disabled={loading}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Restart Server
          </button>
        </div>
        
        {loading && (
          <div className="mt-4 text-blue-600">
            Processing server action...
          </div>
        )}
      </div>

      {/* Quick Setup */}
      <QuickSetupPanel />
    </div>
  );
};

const QuickSetupPanel = () => {
  const [setupData, setSetupData] = useState({
    hospital_name: 'SA Healthcare PACS',
    web_port: 8042,
    dicom_port: 4242,
    aet_title: 'ORTHANC',
    allow_remote: true
  });
  const [loading, setLoading] = useState(false);

  const handleQuickSetup = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/orthanc/quick-setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(setupData)
      });
      
      const data = await response.json();
      if (data.success) {
        alert('Quick setup completed successfully!');
      } else {
        alert(`Setup error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error in quick setup:', error);
      alert(`Setup error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-blue-50 rounded-lg p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Setup</h3>
      <p className="text-gray-600 mb-4">
        Set up your Orthanc server with basic configuration for South African healthcare facilities.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Hospital/Clinic Name
          </label>
          <input
            type="text"
            value={setupData.hospital_name}
            onChange={(e) => setSetupData({...setupData, hospital_name: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AET Title
          </label>
          <input
            type="text"
            value={setupData.aet_title}
            onChange={(e) => setSetupData({...setupData, aet_title: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Web Port
          </label>
          <input
            type="number"
            value={setupData.web_port}
            onChange={(e) => setSetupData({...setupData, web_port: parseInt(e.target.value)})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            DICOM Port
          </label>
          <input
            type="number"
            value={setupData.dicom_port}
            onChange={(e) => setSetupData({...setupData, dicom_port: parseInt(e.target.value)})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
      
      <div className="flex items-center mb-4">
        <input
          type="checkbox"
          id="allow_remote"
          checked={setupData.allow_remote}
          onChange={(e) => setSetupData({...setupData, allow_remote: e.target.checked})}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="allow_remote" className="ml-2 text-sm text-gray-700">
          Allow remote access (recommended for multi-user environments)
        </label>
      </div>
      
      <button
        onClick={handleQuickSetup}
        disabled={loading}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Setting up...' : 'Quick Setup & Start'}
      </button>
    </div>
  );
};

const ConfigurationPanel = () => {
  return (
    <div className="text-center py-12">
      <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Advanced Configuration</h3>
      <p className="text-gray-600 mb-4">
        Advanced configuration options will be available here.
      </p>
      <p className="text-sm text-gray-500">
        For now, use the Quick Setup above for basic configuration.
      </p>
    </div>
  );
};

const PatientSharingPanel = () => {
  return (
    <div className="text-center py-12">
      <Share2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Patient Sharing</h3>
      <p className="text-gray-600 mb-4">
        Create secure links to share patient images with referring doctors.
      </p>
      <p className="text-sm text-gray-500">
        Patient sharing interface coming soon.
      </p>
    </div>
  );
};

const ReferringDoctorsPanel = () => {
  return (
    <div className="text-center py-12">
      <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">Referring Doctors</h3>
      <p className="text-gray-600 mb-4">
        Manage referring doctors and their access to patient studies.
      </p>
      <p className="text-sm text-gray-500">
        Doctor management interface coming soon.
      </p>
    </div>
  );
};

export default OrthancManager;