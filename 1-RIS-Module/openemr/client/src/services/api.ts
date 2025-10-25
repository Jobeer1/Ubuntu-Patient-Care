import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't redirect on login page or if it's a login request
    if (error.response?.status === 401 && 
        !window.location.pathname.includes('/login') && 
        !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }).then(res => res.data),
  
  register: (userData: any) =>
    api.post('/auth/register', userData).then(res => res.data),
  
  verifyToken: () =>
    api.get('/auth/verify').then(res => res.data),
  
  logout: () =>
    api.post('/auth/logout').then(res => res.data),
};

// Tasks API
export const tasksAPI = {
  getTasks: () =>
    api.get('/tasks').then(res => res.data),
  
  createTask: (taskData: any) =>
    api.post('/tasks', taskData).then(res => res.data),
  
  updateTask: (id: string, taskData: any) =>
    api.put(`/tasks/${id}`, taskData).then(res => res.data),
  
  deleteTask: (id: string) =>
    api.delete(`/tasks/${id}`).then(res => res.data),
};

// Notes API
export const notesAPI = {
  getNotes: () =>
    api.get('/notes').then(res => res.data),
  
  getNote: (id: string) =>
    api.get(`/notes/${id}`).then(res => res.data),
  
  createNote: (noteData: any) =>
    api.post('/notes', noteData).then(res => res.data),
  
  updateNote: (id: string, noteData: any) =>
    api.put(`/notes/${id}`, noteData).then(res => res.data),
  
  deleteNote: (id: string) =>
    api.delete(`/notes/${id}`).then(res => res.data),
};

export default api;