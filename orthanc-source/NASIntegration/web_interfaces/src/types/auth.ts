export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role?: UserRole;
}

export type UserRole = 
  | 'admin' 
  | 'doctor' 
  | 'nurse' 
  | 'technician' 
  | 'radiologist' 
  | 'patient';

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface PermissionRequest {
  patient_id: number;
  requesting_doctor_id: number;
  permission_type: 'view' | 'edit' | 'download';
  reason: string;
  expiry_date?: string;
}

export interface PermissionResponse {
  id: number;
  patient_id: number;
  requesting_doctor_id: number;
  approving_doctor_id?: number;
  permission_type: string;
  reason: string;
  status: 'pending' | 'approved' | 'denied' | 'expired';
  created_at: string;
  expiry_date?: string;
  approved_at?: string;
}
