import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, Activity, Thermometer, ShieldAlert, CheckCircle2, ArrowRight } from 'lucide-react';
import type { Vitals } from '../../../types/triage';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import { getVitalStatus, VITALS_META } from '../../../constants/vitalsDefaults';

interface VitalsScreenProps {
  initialVitals: Vitals;
  onConfirm: (vitals: Vitals) => void;
}

export const VitalsScreen: React.FC<VitalsScreenProps> = ({ initialVitals, onConfirm }) => {
  const [vitals, setVitals] = useState<Vitals>(initialVitals);
  const [activeTab, setActiveTab] = useState<'cards' | 'adjust'>('cards');

  const updateVital = (key: keyof Vitals, val: number) => {
    setVitals((prev) => ({ ...prev, [key]: val }));
  };

  const hrStatus = getVitalStatus('hr', vitals.hr);
  const spo2Status = getVitalStatus('spo2', vitals.spo2);
  const tempStatus = getVitalStatus('temp_c', vitals.temp_c);
  const bpStatus = getVitalStatus('systolic_bp', vitals.systolic_bp);

  const hasUrgent =
    hrStatus === 'urgent' ||
    spo2Status === 'urgent' ||
    tempStatus === 'urgent' ||
    bpStatus === 'urgent';

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-6 flex flex-col items-center">
      {/* Top Nia Guidance */}
      <div className="w-full flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
        <div className="flex items-center gap-4">
          <NiaCharacter pose={hasUrgent ? 'urgent' : 'guiding'} size="sm" />
          <NiaSpeechBubble
            message="Let's start with a few basic measurements."
            subMessage={
              hasUrgent
                ? "Some readings are outside typical ranges. We'll prioritize doctor review."
                : "Biometric sensors connected. Verify or fine-tune your readings below."
            }
          />
        </div>

        {/* Quick Simulation Presets for Kiosk Demo */}
        <div className="flex items-center gap-2 bg-white/70 backdrop-blur-md p-1.5 rounded-2xl border border-[#E2A3C7]/30">
          <button
            onClick={() =>
              setVitals({
                spo2: 98,
                temp_c: 37.0,
                hr: 75,
                systolic_bp: 120,
                diastolic_bp: 80,
              })
            }
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
              !hasUrgent
                ? 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/70'
                : 'text-[#60435F]/70 hover:text-[#60435F]'
            }`}
          >
            Normal Preset
          </button>
          <button
            onClick={() =>
              setVitals({
                spo2: 89,
                temp_c: 39.8,
                hr: 126,
                systolic_bp: 145,
                diastolic_bp: 95,
              })
            }
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all ${
              hasUrgent
                ? 'bg-[#E14D62]/20 text-[#C42239] border border-[#E14D62]/50'
                : 'text-[#60435F]/70 hover:text-[#60435F]'
            }`}
          >
            Simulate Alert
          </button>
        </div>
      </div>

      {/* Vitals Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 w-full mb-8">
        {/* Heart Rate Card */}
        <motion.div
          whileHover={{ y: -4 }}
          className="rounded-3xl bg-white/90 backdrop-blur-xl p-6 border border-white/80 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.09)] flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-2xl bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center">
              <Heart className="w-6 h-6 fill-[#D67AB1]/20 text-[#D67AB1]" />
            </div>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                hrStatus === 'urgent'
                  ? 'bg-[#E14D62]/15 text-[#C42239]'
                  : hrStatus === 'warning'
                  ? 'bg-[#D9822B]/15 text-[#9B5510]'
                  : 'bg-[#A8DCD9]/30 text-[#2B605E]'
              }`}
            >
              {hrStatus === 'urgent' ? 'Attention' : hrStatus === 'warning' ? 'Elevated' : 'Normal'}
            </span>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-[#60435F]/60">Heart Rate</p>
            <div className="flex items-baseline gap-1.5 my-1">
              <span className="text-4xl font-black text-[#60435F]">{vitals.hr}</span>
              <span className="text-sm font-bold text-[#60435F]/60">BPM</span>
            </div>
            <p className="text-xs text-[#60435F]/65">Resting pulse (60-100 BPM)</p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#E2A3C7]/20 flex items-center gap-2">
            <input
              type="range"
              min={40}
              max={150}
              value={vitals.hr}
              onChange={(e) => updateVital('hr', Number(e.target.value))}
              className="w-full accent-[#D67AB1] cursor-pointer"
            />
          </div>
        </motion.div>

        {/* SpO2 Blood Oxygen Card */}
        <motion.div
          whileHover={{ y: -4 }}
          className="rounded-3xl bg-white/90 backdrop-blur-xl p-6 border border-white/80 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.09)] flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-2xl bg-[#A8DCD9]/30 text-[#2B605E] flex items-center justify-center">
              <Activity className="w-6 h-6 text-[#2B605E]" />
            </div>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                spo2Status === 'urgent'
                  ? 'bg-[#E14D62]/15 text-[#C42239]'
                  : spo2Status === 'warning'
                  ? 'bg-[#D9822B]/15 text-[#9B5510]'
                  : 'bg-[#A8DCD9]/30 text-[#2B605E]'
              }`}
            >
              {spo2Status === 'urgent' ? 'Low Oxygen' : spo2Status === 'warning' ? 'Borderline' : 'Optimal'}
            </span>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-[#60435F]/60">Blood Oxygen</p>
            <div className="flex items-baseline gap-1.5 my-1">
              <span className="text-4xl font-black text-[#2B605E]">{vitals.spo2}%</span>
              <span className="text-sm font-bold text-[#60435F]/60">SpO2</span>
            </div>
            <p className="text-xs text-[#60435F]/65">Normal: 95% – 100%</p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#E2A3C7]/20 flex items-center gap-2">
            <input
              type="range"
              min={80}
              max={100}
              value={vitals.spo2}
              onChange={(e) => updateVital('spo2', Number(e.target.value))}
              className="w-full accent-[#A8DCD9] cursor-pointer"
            />
          </div>
        </motion.div>

        {/* Temperature Card */}
        <motion.div
          whileHover={{ y: -4 }}
          className="rounded-3xl bg-white/90 backdrop-blur-xl p-6 border border-white/80 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.09)] flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-2xl bg-[#E2A3C7]/25 text-[#96376D] flex items-center justify-center">
              <Thermometer className="w-6 h-6 text-[#96376D]" />
            </div>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                tempStatus === 'urgent'
                  ? 'bg-[#E14D62]/15 text-[#C42239]'
                  : tempStatus === 'warning'
                  ? 'bg-[#D9822B]/15 text-[#9B5510]'
                  : 'bg-[#A8DCD9]/30 text-[#2B605E]'
              }`}
            >
              {tempStatus === 'urgent' ? 'High Fever' : tempStatus === 'warning' ? 'Mild Fever' : 'Normal'}
            </span>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-[#60435F]/60">Body Temp</p>
            <div className="flex items-baseline gap-1.5 my-1">
              <span className="text-4xl font-black text-[#60435F]">{vitals.temp_c.toFixed(1)}</span>
              <span className="text-sm font-bold text-[#60435F]/60">°C</span>
            </div>
            <p className="text-xs text-[#60435F]/65">Baseline: 36.5°C – 37.5°C</p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#E2A3C7]/20 flex items-center gap-2">
            <input
              type="range"
              min={35.0}
              max={41.0}
              step={0.1}
              value={vitals.temp_c}
              onChange={(e) => updateVital('temp_c', parseFloat(e.target.value))}
              className="w-full accent-[#D67AB1] cursor-pointer"
            />
          </div>
        </motion.div>

        {/* Blood Pressure Card */}
        <motion.div
          whileHover={{ y: -4 }}
          className="rounded-3xl bg-white/90 backdrop-blur-xl p-6 border border-white/80 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.09)] flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-2xl bg-[#60435F]/10 text-[#60435F] flex items-center justify-center">
              <span className="font-black text-sm">BP</span>
            </div>
            <span
              className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                bpStatus === 'urgent'
                  ? 'bg-[#E14D62]/15 text-[#C42239]'
                  : bpStatus === 'warning'
                  ? 'bg-[#D9822B]/15 text-[#9B5510]'
                  : 'bg-[#A8DCD9]/30 text-[#2B605E]'
              }`}
            >
              {bpStatus === 'urgent' ? 'High BP' : bpStatus === 'warning' ? 'Elevated' : 'Optimal'}
            </span>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-[#60435F]/60">Blood Pressure</p>
            <div className="flex items-baseline gap-1 my-1">
              <span className="text-3xl font-black text-[#60435F]">{vitals.systolic_bp}</span>
              <span className="text-xl font-bold text-[#60435F]/50">/</span>
              <span className="text-2xl font-bold text-[#60435F]/80">{vitals.diastolic_bp}</span>
              <span className="text-xs font-bold text-[#60435F]/60 ml-1">mmHg</span>
            </div>
            <p className="text-xs text-[#60435F]/65">Target: 120/80 mmHg</p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#E2A3C7]/20 flex items-center gap-2">
            <input
              type="range"
              min={80}
              max={190}
              value={vitals.systolic_bp}
              onChange={(e) => updateVital('systolic_bp', Number(e.target.value))}
              className="w-full accent-[#60435F] cursor-pointer"
            />
          </div>
        </motion.div>
      </div>

      {/* Confirmation Call To Action */}
      <div className="w-full max-w-md flex flex-col items-center gap-3">
        <PrimaryButton
          size="xl"
          fullWidth
          onClick={() => onConfirm(vitals)}
          icon={<ArrowRight className="w-6 h-6" />}
        >
          Confirm Vitals & Continue →
        </PrimaryButton>
        <p className="text-xs text-[#60435F]/60 text-center">
          Measurements will be sent securely to the clinical triage dashboard.
        </p>
      </div>
    </div>
  );
};
