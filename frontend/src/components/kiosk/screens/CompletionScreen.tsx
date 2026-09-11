import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, ShieldAlert, FileText, Download, RotateCcw, Clock, AlertTriangle, Pill } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import type { CaseRecord, TriageState } from '../../../types/triage';
import { ApiService } from '../../../services/api';

interface CompletionScreenProps {
  caseId: number;
  finalState: TriageState;
  onStartNew: () => void;
}

export const CompletionScreen: React.FC<CompletionScreenProps> = ({
  caseId,
  finalState,
  onStartNew,
}) => {
  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [isPrescribed, setIsPrescribed] = useState(false);

  const isUrgent =
    finalState.escalate ||
    finalState.escalation_reason === 'red_flag' ||
    (finalState.red_flags && finalState.red_flags.length > 0);

  const department =
    caseData?.effective_department || finalState.department || 'General Physician';

  // Live poll the backend for doctor prescription updates
  useEffect(() => {
    let active = true;
    const checkCase = async () => {
      const { caseRecord } = await ApiService.getCase(caseId);
      if (active && caseRecord) {
        setCaseData(caseRecord);
        if (caseRecord.status === 'prescribed') {
          setIsPrescribed(true);
          return;
        }
      }
      if (active && !isPrescribed) {
        setTimeout(checkCase, 3500);
      }
    };

    checkCase();
    return () => {
      active = false;
    };
  }, [caseId, isPrescribed]);

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8 flex flex-col items-center">
      {/* Top Reassuring Nia Presentation */}
      <div className="w-full flex flex-col md:flex-row items-center justify-center gap-6 mb-8">
        <NiaCharacter pose={isUrgent ? 'urgent' : 'success'} size="md" />
        <NiaSpeechBubble
          message={isUrgent ? 'A clinician has been notified.' : "You're all checked in."}
          subMessage={
            isUrgent
              ? 'Your symptoms need prompt medical attention. A healthcare provider is prioritizing your case.'
              : 'Your information has been securely sent to the clinical team.'
          }
        />
      </div>

      {/* Main Ticket & Summary Card */}
      <div className="w-full max-w-2xl bg-white/90 backdrop-blur-2xl rounded-3xl p-6 sm:p-8 border border-white/85 shadow-[0_20px_50px_-10px_rgba(96,67,95,0.12)] flex flex-col gap-6">
        {/* Urgent Alert Banner (Calm, non-panicky) */}
        {isUrgent && (
          <div className="p-4 rounded-2xl bg-[#FDF0F2] border border-[#F9B4BF] flex items-start gap-3">
            <ShieldAlert className="w-6 h-6 text-[#E14D62] shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-[#C42239]">Priority Review Active</h4>
              <p className="text-xs text-[#60435F]/80 mt-1">
                Your reported readings indicate priority attention. Please remain seated in the intake waiting area; a nurse or doctor will call your ticket shortly.
              </p>
            </div>
          </div>
        )}

        {/* Ticket Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-5 border-b border-[#E2A3C7]/30 gap-4">
          <div>
            <span className="text-xs uppercase tracking-wider font-bold text-[#60435F]/60">
              Check-In Ticket
            </span>
            <h2 className="text-3xl font-black text-[#60435F] tracking-tight">
              Case #{caseId}
            </h2>
          </div>

          <div className="flex flex-col sm:items-end">
            <span className="text-xs uppercase tracking-wider font-bold text-[#60435F]/60">
              Assigned Department
            </span>
            <span className="text-base font-bold text-[#D67AB1] bg-[#D67AB1]/10 px-3.5 py-1 rounded-full mt-1 border border-[#D67AB1]/30">
              {department}
            </span>
          </div>
        </div>

        {/* What Happens Next 3-Step Guide */}
        <div>
          <h4 className="text-xs uppercase tracking-wider font-bold text-[#60435F]/70 mb-3">
            What Happens Next
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30">
              <span className="w-6 h-6 rounded-full bg-[#D67AB1]/20 text-[#D67AB1] text-xs font-bold flex items-center justify-center mb-2">
                1
              </span>
              <p className="text-xs font-bold text-[#60435F]">Doctor Reviews</p>
              <p className="text-[11px] text-[#60435F]/65 mt-0.5">
                A licensed physician inspects your symptoms and vitals.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30">
              <span className="w-6 h-6 rounded-full bg-[#D67AB1]/20 text-[#D67AB1] text-xs font-bold flex items-center justify-center mb-2">
                2
              </span>
              <p className="text-xs font-bold text-[#60435F]">Data Verified</p>
              <p className="text-[11px] text-[#60435F]/65 mt-0.5">
                Vitals and answers are clinically validated on the dashboard.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30">
              <span className="w-6 h-6 rounded-full bg-[#D67AB1]/20 text-[#D67AB1] text-xs font-bold flex items-center justify-center mb-2">
                3
              </span>
              <p className="text-xs font-bold text-[#60435F]">Next Step Decided</p>
              <p className="text-[11px] text-[#60435F]/65 mt-0.5">
                A prescription or consultation order will be issued.
              </p>
            </div>
          </div>
        </div>

        {/* Live Doctor Review Status Box */}
        {isPrescribed && caseData ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-5 rounded-2xl bg-[#A8DCD9]/25 border-2 border-[#A8DCD9] flex flex-col gap-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-6 h-6 text-[#2B605E]" />
                <div>
                  <h4 className="text-base font-bold text-[#2B605E]">
                    Prescription Ready!
                  </h4>
                  <p className="text-xs text-[#2B605E]/80">
                    Reviewed & prescribed by {caseData.doctor_name || 'Attending Physician'}
                  </p>
                </div>
              </div>

              <a
                href={ApiService.getReportUrl(caseId)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#2B605E] text-white text-xs font-bold hover:bg-[#204948] transition-all shadow-md"
              >
                <Download className="w-4 h-4" />
                <span>Download Report PDF</span>
              </a>
            </div>

            {/* Prescribed Medicines Table */}
            {caseData.prescription_medicines && caseData.prescription_medicines.length > 0 && (
              <div className="bg-white rounded-xl p-3 border border-[#A8DCD9]/60">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-[#E2A3C7]/30 text-[#60435F]/70">
                      <th className="py-1.5 px-2">Medicine</th>
                      <th className="py-1.5 px-2">Dosage / Day</th>
                      <th className="py-1.5 px-2">Remark</th>
                    </tr>
                  </thead>
                  <tbody>
                    {caseData.prescription_medicines.map((med, i) => (
                      <tr key={i} className="border-b border-gray-100 last:border-0 font-medium">
                        <td className="py-2 px-2 font-bold text-[#60435F]">{med.name}</td>
                        <td className="py-2 px-2">{med.dosage_per_day}</td>
                        <td className="py-2 px-2 text-[#60435F]/75">{med.remark}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {caseData.doctor_notes && (
              <p className="text-xs text-[#60435F] italic bg-white/70 p-2.5 rounded-xl">
                Notes from doctor: "{caseData.doctor_notes}"
              </p>
            )}
          </motion.div>
        ) : (
          <div className="p-4 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-[#D67AB1] animate-spin" />
              <div>
                <p className="text-xs font-bold text-[#60435F]">Waiting for Doctor Review</p>
                <p className="text-[11px] text-[#60435F]/60">
                  Case is queued in the triage workspace. This screen auto-updates.
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                ApiService.getCase(caseId).then(({ caseRecord }) => {
                  if (caseRecord) {
                    setCaseData(caseRecord);
                    if (caseRecord.status === 'prescribed') setIsPrescribed(true);
                  }
                });
              }}
              className="text-xs font-bold px-3 py-1.5 rounded-xl bg-white hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] transition-all cursor-pointer"
            >
              Refresh
            </button>
          </div>
        )}

        {/* Start New Case Button */}
        <div className="pt-2 border-t border-[#E2A3C7]/30 flex justify-center">
          <button
            onClick={onStartNew}
            className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-[#60435F]/10 hover:bg-[#60435F]/20 text-[#60435F] font-bold text-sm transition-all cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Finish & Reset Kiosk for Next Patient</span>
          </button>
        </div>
      </div>
    </div>
  );
};
