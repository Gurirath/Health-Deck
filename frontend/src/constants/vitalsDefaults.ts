import type { Vitals } from '../types/triage';

export const DEFAULT_VITALS: Vitals = {
  spo2: 98,
  temp_c: 37.0,
  hr: 75,
  systolic_bp: 120,
  diastolic_bp: 80,
};

export interface VitalMeta {
  key: keyof Vitals;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  normalMin: number;
  normalMax: number;
  redFlagMin?: number;
  redFlagMax?: number;
  description: string;
}

export const VITALS_META: VitalMeta[] = [
  {
    key: 'hr',
    label: 'Heart Rate',
    unit: 'BPM',
    min: 40,
    max: 160,
    step: 1,
    normalMin: 60,
    normalMax: 100,
    redFlagMin: 50,
    redFlagMax: 120,
    description: 'Resting pulse measured via biometric sensor',
  },
  {
    key: 'spo2',
    label: 'Blood Oxygen',
    unit: '%',
    min: 80,
    max: 100,
    step: 1,
    normalMin: 95,
    normalMax: 100,
    redFlagMin: 92,
    description: 'Peripheral oxygen saturation (SpO2)',
  },
  {
    key: 'temp_c',
    label: 'Temperature',
    unit: '°C',
    min: 35.0,
    max: 41.0,
    step: 0.1,
    normalMin: 36.4,
    normalMax: 37.5,
    redFlagMax: 39.5,
    description: 'Infrared skin/temporal body temperature',
  },
  {
    key: 'systolic_bp',
    label: 'Blood Pressure',
    unit: 'mmHg',
    min: 70,
    max: 200,
    step: 1,
    normalMin: 100,
    normalMax: 130,
    redFlagMin: 90,
    redFlagMax: 180,
    description: 'Cuff pressure (Systolic / Diastolic)',
  },
];

export function getVitalStatus(key: keyof Vitals, val: number): 'normal' | 'warning' | 'urgent' {
  if (key === 'spo2') {
    if (val < 92) return 'urgent';
    if (val < 95) return 'warning';
    return 'normal';
  }
  if (key === 'temp_c') {
    if (val > 39.5) return 'urgent';
    if (val > 37.5) return 'warning';
    return 'normal';
  }
  if (key === 'hr') {
    if (val > 120 || val < 50) return 'urgent';
    if (val > 100 || val < 60) return 'warning';
    return 'normal';
  }
  if (key === 'systolic_bp') {
    if (val > 180 || val < 90) return 'urgent';
    if (val > 135 || val < 100) return 'warning';
    return 'normal';
  }
  return 'normal';
}
