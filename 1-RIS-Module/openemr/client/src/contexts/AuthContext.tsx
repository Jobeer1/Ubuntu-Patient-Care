import React, { createContext, useContext, useState, ReactNode } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';

interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  // Check if user is authenticated on app load
  const { isLoading: verifyLoading } = useQuery(
    'verify-auth',
    authAPI.verifyToken,
    {
      retry: false,
      onSuccess: (data) => {
        if (data.success && data.data.user) {
          setUser(data.data.user);
        }
        setLoading(false);
      },
      onError: () => {
        localStorage.removeItem('token');
        setLoading(false);
      },
    }
  );

  // Login mutation
  const loginMutation = useMutation(
    ({ email, password }: { email: string; password: string }) =>
      authAPI.login(email, password),
    {
      onSuccess: (data) => {
        console.log('Login response:', data);
        if (data.success && data.data.token && data.data.user) {
          localStorage.setItem('token', data.data.token);
          setUser(data.data.user);
          toast.success(`Welcome back, ${data.data.user.firstName}!`);
        } else {
          console.error('Invalid login response structure:', data);
          toast.error('Invalid response from server');
        }
      },
      onError: (error: any) => {
        console.error('Login error details:', error);
        console.error('Error response:', error.response?.data);
        
        let message = 'Login failed';
        if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
          message = 'Cannot connect to server. Please make sure the server is running.';
        } else if (error.response?.data?.error?.message) {
          message = error.response.data.error.message;
        } else if (error.message) {
          message = error.message;
        }
        
        toast.error(message);
        throw error;
      },
    }
  );

  // Register mutation
  const registerMutation = useMutation(
    (userData: any) => authAPI.register(userData),
    {
      onSuccess: (data) => {
        if (data.success) {
          toast.success('Account created successfully!');
        }
      },
      onError: (error: any) => {
        const message = error.response?.data?.error?.message || 'Registration failed';
        toast.error(message);
        throw error;
      },
    }
  );

  const login = async (email: string, password: string) => {
    await loginMutation.mutateAsync({ email, password });
  };

  const register = async (userData: any) => {
    await registerMutation.mutateAsync(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    queryClient.clear();
    toast.success('Logged out successfully');
  };

  const value: AuthContextType = {
    user,
    loading: loading || verifyLoading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};