import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// Import components
import LoginPage from './components/auth/LoginPage';
import TwoFactorSetup from './components/auth/TwoFactorSetup';
import TwoFactorVerify from './components/auth/TwoFactorVerify';
import Dashboard from './components/dashboard/Dashboard';
import AdminDashboard from './components/admin/AdminDashboard';
import UserDashboard from './components/user/UserDashboard';
import ImageBrowser from './components/images/ImageBrowser';
import SharedImageView from './components/shared/SharedImageView';
import Layout from './components/layout/Layout';
import LoadingSpinner from './components/common/LoadingSpinner';

function App() {
  const { user, loading, requires2FA, needs2FASetup } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Not authenticated - show login
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/share/:token" element={<SharedImageView />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Authenticated but needs 2FA setup
  if (needs2FASetup) {
    return (
      <Routes>
        <Route path="/2fa/setup" element={<TwoFactorSetup />} />
        <Route path="*" element={<Navigate to="/2fa/setup" replace />} />
      </Routes>
    );
  }

  // Authenticated but needs 2FA verification
  if (requires2FA) {
    return (
      <Routes>
        <Route path="/2fa/verify" element={<TwoFactorVerify />} />
        <Route path="*" element={<Navigate to="/2fa/verify" replace />} />
      </Routes>
    );
  }

  // Fully authenticated - show main app
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        
        {/* Admin routes */}
        {user.role === 'admin' && (
          <>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/*" element={<AdminDashboard />} />
          </>
        )}
        
        {/* User routes */}
        <Route path="/dashboard" element={<UserDashboard />} />
        <Route path="/images" element={<ImageBrowser />} />
        <Route path="/images/*" element={<ImageBrowser />} />
        
        {/* Shared routes */}
        <Route path="/share/:token" element={<SharedImageView />} />
        
        {/* 2FA management routes */}
        <Route path="/2fa/setup" element={<TwoFactorSetup />} />
        <Route path="/2fa/verify" element={<TwoFactorVerify />} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;