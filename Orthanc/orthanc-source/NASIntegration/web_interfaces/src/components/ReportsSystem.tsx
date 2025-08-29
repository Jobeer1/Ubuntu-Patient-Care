import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Users, 
  Activity, 
  TrendingUp, 
  Download,
  Filter,
  RefreshCw
} from 'lucide-react';

interface ReportData {
  user_statistics: {
    total_users: number;
    active_users: number;
    new_users_this_month: number;
    users_by_role: Record<string, number>;
  };
  activity_statistics: {
    total_logins_today: number;
    total_logins_this_week: number;
    total_logins_this_month: number;
    peak_usage_hour: string;
  };
  device_statistics: {
    total_devices: number;
    online_devices: number;
    device_types: Record<string, number>;
    connectivity_rate: number;
  };
  system_performance: {
    avg_response_time: number;
    uptime_percentage: number;
    total_api_calls: number;
    error_rate: number;
  };
}

const ReportsSystem: React.FC = () => {
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportType, setReportType] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadReportData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:5000/api/admin/reports/${reportType}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to load report data');
      }
      
      const data = await response.json();
      setReportData(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format: 'pdf' | 'csv') => {
    try {
      const response = await fetch(`http://localhost:5000/api/admin/reports/export?type=${reportType}&format=${format}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) throw new Error('Failed to export report');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sa-medical-report-${reportType}-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export report');
    }
  };

  useEffect(() => {
    loadReportData();
  }, [reportType]);

  if (loading && !reportData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span className="text-gray-500">Loading reports...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SA Medical System Reports</h1>
          <p className="text-gray-600">Comprehensive analytics and reporting for healthcare operations</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => exportReport('pdf')}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Export PDF</span>
          </button>
          <button
            onClick={() => exportReport('csv')}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-400" />
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="daily">Daily Report</option>
              <option value="weekly">Weekly Report</option>
              <option value="monthly">Monthly Report</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            {lastUpdated && (
              <span className="text-sm text-gray-500">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={loadReportData}
              disabled={loading}
              className="px-3 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {reportData && (
        <>
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Users</p>
                  <p className="text-2xl font-bold text-gray-900">{reportData.user_statistics.total_users}</p>
                  <p className="text-sm text-green-600">
                    +{reportData.user_statistics.new_users_this_month} this month
                  </p>
                </div>
                <Users className="h-8 w-8 text-blue-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Users</p>
                  <p className="text-2xl font-bold text-gray-900">{reportData.user_statistics.active_users}</p>
                  <p className="text-sm text-gray-600">
                    {Math.round((reportData.user_statistics.active_users / reportData.user_statistics.total_users) * 100)}% of total
                  </p>
                </div>
                <Activity className="h-8 w-8 text-green-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">System Uptime</p>
                  <p className="text-2xl font-bold text-gray-900">{reportData.system_performance.uptime_percentage}%</p>
                  <p className="text-sm text-green-600">Excellent performance</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Device Connectivity</p>
                  <p className="text-2xl font-bold text-gray-900">{reportData.device_statistics.connectivity_rate}%</p>
                  <p className="text-sm text-gray-600">
                    {reportData.device_statistics.online_devices}/{reportData.device_statistics.total_devices} online
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-purple-600" />
              </div>
            </div>
          </div>

          {/* Detailed Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* User Distribution */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Users by Role</h3>
              <div className="space-y-3">
                {Object.entries(reportData.user_statistics.users_by_role).map(([role, count]) => (
                  <div key={role} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600 capitalize">{role}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ 
                            width: `${(count / reportData.user_statistics.total_users) * 100}%` 
                          }}
                        ></div>
                      </div>
                      <span className="text-sm font-bold text-gray-900">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Device Types */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Device Distribution</h3>
              <div className="space-y-3">
                {Object.entries(reportData.device_statistics.device_types).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600 capitalize">{type}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-purple-600 h-2 rounded-full" 
                          style={{ 
                            width: `${(count / reportData.device_statistics.total_devices) * 100}%` 
                          }}
                        ></div>
                      </div>
                      <span className="text-sm font-bold text-gray-900">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Activity Summary */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Activity Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{reportData.activity_statistics.total_logins_today}</p>
                <p className="text-sm text-gray-600">Logins Today</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{reportData.activity_statistics.total_logins_this_week}</p>
                <p className="text-sm text-gray-600">Logins This Week</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">{reportData.activity_statistics.total_logins_this_month}</p>
                <p className="text-sm text-gray-600">Logins This Month</p>
              </div>
            </div>
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>Peak Usage:</strong> {reportData.activity_statistics.peak_usage_hour} |
                <strong> Avg Response Time:</strong> {reportData.system_performance.avg_response_time}ms |
                <strong> Error Rate:</strong> {reportData.system_performance.error_rate}%
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ReportsSystem;
