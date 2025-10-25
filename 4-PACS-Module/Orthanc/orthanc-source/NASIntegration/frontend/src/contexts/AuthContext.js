import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';
import api from '../utils/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [requires2FA, setRequires2FA] = useState(false);
  const [needs2FASetup, setNeeds2FASetup] = useState(false);
  const queryClient = useQueryClient();

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await api.get('/profile');
      const userData = response.data.user;
      const twoFAStatus = response.data['2fa_status'];

      setUser(userData);

      // Check 2FA requirements
      if (twoFAStatus.required_for_user) {
        if (twoFAStatus.needs_setup) {
          setNeeds2FASetup(true);
          setRequires2FA(false);
        } else if (twoFAStatus.needs_verification) {
          setRequires2FA(true);
          setNeeds2FASetup(false);
        } else {
          setRequires2FA(false);
          setNeeds2FASetup(false);
        }
      } else {
        setRequires2FA(false);
        setNeeds2FASetup(false);
      }
    } catch (error) {
      // Not authenticated
      setUser(null);
      setRequires2FA(false);
      setNeeds2FASetup(false);
    } finally {
      setLoading(false);
    }
  };

  const loginMutation = useMutation(
    async ({ username, pin }) => {
      const response = await api.post('/login', { username, pin });
      return response.data;
    },
    {
      onSuccess: (data) => {
        const userData = data.user;
        const twoFARequirements = data['2fa_requirements'];

        setUser(userData);

        // Handle 2FA requirements
        if (twoFARequirements.required_for_user) {
          if (twoFARequirements.needs_setup) {
            setNeeds2FASetup(true);
            setRequires2FA(false);
            toast.success('Login successful. Please set up 2FA.');
          } else if (twoFARequirements.needs_verification) {
            setRequires2FA(true);
            setNeeds2FASetup(false);
            toast.success('Login successful. Please verify 2FA.');
          } else {
            setRequires2FA(false);
            setNeeds2FASetup(false);
            toast.success('Login successful!');
          }
        } else {
          setRequires2FA(false);
          setNeeds2FASetup(false);
          toast.success('Login successful!');
        }

        // Invalidate and refetch queries
        queryClient.invalidateQueries();
      },
      onError: (error) => {
        const message = error.response?.data?.error || 'Login failed';
        toast.error(message);
      },
    }
  );

  const logoutMutation = useMutation(
    async () => {
      await api.post('/logout');
    },
    {
      onSuccess: () => {
        setUser(null);
        setRequires2FA(false);
        setNeeds2FASetup(false);
        queryClient.clear();
        toast.success('Logged out successfully');
      },
      onError: (error) => {
        // Even if logout fails on server, clear local state
        setUser(null);
        setRequires2FA(false);
        setNeeds2FASetup(false);
        queryClient.clear();
        toast.error('Logout failed, but you have been logged out locally');
      },
    }
  );

  const verify2FAMutation = useMutation(
    async ({ code, method }) => {
      const response = await api.post('/2fa/verify', { code, method });
      return response.data;
    },
    {
      onSuccess: () => {
        setRequires2FA(false);
        setNeeds2FASetup(false);
        toast.success('2FA verification successful!');
        queryClient.invalidateQueries();
      },
      onError: (error) => {
        const message = error.response?.data?.error || '2FA verification failed';
        toast.error(message);
      },
    }
  );

  const setup2FAMutation = useMutation(
    async () => {
      const response = await api.post('/2fa/setup/totp');
      return response.data;
    },
    {
      onError: (error) => {
        const message = error.response?.data?.error || '2FA setup failed';
        toast.error(message);
      },
    }
  );

  const verify2FASetupMutation = useMutation(
    async ({ code }) => {
      const response = await api.post('/2fa/setup/totp/verify', { code });
      return response.data;
    },
    {
      onSuccess: () => {
        setNeeds2FASetup(false);
        toast.success('2FA setup completed successfully!');
        checkAuthStatus(); // Refresh auth status
      },
      onError: (error) => {
        const message = error.response?.data?.error || '2FA setup verification failed';
        toast.error(message);
      },
    }
  );

  const generateBackupCodesMutation = useMutation(
    async () => {
      const response = await api.post('/2fa/backup-codes/generate');
      return response.data;
    },
    {
      onSuccess: () => {
        toast.success('Backup codes generated successfully!');
      },
      onError: (error) => {
        const message = error.response?.data?.error || 'Failed to generate backup codes';
        toast.error(message);
      },
    }
  );

  const disable2FAMutation = useMutation(
    async () => {
      const response = await api.post('/2fa/disable');
      return response.data;
    },
    {
      onSuccess: () => {
        toast.success('2FA disabled successfully');
        checkAuthStatus(); // Refresh auth status
      },
      onError: (error) => {
        const message = error.response?.data?.error || 'Failed to disable 2FA';
        toast.error(message);
      },
    }
  );

  const updateProfileMutation = useMutation(
    async (profileData) => {
      const response = await api.put('/profile', profileData);
      return response.data;
    },
    {
      onSuccess: (data) => {
        toast.success('Profile updated successfully');
        checkAuthStatus(); // Refresh user data
      },
      onError: (error) => {
        const message = error.response?.data?.error || 'Failed to update profile';
        toast.error(message);
      },
    }
  );

  // Get 2FA status
  const { data: twoFAStatus, refetch: refetch2FAStatus } = useQuery(
    ['2fa-status'],
    async () => {
      const response = await api.get('/2fa/status');
      return response.data.status;
    },
    {
      enabled: !!user,
      onError: (error) => {
        console.error('Failed to fetch 2FA status:', error);
      },
    }
  );

  const value = {
    // State
    user,
    loading,
    requires2FA,
    needs2FASetup,
    twoFAStatus,

    // Actions
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    verify2FA: verify2FAMutation.mutate,
    setup2FA: setup2FAMutation.mutate,
    verify2FASetup: verify2FASetupMutation.mutate,
    generateBackupCodes: generateBackupCodesMutation.mutate,
    disable2FA: disable2FAMutation.mutate,
    updateProfile: updateProfileMutation.mutate,
    checkAuthStatus,
    refetch2FAStatus,

    // Loading states
    loginLoading: loginMutation.isLoading,
    logoutLoading: logoutMutation.isLoading,
    verify2FALoading: verify2FAMutation.isLoading,
    setup2FALoading: setup2FAMutation.isLoading,
    verify2FASetupLoading: verify2FASetupMutation.isLoading,
    generateBackupCodesLoading: generateBackupCodesMutation.isLoading,
    disable2FALoading: disable2FAMutation.isLoading,
    updateProfileLoading: updateProfileMutation.isLoading,

    // Data from mutations
    setup2FAData: setup2FAMutation.data,
    backupCodesData: generateBackupCodesMutation.data,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};