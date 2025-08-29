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
    // Send JSON data instead of form data for the Flask backend
    const response = await apiClient.post<any>('/auth/login', {
      username: credentials.username,
      password: credentials.password
    });

    // Flask backend returns: { success: true, user: {...}, message: string }
    if (response.success && response.user) {
      return {
        user: response.user,
        message: response.message
      };
    } else {
      throw new Error(response.message || 'Login failed');
    }
  }

  static async register(data: RegisterRequest): Promise<User> {
    return apiClient.post<User>('/auth/register', data);
  }

  static async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      // Clear local storage - remove token-based storage
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

  // Session management utilities (no tokens needed)
  static getStoredUser(): User | null {
    const userData = localStorage.getItem('user');
    return userData ? JSON.parse(userData) : null;
  }

  static storeAuthData(loginResponse: LoginResponse): void {
    localStorage.setItem('user', JSON.stringify(loginResponse.user));
  }

  static clearAuthData(): void {
    localStorage.removeItem('user');
  }

  static isAuthenticated(): boolean {
    // For session-based auth, we just check if user exists in storage
    const user = this.getStoredUser();
    return user !== null;
  }
}
