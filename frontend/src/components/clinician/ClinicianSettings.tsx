import React, { useState, useEffect } from 'react';
import {
  User,
  ShieldCheck,
  Building,
  CreditCard,
  Mail,
  Server,
  Database,
  Activity,
  ArrowLeft,
  LogOut,
  CheckCircle2,
  Lock,
  Cpu,
  RefreshCw,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { ApiService } from '../../services/api';

interface ClinicianSettingsProps {
  onSwitchToKiosk: () => void;
}

export const ClinicianSettings: React.FC<ClinicianSettingsProps> = ({ onSwitchToKiosk }) => {
  const { currentUser, logout } = useAuth();
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [isCheckingBackend, setIsCheckingBackend] = useState(false);

  const checkHealth = async () => {
    setIsCheckingBackend(true);
    const ok = await ApiService.checkHealth();
    setBackendOk(ok);
    setIsCheckingBackend(false);
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const initials = currentUser?.full_name
    ? currentUser.full_name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((p) => p[0])
        .join('')
        .toUpperCase()
    : 'DR';

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] p-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-[#60435F]">Clinician Station Settings</h2>
          <p className="text-xs text-[#60435F]/65 mt-0.5">
            Physician profile credentials, station diagnostics, and clinical security status.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/60">
            <ShieldCheck className="w-4 h-4" />
            Authenticated Physician
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Attending Physician Profile Card */}
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 rounded-2xl bg-[#D67AB1]/20 text-[#D67AB1] flex items-center justify-center font-black text-2xl tracking-tight border border-[#D67AB1]/30">
                {initials}
              </div>
              <div>
                <h3 className="text-lg font-bold text-[#60435F]">
                  {currentUser?.full_name || 'Attending Physician'}
                </h3>
                <p className="text-xs text-[#60435F]/65 font-medium">
                  {currentUser?.department || 'General Physician'} • Role:{' '}
                  <span className="capitalize font-bold text-[#D67AB1]">
                    {currentUser?.role || 'doctor'}
                  </span>
                </p>
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-[#2B605E] font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Active Session (Verified)</span>
                </div>
              </div>
            </div>

            <div className="space-y-3 border-t border-[#E2A3C7]/25 pt-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#60435F]/60 flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-[#D67AB1]" />
                  Username
                </span>
                <span className="font-mono font-bold text-[#60435F]">
                  {currentUser?.username || 'dr ary'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-[#60435F]/60 flex items-center gap-2">
                  <CreditCard className="w-3.5 h-3.5 text-[#D67AB1]" />
                  Medical License
                </span>
                <span className="font-mono font-bold text-[#60435F]">
                  {currentUser?.medical_license || 'MD-OFFICIAL'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-[#60435F]/60 flex items-center gap-2">
                  <Building className="w-3.5 h-3.5 text-[#D67AB1]" />
                  Department
                </span>
                <span className="font-bold text-[#60435F]">
                  {currentUser?.department || 'General Physician'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-[#60435F]/60 flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-[#D67AB1]" />
                  Hospital Email
                </span>
                <span className="text-[#60435F]/80">
                  {currentUser?.email || 'dr.ary@hospital.internal'}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#E2A3C7]/25 bg-[#FAF4F8]/50 p-3.5 rounded-2xl">
            <p className="text-[11px] text-[#60435F]/70 leading-relaxed flex items-start gap-1.5">
              <Lock className="w-3.5 h-3.5 text-[#60435F]/50 shrink-0 mt-0.5" />
              <span>
                Physician credentials, license status, and clinical role assignments are provisioned
                by Hospital IT and cannot be modified from the local kiosk terminal.
              </span>
            </p>
          </div>
        </div>

        {/* Station Diagnostics & Security Card */}
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-[#60435F] flex items-center gap-2">
                <Server className="w-4 h-4 text-[#D67AB1]" />
                Station Diagnostics
              </h3>
              <button
                onClick={checkHealth}
                disabled={isCheckingBackend}
                className="p-1.5 rounded-lg hover:bg-[#E2A3C7]/20 text-[#60435F] transition-all cursor-pointer"
                title="Re-check backend health"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isCheckingBackend ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="space-y-3.5">
              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Activity className="w-4 h-4 text-[#D67AB1]" />
                  <div>
                    <p className="text-xs font-bold text-[#60435F]">Backend API Service</p>
                    <p className="text-[10px] text-[#60435F]/60">http://localhost:8000</p>
                  </div>
                </div>
                <span
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                    backendOk
                      ? 'bg-[#A8DCD9]/30 text-[#2B605E]'
                      : 'bg-[#FDF0F2] text-[#C42239]'
                  }`}
                >
                  {backendOk ? 'Connected (200 OK)' : 'Offline / Error'}
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-[#60435F]" />
                  <div>
                    <p className="text-xs font-bold text-[#60435F]">Database Engine</p>
                    <p className="text-[10px] text-[#60435F]/60">healthdeck.db (SQLite Clinical Store)</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-[#60435F]/10 text-[#60435F]">
                  Local Persistent
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Cpu className="w-4 h-4 text-[#D67AB1]" />
                  <div>
                    <p className="text-xs font-bold text-[#60435F]">Security & Authentication</p>
                    <p className="text-[10px] text-[#60435F]/60">JWT Bearer Token (12-Hour Expiration)</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-[#A8DCD9]/30 text-[#2B605E]">
                  Enforced
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 pt-4 border-t border-[#E2A3C7]/25 flex flex-col sm:flex-row gap-3">
            <button
              onClick={onSwitchToKiosk}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[#60435F]/10 hover:bg-[#60435F]/20 text-[#60435F] text-xs font-bold transition-all cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Kiosk</span>
            </button>

            <button
              onClick={logout}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[#FDF0F2] hover:bg-[#FCE0E5] text-[#C42239] text-xs font-bold border border-[#F9B4BF]/50 transition-all cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span>End Doctor Session</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
