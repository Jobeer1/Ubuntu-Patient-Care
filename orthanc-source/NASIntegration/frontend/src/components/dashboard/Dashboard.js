import React from 'react';
import { useQuery } from 'react-query';
import { 
  Activity, 
  Users, 
  Images, 
  HardDrive, 
  Shield, 
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../utils/api';
import LoadingSpinner from '../common/LoadingSpinner';
import StatsCard from './StatsCard';
import QuickActions from './QuickActions';

const Dashboard = () => {
  const { user } = useAuth();

  // Fetch dashboard statistics
  const { data: stats, isLoading, error } = useQuery(
    ['dashboard-stats'],
    async () => {
      const response = await api.get('/dashboard/stats');
      return response.data.stats;
    },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-800">Failed to load dashboard data</span>
        </div>
      </div>
    );
  }

  const isAdmin = user?.role === 'admin';

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.username}!
            </h1>
            <p className="text-gray-600 mt-1">
              {isAdmin ? 'System Administrator Dashboard' : 'Medical Imaging Dashboard'}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-12 w-12 bg-primary-100 rounded-full flex items-center justify-center">
              <Activity className="h-6 w-6 text-primary-600" />
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center p-3 bg-green-50 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
            <div>
              <p className="text-sm font-medium text-green-900">API Server</p>
              <p className="text-xs text-green-700">Online</p>
            </div>
          </div>
          
          <div className="flex items-center p-3 bg-blue-50 rounded-lg">
            <HardDrive className="h-5 w-5 text-blue-500 mr-3" />
            <div>
              <p className="text-sm font-medium text-blue-900">NAS Storage</p>
              <p className="text-xs text-blue-700">
                {stats?.nas?.status?.connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center p-3 bg-purple-50 rounded-lg">
            <Shield className="h-5 w-5 text-purple-500 mr-3" />
            <div>
              <p className="text-sm font-medium text-purple-900">Security</p>
              <p className="text-xs text-purple-700">
                2FA {stats?.['2fa']?.system_2fa_enabled ? 'Enabled' : 'Disabled'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Images"
          value={stats?.images?.total_images || 0}
          icon={Images}
          color="blue"
          subtitle="DICOM files stored"
        />
        
        {isAdmin && (
          <StatsCard
            title="Total Users"
            value={stats?.users?.total_users || 0}
            icon={Users}
            color="green"
            subtitle="Active accounts"
          />
        )}
        
        <StatsCard
          title="Recent Uploads"
          value={stats?.images?.recent_uploads_7d || 0}
          icon={TrendingUp}
          color="purple"
          subtitle="Last 7 days"
        />
        
        <StatsCard
          title="Storage Used"
          value={`${stats?.images?.total_size_gb || 0} GB`}
          icon={HardDrive}
          color="orange"
          subtitle="Total file size"
        />
      </div>

      {/* Quick Actions */}
      <QuickActions user={user} />

      {/* Recent Activity & Modality Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Modality Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Images by Modality</h3>
          {stats?.images?.images_by_modality && Object.keys(stats.images.images_by_modality).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(stats.images.images_by_modality).map(([modality, count]) => (
                <div key={modality} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-primary-500 rounded-full mr-3"></div>
                    <span className="text-sm font-medium text-gray-900">{modality}</span>
                  </div>
                  <span className="text-sm text-gray-600">{count} images</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Images className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No images uploaded yet</p>
            </div>
          )}
        </div>

        {/* NAS Storage Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Storage Information</h3>
          {stats?.nas?.space && !stats.nas.space.error ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Total Space</span>
                <span className="text-sm font-medium">{stats.nas.space.total_gb} GB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Used Space</span>
                <span className="text-sm font-medium">{stats.nas.space.used_gb} GB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Free Space</span>
                <span className="text-sm font-medium text-green-600">{stats.nas.space.free_gb} GB</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-primary-600 h-2 rounded-full" 
                  style={{ width: `${stats.nas.space.usage_percent}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 text-center">
                {stats.nas.space.usage_percent}% used
              </p>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <HardDrive className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>Storage information unavailable</p>
              <p className="text-xs mt-1">Check NAS connection</p>
            </div>
          )}
        </div>
      </div>

      {/* Admin-only sections */}
      {isAdmin && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Statistics */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">User Activity</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Recent Logins (24h)</span>
                <span className="text-sm font-medium">{stats?.users?.recent_logins_24h || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Failed Attempts (24h)</span>
                <span className="text-sm font-medium text-red-600">{stats?.users?.failed_logins_24h || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Active Sessions</span>
                <span className="text-sm font-medium">{stats?.users?.active_sessions || 0}</span>
              </div>
            </div>
          </div>

          {/* 2FA Statistics */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Security Status</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Users with 2FA</span>
                <span className="text-sm font-medium">{stats?.['2fa']?.users_with_2fa_enabled || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">2FA Attempts (24h)</span>
                <span className="text-sm font-medium">{stats?.['2fa']?.recent_auth_attempts_24h || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Failed 2FA (24h)</span>
                <span className="text-sm font-medium text-red-600">{stats?.['2fa']?.recent_failed_attempts_24h || 0}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;