import React, { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  ShieldCheckIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  HeartIcon
} from '@heroicons/react/24/outline';

interface PatientStats {
  activeAuthorizations: number;
  completedStudies: number;
  pendingApprovals: number;
  sharedStudies: number;
}

interface Authorization {
  id: number;
  study_type: string;
  doctor_name: string;
  date_requested: string;
  status: 'approved' | 'pending' | 'denied';
  expires_at?: string;
}

const PatientDashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<PatientStats>({
    activeAuthorizations: 0,
    completedStudies: 0,
    pendingApprovals: 0,
    sharedStudies: 0
  });
  const [authorizations, setAuthorizations] = useState<Authorization[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchPatientData();
  }, []);

  const fetchPatientData = async () => {
    try {
      setIsLoading(true);
      
      // Simulate API calls - replace with actual service calls
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setStats({
        activeAuthorizations: 3,
        completedStudies: 8,
        pendingApprovals: 1,
        sharedStudies: 2
      });

      setAuthorizations([
        {
          id: 1,
          study_type: 'CT Scan - Chest',
          doctor_name: 'Dr. Sarah Johnson',
          date_requested: '2024-01-15',
          status: 'approved',
          expires_at: '2024-02-15'
        },
        {
          id: 2,
          study_type: 'MRI - Brain',
          doctor_name: 'Dr. Michael Brown',
          date_requested: '2024-01-10',
          status: 'pending'
        },
        {
          id: 3,
          study_type: 'X-Ray - Knee',
          doctor_name: 'Dr. Sarah Johnson',
          date_requested: '2024-01-08',
          status: 'approved',
          expires_at: '2024-02-08'
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch patient data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ComponentType<{ className?: string }>;
    color?: string;
    description?: string;
  }> = ({ title, value, icon: Icon, color = "text-blue-600", description }) => (
    <div className="card">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className={`h-8 w-8 ${color}`} />
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd>
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {description && (
                <div className="text-sm text-gray-500">{description}</div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  );

  const AuthorizationCard: React.FC<{ authorization: Authorization }> = ({ authorization }) => {
    const getStatusConfig = () => {
      switch (authorization.status) {
        case 'approved':
          return {
            color: 'text-green-600 bg-green-100',
            icon: CheckCircleIcon,
            text: 'Approved'
          };
        case 'pending':
          return {
            color: 'text-yellow-600 bg-yellow-100',
            icon: ClockIcon,
            text: 'Pending'
          };
        case 'denied':
          return {
            color: 'text-red-600 bg-red-100',
            icon: ExclamationTriangleIcon,
            text: 'Denied'
          };
        default:
          return {
            color: 'text-gray-600 bg-gray-100',
            icon: ClockIcon,
            text: 'Unknown'
          };
      }
    };

    const statusConfig = getStatusConfig();
    const StatusIcon = statusConfig.icon;

    return (
      <div className="card border-l-4 border-l-blue-500">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h4 className="text-lg font-medium text-gray-900">{authorization.study_type}</h4>
            <p className="text-sm text-gray-600 mt-1">Requested by: {authorization.doctor_name}</p>
            <p className="text-sm text-gray-600">Date: {new Date(authorization.date_requested).toLocaleDateString()}</p>
            {authorization.expires_at && authorization.status === 'approved' && (
              <p className="text-sm text-gray-600">
                Expires: {new Date(authorization.expires_at).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 text-sm rounded-full flex items-center ${statusConfig.color}`}>
              <StatusIcon className="h-4 w-4 mr-1" />
              {statusConfig.text}
            </span>
            {authorization.status === 'approved' && (
              <button className="text-blue-600 hover:text-blue-800">
                <EyeIcon className="h-5 w-5" />
              </button>
            )}
          </div>
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
            Patient Portal
          </h1>
          <p className="mt-2 text-gray-600">
            Welcome, {user?.full_name || user?.username || 'Patient'}! Manage your medical authorizations and view your studies.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          <StatCard
            title="Active Authorizations"
            value={stats.activeAuthorizations}
            icon={DocumentTextIcon}
            color="text-green-600"
            description="Currently valid"
          />
          <StatCard
            title="Completed Studies"
            value={stats.completedStudies}
            icon={ChartBarIcon}
            color="text-blue-600"
            description="Total studies done"
          />
          <StatCard
            title="Pending Approvals"
            value={stats.pendingApprovals}
            icon={ClockIcon}
            color="text-yellow-600"
            description="Awaiting approval"
          />
          <StatCard
            title="Shared Studies"
            value={stats.sharedStudies}
            icon={ShieldCheckIcon}
            color="text-purple-600"
            description="Available to view"
          />
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Authorization List */}
          <div className="lg:col-span-2">
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Your Authorizations</h3>
              <div className="space-y-4">
                {authorizations.map((auth) => (
                  <AuthorizationCard key={auth.id} authorization={auth} />
                ))}
              </div>
              {authorizations.length === 0 && (
                <div className="text-center py-8">
                  <DocumentTextIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No authorizations found</p>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button className="btn-primary w-full flex items-center justify-center">
                  <EyeIcon className="h-5 w-5 mr-2" />
                  View Studies
                </button>
                <button className="btn-secondary w-full flex items-center justify-center">
                  <DocumentTextIcon className="h-5 w-5 mr-2" />
                  Request Authorization
                </button>
                <button className="btn-secondary w-full flex items-center justify-center">
                  <ShieldCheckIcon className="h-5 w-5 mr-2" />
                  Manage Consents
                </button>
              </div>
            </div>

            {/* Health Summary */}
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Health Summary</h3>
              <div className="space-y-3">
                <div className="flex items-center">
                  <HeartIcon className="h-5 w-5 text-red-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium">Recent Studies</p>
                    <p className="text-xs text-gray-500">Last: CT Scan (Jan 15)</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <DocumentTextIcon className="h-5 w-5 text-blue-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium">Authorizations</p>
                    <p className="text-xs text-gray-500">3 active, 1 pending</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Important Notice */}
            <div className="card bg-blue-50 border-blue-200">
              <div className="flex items-start">
                <ExclamationTriangleIcon className="h-6 w-6 text-blue-600 mt-1" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    Important Notice
                  </h3>
                  <p className="mt-1 text-sm text-blue-700">
                    Your authorization for CT Scan expires in 30 days. Please consult with your doctor if you need an extension.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientDashboard;
