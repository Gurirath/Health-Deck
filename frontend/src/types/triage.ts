export interface Vitals {
  spo2: number;
  temp_c: number;
  hr: number;
  systolic_bp: number;
  diastolic_bp: number;
}

export interface TranscriptTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface DiagnosisData {
  probable_diagnosis?: string;
  differentials?: Array<string | { name?: string; diagnosis?: string }>;
  confidence?: number;
  category?: string;
  reasoning?: string;
  self_care_advice?: string;
  safety_note?: string;
}

export interface ImageAnalysis {
  description?: string;
  visual_characteristics?: string[];
  note?: string;
}

export interface TriageState {
  vitals: Vitals;
  chief_complaint: string;
  symptom_location: string;
  transcript: TranscriptTurn[];
  extracted: Record<string, any>;
  turn_count: number;
  ready_to_diagnose: boolean;
  red_flags: string[];
  next_question: string;
  diagnosis: DiagnosisData;
  raw_llm_response?: Record<string, any>;
  escalate: boolean;
  escalation_reason: string;
  department: string;
  solution_sources: string[];
  image_analysis?: ImageAnalysis | null;
  status: 'awaiting_answer' | 'complete' | string;
  session_id?: string;
}

export interface Medicine {
  name: string;
  dosage_per_day: string;
  remark: string;
}

export interface CaseRecord {
  id: number;
  created_at: string;
  vitals: Vitals;
  chief_complaint: string;
  symptom_location: string;
  transcript: TranscriptTurn[];
  extracted: Record<string, any>;
  red_flags: string[];
  diagnosis: DiagnosisData;
  raw_llm_response?: Record<string, any>;
  solution_sources: string[];
  image_analysis?: ImageAnalysis | null;
  session_id?: string;
  photo_path?: string | null;
  confidence: number;
  department: string;
  department_override?: string | null;
  effective_department: string;
  escalate: boolean;
  escalation_reason: string;
  reviewed: boolean;
  reviewed_at?: string | null;
  status: 'pending' | 'prescribed' | string;
  doctor_name?: string | null;
  prescription_medicines: Medicine[];
  doctor_notes?: string | null;
  prescribed_at?: string | null;
  report_pdf_path?: string | null;
}

export type BodyRegionId =
  | 'head'
  | 'neck'
  | 'chest'
  | 'abdomen'
  | 'back'
  | 'arm'
  | 'hand'
  | 'leg'
  | 'foot'
  | 'other';

export type KioskScreen =
  | 'welcome'
  | 'vitals'
  | 'complaint'
  | 'body_map'
  | 'conversation'
  | 'photo'
  | 'processing'
  | 'completion';

export type AppMode = 'kiosk' | 'clinician';
