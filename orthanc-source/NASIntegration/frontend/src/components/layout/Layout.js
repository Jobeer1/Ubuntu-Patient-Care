import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Activity, 
  Users, 
  Images, 
  Settings, 
  LogOut, 
  Menu, 
  X,
  Shield,
  Database,
  BarChart3
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../common/LoadingSpinner';

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout, logoutLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navigation = [
    { name: 'Dashboard', href: '/', icon: BarChart3, current: location.pathname === '/' },
    { name: 'Images', href: '/images', icon: Images, current: location.pathname.startsWith('/images') },
    ...(user?.role === 'admin' ? [
      { name: 'Admin Panel', href: '/admin', icon: Settings, current: location.pathname.startsWith('/admin') },
      { name: 'User Management', href: '/admin/users', icon: Users, current: location.pathname === '/admin/users' },
      { name: 'NAS Settings', href: '/admin/nas', icon: Database, current: location.pathname === '/admin/nas' },
    ] : []),
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 flex z-40 md:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white">
          <div className="absolute top-0 right-0 -mr-12 pt-2">
            <button
              type="button"
              className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-6 w-6 text-white" />
            </button>
          </div>
          <SidebarContent navigation={navigation} user={user} onLogout={handleLogout} logoutLoading={logoutLoading} />
        </div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
        <SidebarContent navigation={navigation} user={user} onLogout={handleLogout} logoutLoading={logoutLoading} />
      </div>

      {/* Main content */}
      <div className="md:pl-64 flex flex-col flex-1">
        {/* Top bar */}
        <div className="sticky top-0 z-10 md:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-gray-50">
          <button
            type="button"
            className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
        </div>

        {/* Page content */}
        <main className="flex-1">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

const SidebarContent = ({ navigation, user, onLogout, logoutLoading }) => (
  <div className="flex-1 flex flex-col min-h-0 bg-white border-r border-gray-200">
    {/* Logo */}
    <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
      <div className="flex items-center flex-shrink-0 px-4">
        <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
          <Activity className="h-5 w-5 text-white" />
        </div>
        <div className="ml-3">
          <h1 className="text-lg font-semibold text-gray-900">Orthanc NAS</h1>
          <p className="text-xs text-gray-500">Medical Imaging</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="mt-8 flex-1 px-2 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
                item.current
                  ? 'bg-primary-100 text-primary-900'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon
                className={`mr-3 flex-shrink-0 h-5 w-5 ${
                  item.current ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                }`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </div>

    {/* User info and logout */}
    <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
      <div className="flex-shrink-0 w-full group block">
        <div className="flex items-center">
          <div className="h-9 w-9 bg-primary-100 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-primary-700">
              {user?.username?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-gray-700">{user?.username}</p>
            <div className="flex items-center">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                user?.role === 'admin' 
                  ? 'bg-red-100 text-red-800' 
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {user?.role}
              </span>
              {user?.['2fa_status']?.setup_complete && (
                <Shield className="ml-2 h-3 w-3 text-green-500" title="2FA Enabled" />
              )}
            </div>
          </div>
          <button
            onClick={onLogout}
            disabled={logoutLoading}
            className="ml-2 p-1 rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500"
            title="Logout"
          >
            {logoutLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <LogOut className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  </div>
);

export default Layout;