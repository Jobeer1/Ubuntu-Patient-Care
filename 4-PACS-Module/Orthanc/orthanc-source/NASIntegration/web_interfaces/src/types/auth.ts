export interface User {
  id: string;
  username: string;
  email: string;
  name: string;
  role: string;
  facility: string;
  province: string;
  session_token?: string;
  login_time?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  message?: string;
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
