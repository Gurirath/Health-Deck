import type {
  CaseRecord,
  TriageState,
  Vitals,
  Medicine,
  DoctorUser,
  LoginCredentials,
  AuthResponse,
  PatientCaseStatus,
} from '../types/triage';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const TOKEN_STORAGE_KEY = 'healthdeck_token';

export class ApiService {
  private static token: string | null = null;
  private static onUnauthorizedCallback: (() => void) | null = null;
  private static isHandling401 = false;

  static setToken(token: string | null): void {
    this.token = token;
    if (token) {
      try {
        sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
      } catch {}
    } else {
      try {
        sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      } catch {}
    }
  }

  static getToken(): string | null {
    if (this.token) return this.token;
    try {
      const stored = sessionStorage.getItem(TOKEN_STORAGE_KEY);
      if (stored) {
        this.token = stored;
        return stored;
      }
    } catch {}
    return null;
  }

  static setOnUnauthorized(cb: () => void): void {
    this.onUnauthorizedCallback = cb;
  }

  private static triggerUnauthorized(): void {
    if (this.onUnauthorizedCallback && !this.isHandling401) {
      this.isHandling401 = true;
      try {
        this.onUnauthorizedCallback();
      } finally {
        setTimeout(() => {
          this.isHandling401 = false;
        }, 300);
      }
    }
  }

  private static async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isProtected = false,
    suppressUnauthorized = false
  ): Promise<{ data: T | null; error: string | null; status?: number }> {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      };

      if (isProtected) {
        const token = this.getToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      }

      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });

      if (!res.ok) {
        if (res.status === 401 && isProtected && !suppressUnauthorized && Boolean(this.getToken())) {
          this.triggerUnauthorized();
        }

        let errorMsg = `Backend Error (${res.status})`;
        try {
          const json = await res.json();
          if (json.detail) {
            errorMsg = typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail);
          } else {
            errorMsg = JSON.stringify(json);
          }
        } catch {
          const text = await res.text().catch(() => res.statusText);
          if (text) errorMsg = text;
        }
        return { data: null, error: errorMsg, status: res.status };
      }

      const data = await res.json();
      return { data, error: null, status: res.status };
    } catch (err: any) {
      return {
        data: null,
        error: err.message || 'Could not connect to Health Deck backend on port 8000.',
      };
    }
  }

  static async login(
    credentials: LoginCredentials
  ): Promise<{ data: AuthResponse | null; error: string | null }> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (res.data?.access_token) {
      this.setToken(res.data.access_token);
    }
    return { data: res.data, error: res.error };
  }

  static async getMe(
    tokenOverride?: string
  ): Promise<{ doctor: DoctorUser | null; error: string | null; status?: number }> {
    if (tokenOverride) {
      this.setToken(tokenOverride);
    }
    const res = await this.request<DoctorUser>('/auth/me', {}, true, true);
    return { doctor: res.data, error: res.error, status: res.status };
  }

  static async logout(): Promise<{ success: boolean }> {
    this.setToken(null);
    try {
      await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    } catch {}
    return { success: true };
  }

  static async checkHealth(): Promise<boolean> {
    const { data } = await this.request<{ ok: boolean }>('/');
    return Boolean(data?.ok);
  }

  static async startTriage(
    vitals: Vitals,
    symptomLocation: string,
    chiefComplaint: string,
    sessionId: string
  ): Promise<{ state: TriageState | null; error: string | null }> {
    const res = await this.request<TriageState>('/triage/start', {
      method: 'POST',
      body: JSON.stringify({
        vitals,
        symptom_location: symptomLocation,
        chief_complaint: chiefComplaint,
        session_id: sessionId,
      }),
    });

    if (res.data) {
      return { state: res.data, error: null };
    }
    return { state: null, error: res.error || 'Failed to start triage graph.' };
  }

  static async stepTriage(
    currentState: TriageState,
    answer: string
  ): Promise<{ state: TriageState | null; error: string | null }> {
    const res = await this.request<TriageState>('/triage/step', {
      method: 'POST',
      body: JSON.stringify({
        state: currentState,
        answer,
      }),
    });

    if (res.data) {
      return { state: res.data, error: null };
    }
    return { state: null, error: res.error || 'Failed to process answer with triage agent.' };
  }

  static async transcribeAudio(
    audioBlob: Blob
  ): Promise<{ text: string | null; error: string | null }> {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'speech.webm');

      const res = await fetch(`${API_BASE}/triage/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => res.statusText);
        return { text: null, error: `STT error (${res.status}): ${errText}` };
      }

      const data = await res.json();
      return { text: data.text || '', error: null };
    } catch (err: any) {
      return { text: null, error: err.message || 'Failed to send audio to transcription backend.' };
    }
  }

  static async saveCase(state: TriageState): Promise<{ id: number | null; error: string | null }> {
    const payload = {
      vitals: state.vitals,
      chief_complaint: state.chief_complaint,
      symptom_location: state.symptom_location,
      transcript: state.transcript,
      extracted: state.extracted || {},
      red_flags: state.red_flags || [],
      diagnosis: state.diagnosis || {},
      raw_llm_response: state.raw_llm_response || state.diagnosis || {},
      escalate: state.escalate,
      escalation_reason: state.escalation_reason || '',
      department: state.department || 'General Physician',
      solution_sources: state.solution_sources || [],
      image_analysis: state.image_analysis || null,
      session_id: state.session_id || '',
    };

    const res = await this.request<{ id: number }>('/cases', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (res.data) {
      return { id: res.data.id, error: null };
    }
    return { id: null, error: res.error || 'Could not file case to backend.' };
  }

  static async getAllCases(): Promise<{ cases: CaseRecord[]; error: string | null }> {
    const res = await this.request<CaseRecord[]>('/cases', {}, true);
    if (res.data) {
      return { cases: res.data, error: null };
    }
    return { cases: [], error: res.error };
  }

  static async getOpenCases(): Promise<{ cases: CaseRecord[]; error: string | null }> {
    const res = await this.request<CaseRecord[]>('/cases/open', {}, true);
    if (res.data) {
      return { cases: res.data, error: null };
    }
    return { cases: [], error: res.error };
  }

  static async getCase(
    caseId: number
  ): Promise<{ caseRecord: CaseRecord | null; error: string | null }> {
    const res = await this.request<CaseRecord>(`/cases/${caseId}`, {}, true);
    return { caseRecord: res.data, error: res.error };
  }

  static async getPatientStatus(
    caseId: number
  ): Promise<{ statusData: PatientCaseStatus | null; error: string | null }> {
    const res = await this.request<PatientCaseStatus>(`/cases/${caseId}/patient-status`, {}, false);
    return { statusData: res.data, error: res.error };
  }

  static async reviewCase(
    caseId: number,
    departmentOverride?: string
  ): Promise<{ success: boolean; error: string | null }> {
    const res = await this.request<CaseRecord>(
      `/cases/${caseId}/review`,
      {
        method: 'PATCH',
        body: JSON.stringify({ department_override: departmentOverride || null }),
      },
      true
    );
    return { success: Boolean(res.data), error: res.error };
  }

  static async prescribeCase(
    caseId: number,
    doctorName: string,
    medicines: Medicine[],
    notes: string
  ): Promise<{ caseRecord: CaseRecord | null; error: string | null }> {
    const res = await this.request<CaseRecord>(
      `/cases/${caseId}/prescribe`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          doctor_name: doctorName,
          medicines,
          notes,
        }),
      },
      true
    );
    return { caseRecord: res.data, error: res.error };
  }

  static async downloadReport(
    caseId: number
  ): Promise<{ success: boolean; error: string | null }> {
    try {
      const headers: Record<string, string> = {};
      const token = this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${API_BASE}/cases/${caseId}/report`, {
        headers,
      });

      if (!res.ok) {
        if (res.status === 401) {
          this.triggerUnauthorized();
          return { success: false, error: 'Session expired. Please log in again.' };
        }
        let errorMsg = `Report Error (${res.status})`;
        try {
          const json = await res.json();
          if (json.detail) errorMsg = json.detail;
        } catch {
          const text = await res.text().catch(() => res.statusText);
          if (text) errorMsg = text;
        }
        return { success: false, error: errorMsg };
      }

      const blob = await res.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `health_deck_case_${caseId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(objectUrl);

      return { success: true, error: null };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to download report.' };
    }
  }

  static getReportUrl(caseId: number): string {
    return `${API_BASE}/cases/${caseId}/report`;
  }

  static getUploadStatusUrl(sessionId: string): string {
    return `${API_BASE}/upload/${sessionId}/status`;
  }

  static async checkUploadStatus(sessionId: string): Promise<boolean> {
    const res = await this.request<{ uploaded: boolean }>(`/upload/${sessionId}/status`);
    return Boolean(res.data?.uploaded);
  }

  static getUploadPageUrl(sessionId: string): string {
    return `${API_BASE}/upload/${sessionId}`;
  }

  static getImageUrl(sessionId: string): string {
    return `${API_BASE}/upload/${sessionId}/image`;
  }

  static async uploadDirectImage(
    sessionId: string,
    file: File
  ): Promise<{ success: boolean; error: string | null }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/upload/${sessionId}`, {
        method: 'POST',
        body: formData,
      });
      return { success: res.ok, error: res.ok ? null : `Status ${res.status}` };
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  }
}

