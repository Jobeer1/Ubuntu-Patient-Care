import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const DashboardRouter: React.FC = () => {
  const { user } = useAuth();

  // Redirect to appropriate dashboard based on user role
  if (user?.role === 'admin') {
    return <Navigate to="/admin" replace />;
  } else if (user?.role === 'doctor') {
    return <Navigate to="/doctor" replace />;
  } else if (user?.role === 'patient') {
    return <Navigate to="/patient" replace />;
  }

  // Default fallback - should not happen if auth is working properly
  return <Navigate to="/dashboard" replace />;
};

export default DashboardRouter;
