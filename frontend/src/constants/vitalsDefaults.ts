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

export type VitalStatusLevel = 'normal' | 'warning' | 'urgent';

export interface VitalEvaluation {
  status: VitalStatusLevel;
  label: string;
  badgeClass: string;
  description?: string;
}

export function getBloodPressureStatus(systolic: number, diastolic: number): VitalEvaluation {
  // Urgent: Hypertensive crisis or severe hypotension
  if (systolic >= 180 || diastolic >= 120) {
    return {
      status: 'urgent',
      label: 'High BP (Urgent)',
      badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
      description: 'Hypertensive crisis — immediate attention required',
    };
  }
  if (systolic < 90 || diastolic < 50) {
    return {
      status: 'urgent',
      label: 'Low BP (Urgent)',
      badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
      description: 'Severe hypotension — clinical attention required',
    };
  }

  // High BP (Stage 1 / Stage 2 hypertension)
  if (systolic >= 140 || diastolic >= 90) {
    return {
      status: 'warning',
      label: 'High BP',
      badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
      description: 'High blood pressure (Hypertension)',
    };
  }

  // Elevated BP
  if (systolic >= 121 || diastolic >= 81) {
    return {
      status: 'warning',
      label: 'Elevated',
      badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
      description: 'Slightly above optimal range',
    };
  }

  // Mild Low BP
  if (systolic < 100 || diastolic < 60) {
    return {
      status: 'warning',
      label: 'Low BP',
      badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
      description: 'Mildly low blood pressure',
    };
  }

  // Normal / Optimal: 100-120 / 60-80
  return {
    status: 'normal',
    label: 'Optimal',
    badgeClass: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70',
    description: 'Within healthy target range',
  };
}

export function getVitalEvaluation(key: keyof Vitals, val: number, secondaryVal?: number): VitalEvaluation {
  if (key === 'systolic_bp' || key === 'diastolic_bp') {
    const sys = key === 'systolic_bp' ? val : (secondaryVal ?? 120);
    const dia = key === 'diastolic_bp' ? val : (secondaryVal ?? 80);
    return getBloodPressureStatus(sys, dia);
  }

  if (key === 'spo2') {
    if (val < 92) {
      return {
        status: 'urgent',
        label: 'Low Oxygen',
        badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
        description: 'Critically low oxygen saturation',
      };
    }
    if (val < 95) {
      return {
        status: 'warning',
        label: 'Borderline',
        badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
        description: 'Slightly lower than typical baseline',
      };
    }
    return {
      status: 'normal',
      label: 'Optimal',
      badgeClass: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70',
      description: 'Normal blood oxygen saturation (95-100%)',
    };
  }

  if (key === 'temp_c') {
    if (val >= 39.5) {
      return {
        status: 'urgent',
        label: 'High Fever',
        badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
        description: 'High temperature requiring clinical care',
      };
    }
    if (val < 35.0) {
      return {
        status: 'urgent',
        label: 'Hypothermia',
        badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
        description: 'Abnormally low body temperature',
      };
    }
    if (val > 37.5) {
      return {
        status: 'warning',
        label: 'Mild Fever',
        badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
        description: 'Elevated temperature',
      };
    }
    if (val < 36.0) {
      return {
        status: 'warning',
        label: 'Low Temp',
        badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
        description: 'Slightly low body temperature',
      };
    }
    return {
      status: 'normal',
      label: 'Normal',
      badgeClass: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70',
      description: 'Typical body temperature (36.4°C - 37.5°C)',
    };
  }

  if (key === 'hr') {
    if (val > 130) {
      return {
        status: 'urgent',
        label: 'Tachycardia',
        badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
        description: 'Significantly elevated heart rate',
      };
    }
    if (val < 45) {
      return {
        status: 'urgent',
        label: 'Severe Bradycardia',
        badgeClass: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/30',
        description: 'Significantly low resting heart rate',
      };
    }
    if (val > 100) {
      return {
        status: 'warning',
        label: 'Elevated Pulse',
        badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
        description: 'Above typical resting pulse range',
      };
    }
    if (val < 60) {
      return {
        status: 'warning',
        label: 'Low Pulse',
        badgeClass: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/30',
        description: 'Below typical resting pulse range',
      };
    }
    return {
      status: 'normal',
      label: 'Normal',
      badgeClass: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70',
      description: 'Healthy resting pulse (60-100 BPM)',
    };
  }

  return {
    status: 'normal',
    label: 'Normal',
    badgeClass: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70',
  };
}

export function getVitalStatus(key: keyof Vitals, val: number): VitalStatusLevel {
  return getVitalEvaluation(key, val).status;
}
