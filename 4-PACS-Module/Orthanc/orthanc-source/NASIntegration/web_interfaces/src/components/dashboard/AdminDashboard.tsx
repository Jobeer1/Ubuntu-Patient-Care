import React, { useState, useEffect } from 'react';
import { Users, Activity, AlertTriangle, CheckCircle, Monitor, Network, Database, Shield, XCircle } from 'lucide-react';

interface DashboardStats {
  total_users: number;
  active_sessions: number;
  total_devices: number;
  online_devices: number;
  total_studies: number;
  recent_scans: number;
  system_health: 'healthy' | 'warning' | 'critical';
  nas_status: 'connected' | 'disconnected' | 'error';
}

interface RecentActivity {
  id: string;
  type: 'login' | 'device_scan' | 'study_upload' | 'user_created';
  user: string;
  timestamp: string;
  details: string;
}

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load dashboard statistics
      const statsResponse = await fetch('/api/admin/dashboard/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      // Load recent activity
      const activityResponse = await fetch('/api/admin/dashboard/activity?limit=10');
      if (activityResponse.ok) {
        const activityData = await activityResponse.json();
        setRecentActivity(activityData.activities || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy': return <CheckCircle className="w-5 h-5" />;
      case 'warning': return <AlertTriangle className="w-5 h-5" />;
      case 'critical': return <XCircle className="w-5 h-5" />;
      default: return <Monitor className="w-5 h-5" />;
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'login': return <Users className="w-4 h-4" />;
      case 'device_scan': return <Network className="w-4 h-4" />;
      case 'study_upload': return <Database className="w-4 h-4" />;
      case 'user_created': return <Shield className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* System Health Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">System Health</p>
                <div className={`flex items-center gap-2 mt-2 px-3 py-1 rounded-full text-sm font-medium ${getHealthColor(stats.system_health)}`}>
                  {getHealthIcon(stats.system_health)}
                  {stats.system_health.charAt(0).toUpperCase() + stats.system_health.slice(1)}
                </div>
              </div>
              <Monitor className="w-8 h-8 text-gray-400" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Users</p>
                <p className="text-2xl font-bold text-gray-900">{stats.active_sessions}</p>
                <p className="text-xs text-gray-500">of {stats.total_users} total</p>
              </div>
              <Users className="w-8 h-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Medical Devices</p>
                <p className="text-2xl font-bold text-gray-900">{stats.online_devices}</p>
                <p className="text-xs text-gray-500">of {stats.total_devices} online</p>
              </div>
              <Activity className="w-8 h-8 text-green-400" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">DICOM Studies</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_studies}</p>
                <p className="text-xs text-gray-500">{stats.recent_scans} today</p>
              </div>
              <Database className="w-8 h-8 text-purple-400" />
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Network className="w-6 h-6 text-blue-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">Scan Network</div>
                <div className="text-sm text-gray-500">Discover medical devices</div>
              </div>
            </button>
            
            <button className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Users className="w-6 h-6 text-green-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">Manage Users</div>
                <div className="text-sm text-gray-500">Add or edit users</div>
              </div>
            </button>
            
            <button className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <Database className="w-6 h-6 text-purple-600" />
              <div className="text-left">
                <div className="font-medium text-gray-900">System Reports</div>
                <div className="text-sm text-gray-500">Generate reports</div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
        </div>
        <div className="p-6">
          {recentActivity.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No recent activity
            </div>
          ) : (
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 text-gray-600">
                    {getActivityIcon(activity.type)}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      {activity.details}
                    </div>
                    <div className="text-xs text-gray-500">
                      {activity.user} • {new Date(activity.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
