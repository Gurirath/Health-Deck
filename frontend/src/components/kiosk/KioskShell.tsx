import React from 'react';
import { HealthDeckLogo } from '../common/HealthDeckLogo';
import { RotateCcw, Stethoscope, AlertCircle } from 'lucide-react';
import type { KioskScreen } from '../../types/triage';

interface KioskShellProps {
  currentScreen: KioskScreen;
  onReset: () => void;
  onSwitchToClinician: () => void;
  children: React.ReactNode;
}

export const KioskShell: React.FC<KioskShellProps> = ({
  currentScreen,
  onReset,
  onSwitchToClinician,
  children,
}) => {
  // Step indicator progression in exact required order
  const steps: { id: KioskScreen; label: string }[] = [
    { id: 'vitals', label: 'Vitals' },
    { id: 'body_map', label: 'Location' },
    { id: 'complaint', label: 'Symptoms' },
    { id: 'conversation', label: 'Questions' },
    { id: 'photo', label: 'Photo' },
    { id: 'completion', label: 'Done' },
  ];


  const currentStepIndex = steps.findIndex((s) => s.id === currentScreen);
  const isWelcome = currentScreen === 'welcome';
  const isKioskJourney = !isWelcome && currentScreen !== 'processing';

  return (
    <div className="min-h-screen flex flex-col bg-[#FDF7FA] text-[#60435F] select-none">
      {/* Top Kiosk Navigation Bar */}
      <header
        className={`w-full sticky top-0 z-50 px-6 sm:px-10 py-4 flex items-center justify-between transition-all ${
          isWelcome
            ? 'bg-transparent'
            : 'bg-white/80 backdrop-blur-xl border-b border-[#E2A3C7]/30 shadow-[0_4px_20px_-4px_rgba(96,67,95,0.05)]'
        }`}
      >
        <HealthDeckLogo size="md" showSubtitle={!isWelcome} />

        {/* Journey Step Indicator (only during active triage journey) */}
        {isKioskJourney && (
          <div className="hidden md:flex items-center gap-2 bg-[#FDF7FA] px-4 py-2 rounded-2xl border border-[#E2A3C7]/30">
            {steps.map((step, idx) => {
              const isCurrent = step.id === currentScreen;
              const isPast = currentStepIndex > idx;

              return (
                <React.Fragment key={step.id}>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`
                        w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all
                        ${
                          isCurrent
                            ? 'bg-[#D67AB1] text-white shadow-[0_2px_8px_rgba(214,122,177,0.4)] scale-110'
                            : isPast
                            ? 'bg-[#A8DCD9] text-[#2C6260]'
                            : 'bg-white text-[#60435F]/40 border border-[#E2A3C7]/40'
                        }
                      `}
                    >
                      {idx + 1}
                    </span>
                    <span
                      className={`text-xs font-semibold tracking-wide ${
                        isCurrent
                          ? 'text-[#60435F]'
                          : isPast
                          ? 'text-[#60435F]/70'
                          : 'text-[#60435F]/40'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {idx < steps.length - 1 && (
                    <span className="w-4 h-0.5 bg-[#E2A3C7]/40 rounded-full mx-0.5" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        )}

        {/* Right Action Controls */}
        <div className="flex items-center gap-3">
          {/* Welcome Screen: Sleek System Ready Indicator */}
          {isWelcome && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/60 shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-bold tracking-wide text-emerald-800">
                  System Ready
                </span>
              </div>

              <button
                onClick={onSwitchToClinician}
                className="text-xs font-semibold text-[#60435F]/50 hover:text-[#60435F] px-2.5 py-1.5 rounded-xl hover:bg-white/80 transition-all cursor-pointer"
                title="Switch to Clinician Dashboard"
              >
                Clinician Mode
              </button>
            </div>
          )}

          {/* Active Flow: Reset / Start Over */}
          {!isWelcome && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-[#60435F]/70 hover:text-[#60435F] bg-white/70 hover:bg-white rounded-xl border border-[#E2A3C7]/40 transition-all cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Start Over</span>
            </button>
          )}

          {/* Clinician Portal Button (in flow) */}
          {!isWelcome && (
            <button
              onClick={onSwitchToClinician}
              className="flex items-center gap-2 px-3.5 py-2 text-xs font-bold text-[#60435F] bg-[#A8DCD9]/25 hover:bg-[#A8DCD9]/45 border border-[#A8DCD9]/60 rounded-xl transition-all cursor-pointer shadow-sm"
            >
              <Stethoscope className="w-4 h-4 text-[#2B605E]" />
              <span className="hidden sm:inline">Clinician View</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Kiosk Body */}
      <main className="flex-1 flex flex-col items-center justify-center relative overflow-hidden w-full">
        {children}
      </main>

      {/* Clinical Footer (only visible during intake journey, hidden on welcome screen) */}
      {!isWelcome && (
        <footer className="w-full py-3 px-4 sm:px-8 border-t border-[#E2A3C7]/20 bg-white/60 backdrop-blur-md flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[#60435F]/65 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-[#D67AB1] shrink-0" />
            <span>Preliminary healthcare intake. In an emergency, alert hospital staff or call 911/112.</span>
          </div>
          <div className="text-[11px] text-[#60435F]/50">
            Health Deck AI Kiosk • Patient Privacy Mode Active
          </div>
        </footer>
      )}
    </div>
  );
};

