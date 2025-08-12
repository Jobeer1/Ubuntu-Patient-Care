import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Users, Database, Settings, Shield, Server, Activity } from 'lucide-react';
import OrthancManager from '../orthanc/OrthancManager';

const AdminDashboard = () => {
  const [activeSection, setActiveSection] = useState('overview');

  return (
    <div className="space-y-6">
      {/* Admin Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center">
          <div className="h-12 w-12 bg-red-100 rounded-lg flex items-center justify-center">
            <Shield className="h-6 w-6 text-red-600" />
          </div>
          <div className="ml-4">
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-600">System administration for South African healthcare</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'overview', name: 'Overview', icon: Activity },
              { id: 'orthanc', name: 'PACS Server', icon: Server },
              { id: 'users', name: 'Users', icon: Users },
              { id: 'nas', name: 'Storage', icon: Database },
              { id: 'settings', name: 'Settings', icon: Settings }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveSection(tab.id)}
                className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm ${
                  activeSection === tab.id
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
          {activeSection === 'overview' && <OverviewSection />}
          {activeSection === 'orthanc' && <OrthancManager />}
          {activeSection === 'users' && <UsersSection />}
          {activeSection === 'nas' && <NASSection />}
          {activeSection === 'settings' && <SettingsSection />}
        </div>
      </div>
    </div>
  );
};

const OverviewSection = () => (
  <div className="space-y-6">
    {/* Quick Actions */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <AdminCard
        title="PACS Server"
        description="Manage Orthanc medical imaging server"
        icon={Server}
        color="bg-blue-500"
        highlight={true}
      />
      <AdminCard
        title="User Management"
        description="Manage healthcare professionals"
        icon={Users}
        color="bg-green-500"
      />
      <AdminCard
        title="NAS Storage"
        description="Configure network storage"
        icon={Database}
        color="bg-purple-500"
      />
      <AdminCard
        title="System Settings"
        description="Configure system security"
        icon={Settings}
        color="bg-orange-500"
      />
    </div>

    {/* Welcome Message */}
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
      <div className="flex items-center">
        <Shield className="h-8 w-8 text-blue-600 mr-3" />
        <div>
          <h3 className="text-lg font-medium text-blue-900">Welcome to SA Healthcare Admin</h3>
          <p className="text-blue-700 mt-1">
            This simplified admin interface is designed specifically for South African healthcare facilities. 
            Start by configuring your PACS server in the "PACS Server" tab above.
          </p>
        </div>
      </div>
    </div>
  </div>
);

const UsersSection = () => (
  <div className="text-center py-12">
    <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-gray-900 mb-2">User Management</h3>
    <p className="text-gray-600 mb-4">
      Manage healthcare professionals, roles, and permissions.
    </p>
    <p className="text-sm text-gray-500">
      User management interface coming soon.
    </p>
  </div>
);

const NASSection = () => (
  <div className="text-center py-12">
    <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-gray-900 mb-2">NAS Storage</h3>
    <p className="text-gray-600 mb-4">
      Configure network attached storage for medical images.
    </p>
    <p className="text-sm text-gray-500">
      NAS configuration interface coming soon.
    </p>
  </div>
);

const SettingsSection = () => (
  <div className="text-center py-12">
    <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-gray-900 mb-2">System Settings</h3>
    <p className="text-gray-600 mb-4">
      Configure system-wide settings, security, and compliance.
    </p>
    <p className="text-sm text-gray-500">
      Settings interface coming soon.
    </p>
  </div>
);

const AdminCard = ({ title, description, icon: Icon, color, highlight = false }) => (
  <div className={`bg-white rounded-lg shadow p-6 hover:shadow-md transition-all duration-300 cursor-pointer ${
    highlight ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
  }`}>
    <div className="flex items-center mb-4">
      <div className={`p-3 rounded-lg ${color} text-white`}>
        <Icon className="h-6 w-6" />
      </div>
    </div>
    <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
    <p className="text-gray-600 text-sm">{description}</p>
    <div className="mt-4">
      <span className="text-sm text-blue-600 hover:text-blue-700 font-medium">
        {highlight ? 'Start Here →' : 'Configure →'}
      </span>
    </div>
  </div>
);

export default AdminDashboard;