import type { CaseRecord, TriageState, Vitals, Medicine } from '../types/triage';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class ApiService {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<{ data: T | null; error: string | null }> {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
      });

      if (!res.ok) {
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
        return { data: null, error: errorMsg };
      }

      const data = await res.json();
      return { data, error: null };
    } catch (err: any) {
      return { data: null, error: err.message || 'Could not connect to Health Deck backend on port 8000.' };
    }
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

  static async getOpenCases(): Promise<{ cases: CaseRecord[]; error: string | null }> {
    const res = await this.request<CaseRecord[]>('/cases/open');
    if (res.data) {
      return { cases: res.data, error: null };
    }
    return { cases: [], error: res.error };
  }

  static async getCase(caseId: number): Promise<{ caseRecord: CaseRecord | null; error: string | null }> {
    const res = await this.request<CaseRecord>(`/cases/${caseId}`);
    return { caseRecord: res.data, error: res.error };
  }

  static async reviewCase(
    caseId: number,
    departmentOverride?: string
  ): Promise<{ success: boolean; error: string | null }> {
    const res = await this.request<CaseRecord>(`/cases/${caseId}/review`, {
      method: 'PATCH',
      body: JSON.stringify({ department_override: departmentOverride || null }),
    });
    return { success: Boolean(res.data), error: res.error };
  }

  static async prescribeCase(
    caseId: number,
    doctorName: string,
    medicines: Medicine[],
    notes: string
  ): Promise<{ caseRecord: CaseRecord | null; error: string | null }> {
    const res = await this.request<CaseRecord>(`/cases/${caseId}/prescribe`, {
      method: 'PATCH',
      body: JSON.stringify({
        doctor_name: doctorName,
        medicines,
        notes,
      }),
    });
    return { caseRecord: res.data, error: res.error };
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

