import { apiClient } from './api';
import type { 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest, 
  User,
  PermissionRequest,
  PermissionResponse
} from '../types/auth';

export class AuthService {
  // Authentication endpoints
  static async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  }

  static async register(data: RegisterRequest): Promise<User> {
    return apiClient.post<User>('/auth/register', data);
  }

  static async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      // Clear local storage regardless of API response
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
  }

  static async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me');
  }

  static async refreshToken(): Promise<LoginResponse> {
    return apiClient.post<LoginResponse>('/auth/refresh');
  }

  // Permission management
  static async requestPermission(request: PermissionRequest): Promise<PermissionResponse> {
    return apiClient.post<PermissionResponse>('/authorizations/request', request);
  }

  static async approvePermission(requestId: number): Promise<PermissionResponse> {
    return apiClient.post<PermissionResponse>(`/authorizations/${requestId}/approve`);
  }

  static async denyPermission(requestId: number, reason?: string): Promise<PermissionResponse> {
    return apiClient.post<PermissionResponse>(`/authorizations/${requestId}/deny`, { reason });
  }

  static async getMyPermissions(): Promise<PermissionResponse[]> {
    return apiClient.get<PermissionResponse[]>('/authorizations/my-requests');
  }

  static async getPendingPermissions(): Promise<PermissionResponse[]> {
    return apiClient.get<PermissionResponse[]>('/authorizations/pending');
  }

  // Token management utilities
  static getStoredToken(): string | null {
    return localStorage.getItem('access_token');
  }

  static getStoredUser(): User | null {
    const userData = localStorage.getItem('user');
    return userData ? JSON.parse(userData) : null;
  }

  static storeAuthData(loginResponse: LoginResponse): void {
    localStorage.setItem('access_token', loginResponse.access_token);
    localStorage.setItem('user', JSON.stringify(loginResponse.user));
  }

  static clearAuthData(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }

  static isAuthenticated(): boolean {
    const token = this.getStoredToken();
    const user = this.getStoredUser();
    return !!(token && user);
  }
}
