import React from 'react';
import AdminDashboard from '../../components/dashboard/AdminDashboard';

const AdminDashboardPage: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <AdminDashboard />
    </div>
  );
};

export default AdminDashboardPage;
      
      // Fetch doctor statistics
      const doctorStats = await doctorService.getDoctorStats();
      
      // Fetch recent doctors
      const doctorList = await doctorService.getDoctors(1, 5);
      
      setStats({
        totalDoctors: doctorStats.total,
        activeDoctors: doctorStats.active,
        pendingDoctors: doctorStats.pending,
        inactiveDoctors: doctorStats.inactive,
        totalAuthorizations: 89, // This would come from authorization service
        pendingAuthorizations: 12, // This would come from authorization service
        systemHealth: 'healthy'
      });
      
      setDoctors(doctorList.doctors);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ComponentType<{ className?: string }>;
    trend?: string;
    trendPositive?: boolean;
    color?: string;
  }> = ({ title, value, icon: Icon, trend, trendPositive, color = "text-blue-600" }) => (
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
            Admin Dashboard
          </h1>
          <p className="mt-2 text-gray-600">
            Welcome back, {user?.full_name || user?.username || 'Administrator'}! Manage your healthcare system.
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
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          <StatCard
            title="Total Doctors"
            value={stats.totalDoctors}
            icon={UserGroupIcon}
            trend="+12%"
            trendPositive={true}
          />
          <StatCard
            title="Active Doctors"
            value={stats.activeDoctors}
            icon={ShieldCheckIcon}
            trend="+3%"
            trendPositive={true}
            color="text-green-600"
          />
          <StatCard
            title="Pending Approvals"
            value={stats.pendingDoctors}
            icon={ExclamationTriangleIcon}
            trend="-5%"
            trendPositive={false}
            color="text-yellow-600"
          />
          <StatCard
            title="Authorizations"
            value={stats.totalAuthorizations}
            icon={DocumentTextIcon}
            trend="+8%"
            trendPositive={true}
            color="text-blue-600"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Doctors */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Recent Doctors</h3>
              <button 
                onClick={() => setShowDoctorModal(true)}
                className="btn-primary flex items-center"
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Doctor
              </button>
            </div>
            <div className="space-y-3">
              {doctors.map((doctor) => (
                <div key={doctor.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{doctor.full_name}</p>
                    <p className="text-sm text-gray-500">HPCSA: {doctor.hpcsa_number}</p>
                    <p className="text-sm text-gray-500">{doctor.qualification_primary}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      doctor.status === 'active' 
                        ? 'bg-green-100 text-green-800'
                        : doctor.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {doctor.status}
                    </span>
                    <button 
                      onClick={() => setSelectedDoctor(doctor)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <EyeIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <button className="btn-secondary w-full">
                View All Doctors
              </button>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <button className="btn-primary w-full flex items-center justify-center">
                <UserGroupIcon className="h-5 w-5 mr-2" />
                Manage Doctors
              </button>
              <button className="btn-secondary w-full flex items-center justify-center">
                <DocumentTextIcon className="h-5 w-5 mr-2" />
                Review Authorizations
              </button>
              <button className="btn-secondary w-full flex items-center justify-center">
                <ChartBarIcon className="h-5 w-5 mr-2" />
                Generate Reports
              </button>
              <button className="btn-secondary w-full flex items-center justify-center">
                <ShieldCheckIcon className="h-5 w-5 mr-2" />
                System Configuration
              </button>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="mt-8">
          <div className="card">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <UserGroupIcon className="h-5 w-5 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">New doctor registration</p>
                  <p className="text-sm text-gray-500">Dr. Sarah Johnson applied for approval</p>
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
                  <p className="text-sm text-gray-500">Patient authorization for CT scan</p>
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
                  <p className="text-sm text-gray-900">System backup completed</p>
                  <p className="text-sm text-gray-500">Daily backup successful</p>
                </div>
                <div className="flex-shrink-0 text-sm text-gray-500">
                  6 hours ago
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
