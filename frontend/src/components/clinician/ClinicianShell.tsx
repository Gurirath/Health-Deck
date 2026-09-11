import React, { useState, useEffect } from 'react';
import { HealthDeckLogo } from '../common/HealthDeckLogo';
import {
  LayoutDashboard,
  Users,
  FileText,
  Settings,
  ArrowLeft,
  RefreshCw,
  Bell,
  LogOut,
} from 'lucide-react';
import { StatCards } from './StatCards';
import { PatientQueue } from './PatientQueue';
import { ClinicalReports } from './ClinicalReports';
import { ClinicianSettings } from './ClinicianSettings';
import { CaseDetailDrawer } from './CaseDetailDrawer';
import type { CaseRecord } from '../../types/triage';
import { ApiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ClinicianShellProps {
  onSwitchToKiosk: () => void;
}

export const ClinicianShell: React.FC<ClinicianShellProps> = ({ onSwitchToKiosk }) => {
  const { currentUser, logout } = useAuth();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [activeNav, setActiveNav] = useState<'overview' | 'cases' | 'reports' | 'settings'>('overview');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogout = () => {
    setSelectedCase(null);
    logout();
  };

  const initials = currentUser?.full_name
    ? currentUser.full_name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((p) => p[0])
        .join('')
        .toUpperCase()
    : 'DR';

  const fetchCases = async () => {
    setIsLoading(true);
    const { cases: data } = await ApiService.getAllCases();
    setIsLoading(false);
    if (data) {
      setCases(data);
    }
  };

  useEffect(() => {
    fetchCases();
    const timer = setInterval(fetchCases, 8000);
    return () => clearInterval(timer);
  }, []);

  const handleCaseUpdated = (updated: CaseRecord) => {
    setSelectedCase(updated);
    setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  };

  return (
    <div className="min-h-screen flex bg-[#FDF7FA] text-[#60435F]">
      {/* Left Sidebar */}
      <aside className="w-64 bg-white/90 backdrop-blur-xl border-r border-[#E2A3C7]/30 flex flex-col justify-between p-5 shrink-0 hidden md:flex">
        <div className="flex flex-col gap-8">
          <HealthDeckLogo size="sm" />

          {/* Navigation Links */}
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveNav('overview')}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-xs font-bold transition-all cursor-pointer ${
                activeNav === 'overview'
                  ? 'bg-[#60435F] text-white shadow-md'
                  : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Overview & Queue</span>
            </button>

            <button
              onClick={() => setActiveNav('cases')}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-xs font-bold transition-all cursor-pointer ${
                activeNav === 'cases'
                  ? 'bg-[#60435F] text-white shadow-md'
                  : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
              }`}
            >
              <Users className="w-4 h-4" />
              <span>All Patients</span>
            </button>

            <button
              onClick={() => setActiveNav('reports')}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-xs font-bold transition-all cursor-pointer ${
                activeNav === 'reports'
                  ? 'bg-[#60435F] text-white shadow-md'
                  : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Clinical Reports</span>
            </button>

            <button
              onClick={() => setActiveNav('settings')}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-xs font-bold transition-all cursor-pointer ${
                activeNav === 'settings'
                  ? 'bg-[#60435F] text-white shadow-md'
                  : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
          </nav>
        </div>

        {/* Doctor Profile & Actions */}
        <div className="pt-4 border-t border-[#E2A3C7]/30 flex flex-col gap-2.5">
          <div className="flex items-center gap-3 p-2.5 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30 shadow-sm">
            <div className="w-9 h-9 rounded-xl bg-[#D67AB1]/20 text-[#D67AB1] flex items-center justify-center font-bold text-xs tracking-tight">
              {initials}
            </div>
            <div className="overflow-hidden min-w-0 flex-1">
              <p className="text-xs font-bold text-[#60435F] truncate">
                {currentUser?.full_name || 'Attending Physician'}
              </p>
              <p className="text-[10px] text-[#60435F]/65 truncate">
                {currentUser?.department || 'General Physician'}
                {currentUser?.medical_license ? ` • ${currentUser.medical_license}` : ''}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <button
              onClick={onSwitchToKiosk}
              className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#60435F]/10 hover:bg-[#60435F]/20 text-[#60435F] font-bold text-xs transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Switch to Kiosk</span>
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-[#FDF0F2] hover:bg-[#FCE0E5] text-[#C42239] font-bold text-xs border border-[#F9B4BF]/50 transition-all cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Clinical Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navbar */}
        <header className="bg-white/80 backdrop-blur-xl border-b border-[#E2A3C7]/30 px-6 py-4 flex items-center justify-between sticky top-0 z-30">
          <div>
            <h1 className="text-xl sm:text-2xl font-black text-[#60435F] tracking-tight">
              {activeNav === 'overview' && (currentUser?.full_name ? `Welcome, ${currentUser.full_name}` : 'Clinician Workspace')}
              {activeNav === 'cases' && 'All Patients Directory'}
              {activeNav === 'reports' && 'Clinical Reports Repository'}
              {activeNav === 'settings' && 'Clinician Station Settings'}
            </h1>
            <p className="text-xs text-[#60435F]/60">
              {activeNav === 'overview' && `${currentUser?.department || 'Emergency Triage Station'} • Live Patient Feed & Review`}
              {activeNav === 'cases' && 'Comprehensive historical directory of all intake admissions and triage records'}
              {activeNav === 'reports' && 'Signed clinical reports, issued prescriptions, and hospital discharge summaries'}
              {activeNav === 'settings' && `${currentUser?.full_name || 'Doctor'} • Station security and diagnostics`}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onSwitchToKiosk}
              className="md:hidden flex items-center gap-1 text-xs font-bold text-[#60435F] bg-white border border-[#E2A3C7]/40 px-3 py-1.5 rounded-xl cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Kiosk</span>
            </button>

            <button
              onClick={handleLogout}
              title="Log Out"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#FDF0F2] hover:bg-[#FCE0E5] text-[#C42239] text-xs font-bold border border-[#F9B4BF]/50 transition-all cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Log Out</span>
            </button>

            <button
              onClick={fetchCases}
              disabled={isLoading}
              title="Refresh queue"
              className="p-2.5 rounded-xl bg-white hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] transition-all cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>

            <div className="w-8 h-8 rounded-xl bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center">
              <Bell className="w-4 h-4" />
            </div>
          </div>
        </header>

        {/* Mobile Navigation Tabs */}
        <div className="md:hidden flex items-center gap-2 overflow-x-auto px-6 py-2.5 bg-white/70 border-b border-[#E2A3C7]/30">
          <button
            onClick={() => setActiveNav('overview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
              activeNav === 'overview'
                ? 'bg-[#60435F] text-white shadow-xs'
                : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Overview</span>
          </button>
          <button
            onClick={() => setActiveNav('cases')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
              activeNav === 'cases'
                ? 'bg-[#60435F] text-white shadow-xs'
                : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>All Patients</span>
          </button>
          <button
            onClick={() => setActiveNav('reports')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
              activeNav === 'reports'
                ? 'bg-[#60435F] text-white shadow-xs'
                : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Reports</span>
          </button>
          <button
            onClick={() => setActiveNav('settings')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
              activeNav === 'settings'
                ? 'bg-[#60435F] text-white shadow-xs'
                : 'text-[#60435F]/70 hover:bg-[#E2A3C7]/15'
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Settings</span>
          </button>
        </div>

        {/* Content Body */}
        <main className="p-6 flex flex-col gap-6 max-w-7xl w-full mx-auto">
          {activeNav === 'overview' && (
            <>
              <StatCards cases={cases} />
              <PatientQueue
                cases={cases}
                onSelectCase={(c) => setSelectedCase(c)}
                onRefresh={fetchCases}
                isLoading={isLoading}
              />
            </>
          )}

          {activeNav === 'cases' && (
            <>
              <StatCards cases={cases} />
              <PatientQueue
                cases={cases}
                onSelectCase={(c) => setSelectedCase(c)}
                onRefresh={fetchCases}
                isLoading={isLoading}
              />
            </>
          )}

          {activeNav === 'reports' && (
            <ClinicalReports
              cases={cases}
              onSelectCase={(c) => setSelectedCase(c)}
              onRefresh={fetchCases}
              isLoading={isLoading}
            />
          )}

          {activeNav === 'settings' && (
            <ClinicianSettings onSwitchToKiosk={onSwitchToKiosk} />
          )}
        </main>
      </div>

      {/* Full Dossier Modal Drawer */}
      {selectedCase && (
        <CaseDetailDrawer
          caseRecord={selectedCase}
          onClose={() => setSelectedCase(null)}
          onCaseUpdated={handleCaseUpdated}
        />
      )}
    </div>
  );
};
