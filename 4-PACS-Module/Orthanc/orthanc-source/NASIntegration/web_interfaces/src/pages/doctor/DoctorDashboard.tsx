import React, { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  UserIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CalendarIcon,
  EyeIcon
} from '@heroicons/react/24/outline';

interface DoctorStats {
  totalPatients: number;
  activeAuthorizations: number;
  pendingAuthorizations: number;
  completedStudies: number;
  todayAppointments: number;
}

interface RecentActivity {
  id: number;
  type: 'authorization' | 'study' | 'appointment';
  description: string;
  patient?: string;
  timestamp: string;
  status: 'completed' | 'pending' | 'cancelled';
}

const DoctorDashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DoctorStats>({
    totalPatients: 0,
    activeAuthorizations: 0,
    pendingAuthorizations: 0,
    completedStudies: 0,
    todayAppointments: 0
  });
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDoctorData();
  }, []);

  const fetchDoctorData = async () => {
    try {
      setIsLoading(true);
      
      // Simulate API calls - replace with actual service calls
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setStats({
        totalPatients: 142,
        activeAuthorizations: 23,
        pendingAuthorizations: 8,
        completedStudies: 156,
        todayAppointments: 12
      });

      setRecentActivity([
        {
          id: 1,
          type: 'authorization',
          description: 'CT Scan authorization approved',
          patient: 'John Smith',
          timestamp: '2 hours ago',
          status: 'completed'
        },
        {
          id: 2,
          type: 'study',
          description: 'MRI study completed',
          patient: 'Jane Doe',
          timestamp: '4 hours ago',
          status: 'completed'
        },
        {
          id: 3,
          type: 'authorization',
          description: 'X-Ray authorization pending',
          patient: 'Bob Johnson',
          timestamp: '6 hours ago',
          status: 'pending'
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch doctor data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ComponentType<{ className?: string }>;
    color?: string;
    change?: string;
    changePositive?: boolean;
  }> = ({ title, value, icon: Icon, color = "text-blue-600", change, changePositive }) => (
    <div className="card">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className={`h-8 w-8 ${color}`} />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {change && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  changePositive ? 'text-green-600' : 'text-red-600'
                }`}>
                  {change}
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  );

  const ActivityItem: React.FC<{ activity: RecentActivity }> = ({ activity }) => {
    const getActivityIcon = () => {
      switch (activity.type) {
        case 'authorization':
          return DocumentTextIcon;
        case 'study':
          return ChartBarIcon;
        case 'appointment':
          return CalendarIcon;
        default:
          return DocumentTextIcon;
      }
    };

    const getStatusColor = () => {
      switch (activity.status) {
        case 'completed':
          return 'text-green-600 bg-green-100';
        case 'pending':
          return 'text-yellow-600 bg-yellow-100';
        case 'cancelled':
          return 'text-red-600 bg-red-100';
        default:
          return 'text-gray-600 bg-gray-100';
      }
    };

    const Icon = getActivityIcon();

    return (
      <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
        <div className="flex-shrink-0">
          <Icon className="h-5 w-5 text-gray-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-900">{activity.description}</p>
          {activity.patient && (
            <p className="text-sm text-gray-500">Patient: {activity.patient}</p>
          )}
        </div>
        <div className="flex-shrink-0 flex items-center space-x-2">
          <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor()}`}>
            {activity.status}
          </span>
          <span className="text-sm text-gray-500">{activity.timestamp}</span>
        </div>
      </div>
    );
  };

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
            Doctor Dashboard
          </h1>
          <p className="mt-2 text-gray-600">
            Welcome back, Dr. {user?.full_name || user?.username || 'Doctor'}! Here's your practice overview.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5 mb-8">
          <StatCard
            title="Total Patients"
            value={stats.totalPatients}
            icon={UserIcon}
            change="+5%"
            changePositive={true}
          />
          <StatCard
            title="Active Authorizations"
            value={stats.activeAuthorizations}
            icon={DocumentTextIcon}
            color="text-green-600"
            change="+3"
            changePositive={true}
          />
          <StatCard
            title="Pending Authorizations"
            value={stats.pendingAuthorizations}
            icon={ExclamationTriangleIcon}
            color="text-yellow-600"
          />
          <StatCard
            title="Completed Studies"
            value={stats.completedStudies}
            icon={ChartBarIcon}
            color="text-blue-600"
            change="+12"
            changePositive={true}
          />
          <StatCard
            title="Today's Appointments"
            value={stats.todayAppointments}
            icon={CalendarIcon}
            color="text-purple-600"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Activity */}
          <div className="lg:col-span-2">
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
              <div className="space-y-3">
                {recentActivity.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
              <div className="mt-4">
                <button className="btn-secondary w-full">
                  View All Activity
                </button>
              </div>
            </div>
          </div>

          {/* Quick Actions & Today's Schedule */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button className="btn-primary w-full flex items-center justify-center">
                  <DocumentTextIcon className="h-5 w-5 mr-2" />
                  New Authorization
                </button>
                <button className="btn-secondary w-full flex items-center justify-center">
                  <ChartBarIcon className="h-5 w-5 mr-2" />
                  View Studies
                </button>
                <button className="btn-secondary w-full flex items-center justify-center">
                  <UserIcon className="h-5 w-5 mr-2" />
                  Manage Patients
                </button>
                <button className="btn-secondary w-full flex items-center justify-center">
                  <EyeIcon className="h-5 w-5 mr-2" />
                  DICOM Viewer
                </button>
              </div>
            </div>

            {/* Today's Schedule */}
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Today's Schedule</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">9:00 AM - Patient Consultation</p>
                    <p className="text-xs text-gray-500">John Smith</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">11:30 AM - MRI Review</p>
                    <p className="text-xs text-gray-500">Jane Doe</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">2:00 PM - Authorization Review</p>
                    <p className="text-xs text-gray-500">Pending approvals</p>
                  </div>
                </div>
              </div>
              <div className="mt-4">
                <button className="btn-secondary w-full">
                  <CalendarIcon className="h-4 w-4 mr-2 inline" />
                  View Full Schedule
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DoctorDashboard;
