import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { 
  UserGroupIcon, 
  DocumentTextIcon, 
  ChartBarIcon, 
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

interface DashboardStats {
  totalUsers: number;
  totalDoctors: number;
  totalAuthorizations: number;
  pendingAuthorizations: number;
  totalShares: number;
  systemHealth: 'healthy' | 'warning' | 'error';
}

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalUsers: 0,
    totalDoctors: 0,
    totalAuthorizations: 0,
    pendingAuthorizations: 0,
    totalShares: 0,
    systemHealth: 'healthy'
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate API call to fetch dashboard stats
    const fetchStats = async () => {
      try {
        // This would be replaced with actual API calls
        await new Promise(resolve => setTimeout(resolve, 1000));
        setStats({
          totalUsers: 145,
          totalDoctors: 23,
          totalAuthorizations: 89,
          pendingAuthorizations: 12,
          totalShares: 156,
          systemHealth: 'healthy'
        });
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ComponentType<{ className?: string }>;
    trend?: string;
    trendPositive?: boolean;
  }> = ({ title, value, icon: Icon, trend, trendPositive }) => (
    <div className="card">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className="h-8 w-8 text-blue-600" />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {trend && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  trendPositive ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trend}
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  );

  const getHealthStatus = () => {
    switch (stats.systemHealth) {
      case 'healthy':
        return {
          icon: CheckCircleIcon,
          text: 'System Healthy',
          color: 'text-green-600',
          bgColor: 'bg-green-50'
        };
      case 'warning':
        return {
          icon: ExclamationTriangleIcon,
          text: 'System Warning',
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50'
        };
      case 'error':
        return {
          icon: ExclamationTriangleIcon,
          text: 'System Error',
          color: 'text-red-600',
          bgColor: 'bg-red-50'
        };
      default:
        return {
          icon: CheckCircleIcon,
          text: 'Unknown',
          color: 'text-gray-600',
          bgColor: 'bg-gray-50'
        };
    }
  };

  const healthStatus = getHealthStatus();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name || user?.username || 'User'}!
          </h1>
          <p className="mt-2 text-gray-600">
            Here's what's happening with your healthcare management system today.
          </p>
        </div>

        {/* System Health Status */}
        <div className={`mb-8 p-4 rounded-md ${healthStatus.bgColor}`}>
          <div className="flex items-center">
            <healthStatus.icon className={`h-6 w-6 ${healthStatus.color}`} />
            <h3 className={`ml-3 text-sm font-medium ${healthStatus.color}`}>
              {healthStatus.text}
            </h3>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-8">
          <StatCard
            title="Total Users"
            value={stats.totalUsers}
            icon={UserGroupIcon}
            trend="+12%"
            trendPositive={true}
          />
          <StatCard
            title="Active Doctors"
            value={stats.totalDoctors}
            icon={ShieldCheckIcon}
            trend="+3%"
            trendPositive={true}
          />
          <StatCard
            title="Total Authorizations"
            value={stats.totalAuthorizations}
            icon={DocumentTextIcon}
            trend="+8%"
            trendPositive={true}
          />
          <StatCard
            title="Pending Authorizations"
            value={stats.pendingAuthorizations}
            icon={ExclamationTriangleIcon}
            trend="-5%"
            trendPositive={false}
          />
          <StatCard
            title="Secure Shares"
            value={stats.totalShares}
            icon={ChartBarIcon}
            trend="+15%"
            trendPositive={true}
          />
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Activity */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <UserGroupIcon className="h-5 w-5 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">New user registration</p>
                  <p className="text-sm text-gray-500">Dr. Sarah Johnson joined the system</p>
                </div>
                <div className="flex-shrink-0 text-sm text-gray-500">
                  2 hours ago
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <DocumentTextIcon className="h-5 w-5 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">Authorization approved</p>
                  <p className="text-sm text-gray-500">Patient John Doe - Imaging Study</p>
                </div>
                <div className="flex-shrink-0 text-sm text-gray-500">
                  4 hours ago
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <ChartBarIcon className="h-5 w-5 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">New secure share created</p>
                  <p className="text-sm text-gray-500">Medical records for Patient X</p>
                </div>
                <div className="flex-shrink-0 text-sm text-gray-500">
                  6 hours ago
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <button className="btn-primary w-full">
                Create New Authorization
              </button>
              <button className="btn-secondary w-full">
                View Pending Approvals
              </button>
              <button className="btn-secondary w-full">
                Generate Reports
              </button>
              <button className="btn-secondary w-full">
                Manage User Permissions
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
