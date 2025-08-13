import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Upload, 
  Search, 
  Settings, 
  Users, 
  Shield, 
  Database,
  Plus,
  Eye
} from 'lucide-react';

const QuickActions = ({ user }) => {
  const isAdmin = user?.role === 'admin';

  const userActions = [
    {
      name: 'Browse Images',
      description: 'View and search DICOM images',
      href: '/images',
      icon: Eye,
      color: 'bg-blue-500 hover:bg-blue-600',
    },
    {
      name: 'Upload Images',
      description: 'Upload new DICOM files',
      href: '/images/upload',
      icon: Upload,
      color: 'bg-green-500 hover:bg-green-600',
    },
    {
      name: 'Search Studies',
      description: 'Find specific studies or patients',
      href: '/images?tab=search',
      icon: Search,
      color: 'bg-purple-500 hover:bg-purple-600',
    },
    {
      name: '2FA Settings',
      description: 'Manage two-factor authentication',
      href: '/2fa/setup',
      icon: Shield,
      color: 'bg-orange-500 hover:bg-orange-600',
    },
  ];

  const adminActions = [
    {
      name: 'User Management',
      description: 'Add, edit, and manage users',
      href: '/admin/users',
      icon: Users,
      color: 'bg-indigo-500 hover:bg-indigo-600',
    },
    {
      name: 'NAS Configuration',
      description: 'Configure network storage settings',
      href: '/admin/nas',
      icon: Database,
      color: 'bg-cyan-500 hover:bg-cyan-600',
    },
    {
      name: 'System Settings',
      description: 'Configure system-wide settings',
      href: '/admin/settings',
      icon: Settings,
      color: 'bg-gray-500 hover:bg-gray-600',
    },
    {
      name: 'Add New User',
      description: 'Create a new user account',
      href: '/admin/users/new',
      icon: Plus,
      color: 'bg-emerald-500 hover:bg-emerald-600',
    },
  ];

  const actions = isAdmin ? [...userActions, ...adminActions] : userActions;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              key={action.name}
              to={action.href}
              className="group relative bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg text-white ${action.color} transition-colors`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 group-hover:text-gray-700">
                    {action.name}
                  </p>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                    {action.description}
                  </p>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
};

export default QuickActions;