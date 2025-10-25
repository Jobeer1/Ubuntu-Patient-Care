import { apiClient } from './api';

export interface Doctor {
  id: number;
  full_name: string;
  email: string;
  hpcsa_number: string;
  practice_number: string;
  qualification_primary: string;
  qualification_additional?: string;
  subspecialty?: string;
  practice_address_line1: string;
  practice_address_line2?: string;
  practice_city: string;
  practice_province: string;
  practice_postal_code: string;
  contact_number: string;
  emergency_contact_number?: string;
  years_experience: number;
  hospital_affiliations?: string;
  languages_spoken?: string;
  consultation_fee?: number;
  bio?: string;
  website?: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'inactive' | 'pending';
}

export interface CreateDoctorRequest {
  full_name: string;
  email: string;
  hpcsa_number: string;
  practice_number: string;
  qualification_primary: string;
  qualification_additional?: string;
  subspecialty?: string;
  practice_address_line1: string;
  practice_address_line2?: string;
  practice_city: string;
  practice_province: string;
  practice_postal_code: string;
  contact_number: string;
  emergency_contact_number?: string;
  years_experience: number;
  hospital_affiliations?: string;
  languages_spoken?: string;
  consultation_fee?: number;
  bio?: string;
  website?: string;
}

export interface UpdateDoctorRequest extends Partial<CreateDoctorRequest> {
  status?: 'active' | 'inactive' | 'pending';
}

export interface DoctorListResponse {
  doctors: Doctor[];
  total: number;
  page: number;
  per_page: number;
}

class DoctorService {
  async getDoctors(page = 1, perPage = 10, search = ''): Promise<DoctorListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    });

    if (search) {
      params.append('search', search);
    }

    return await apiClient.get<DoctorListResponse>(`/doctors?${params}`);
  }

  async getDoctor(id: number): Promise<Doctor> {
    return await apiClient.get<Doctor>(`/doctors/${id}`);
  }

  async createDoctor(doctorData: CreateDoctorRequest): Promise<Doctor> {
    return await apiClient.post<Doctor>('/doctors', doctorData);
  }

  async updateDoctor(id: number, doctorData: UpdateDoctorRequest): Promise<Doctor> {
    return await apiClient.put<Doctor>(`/doctors/${id}`, doctorData);
  }

  async deleteDoctor(id: number): Promise<void> {
    await apiClient.delete<void>(`/doctors/${id}`);
  }

  async validateHPCSA(hpcsaNumber: string): Promise<{ valid: boolean; details?: any }> {
    return await apiClient.post<{ valid: boolean; details?: any }>('/doctors/validate-hpcsa', {
      hpcsa_number: hpcsaNumber,
    });
  }

  async getDoctorStats(): Promise<{
    total: number;
    active: number;
    inactive: number;
    pending: number;
  }> {
    return await apiClient.get<{
      total: number;
      active: number;
      inactive: number;
      pending: number;
    }>('/doctors/stats');
  }
}

export const doctorService = new DoctorService();
