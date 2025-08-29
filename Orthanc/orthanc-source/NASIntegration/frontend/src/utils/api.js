import axios from 'axios';
import toast from 'react-hot-toast';

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth headers if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;
          
        case 403:
          // Forbidden - check if 2FA is required
          if (data.requires_2fa) {
            window.location.href = '/2fa/verify';
          } else if (data.requires_2fa_setup) {
            window.location.href = '/2fa/setup';
          } else {
            toast.error(data.error || 'Access denied');
          }
          break;
          
        case 404:
          toast.error('Resource not found');
          break;
          
        case 500:
          toast.error('Server error. Please try again later.');
          break;
          
        default:
          // Don't show toast for other errors - let components handle them
          break;
      }
    } else if (error.request) {
      // Network error
      toast.error('Network error. Please check your connection.');
    }
    
    return Promise.reject(error);
  }
);

export default api;