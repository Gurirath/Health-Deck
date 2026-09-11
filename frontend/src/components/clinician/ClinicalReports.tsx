import React, { useState } from 'react';
import {
  FileText,
  Download,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  User,
  Pill,
  ExternalLink,
  RefreshCw,
  Calendar,
} from 'lucide-react';
import type { CaseRecord } from '../../types/triage';
import { ApiService } from '../../services/api';

interface ClinicalReportsProps {
  cases: CaseRecord[];
  onSelectCase: (caseRecord: CaseRecord) => void;
  onRefresh: () => void;
  isLoading?: boolean;
}

export const ClinicalReports: React.FC<ClinicalReportsProps> = ({
  cases,
  onSelectCase,
  onRefresh,
  isLoading = false,
}) => {
  const [search, setSearch] = useState('');
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [filterMode, setFilterMode] = useState<'prescribed' | 'all'>('prescribed');
  const [feedbackMsg, setFeedbackMsg] = useState<{ id: number; text: string; isError?: boolean } | null>(null);

  // Filter cases: default to prescribed cases that have reports
  const relevantCases = cases.filter((c) => {
    if (filterMode === 'prescribed' && c.status !== 'prescribed') return false;

    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = String(c.id).includes(q);
      const matchComplaint = (c.chief_complaint || '').toLowerCase().includes(q);
      const matchDoctor = (c.doctor_name || c.reviewed_by_doctor_name || '').toLowerCase().includes(q);
      const matchDept = (c.effective_department || c.department || '').toLowerCase().includes(q);
      const matchMed = (c.prescription_medicines || []).some((m) =>
        (m.name || '').toLowerCase().includes(q)
      );
      return matchId || matchComplaint || matchDoctor || matchDept || matchMed;
    }

    return true;
  });

  const handleDownload = async (caseId: number) => {
    setDownloadingId(caseId);
    setFeedbackMsg(null);
    try {
      const res = await ApiService.downloadReport(caseId);
      if (res.success) {
        setFeedbackMsg({ id: caseId, text: 'Report PDF downloaded successfully!' });
      } else {
        setFeedbackMsg({
          id: caseId,
          text: res.error || 'Failed to download report PDF.',
          isError: true,
        });
      }
    } catch (err: any) {
      setFeedbackMsg({
        id: caseId,
        text: err.message || 'Error occurred while downloading.',
        isError: true,
      });
    } finally {
      setDownloadingId(null);
      setTimeout(() => setFeedbackMsg(null), 5000);
    }
  };

  const prescribedCount = cases.filter((c) => c.status === 'prescribed').length;

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Header Banner */}
      <div className="bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] p-6">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-[#60435F]">Clinical Reports Repository</h2>
              <p className="text-xs text-[#60435F]/65 mt-0.5">
                Official medical reports, verified physician prescriptions, and patient summaries.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-[#60435F]/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search ticket, doctor, medicine..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] placeholder-[#60435F]/40 focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/30"
              />
            </div>

            <button
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh reports"
              className="px-3.5 py-2 text-xs font-bold rounded-xl bg-[#FDF7FA] hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] transition-all cursor-pointer flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Filter Switch */}
        <div className="flex items-center gap-2 mt-5 pt-4 border-t border-[#E2A3C7]/25">
          <button
            onClick={() => setFilterMode('prescribed')}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              filterMode === 'prescribed'
                ? 'bg-[#60435F] text-white shadow-sm'
                : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
            }`}
          >
            Prescribed Reports ({prescribedCount})
          </button>
          <button
            onClick={() => setFilterMode('all')}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              filterMode === 'all'
                ? 'bg-[#60435F] text-white shadow-sm'
                : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
            }`}
          >
            All Intake Cases ({cases.length})
          </button>
        </div>
      </div>

      {/* Global Feedback message */}
      {feedbackMsg && (
        <div
          className={`px-4 py-3 rounded-2xl text-xs font-semibold flex items-center justify-between shadow-sm transition-all ${
            feedbackMsg.isError
              ? 'bg-[#FDF0F2] text-[#C42239] border border-[#F9B4BF]'
              : 'bg-[#F0FDF4] text-[#166534] border border-[#BBF7D0]'
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button
            onClick={() => setFeedbackMsg(null)}
            className="text-xs font-bold opacity-60 hover:opacity-100 ml-4 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Reports List */}
      {relevantCases.length === 0 ? (
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 p-12 text-center shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-[#E2A3C7]/20 text-[#60435F] flex items-center justify-center mx-auto mb-3">
            <FileText className="w-7 h-7 opacity-60" />
          </div>
          <h3 className="text-base font-bold text-[#60435F]">No Clinical Reports Found</h3>
          <p className="text-xs text-[#60435F]/60 max-w-md mx-auto mt-1">
            {filterMode === 'prescribed'
              ? 'No prescribed clinical reports match your search criteria. When an attending physician writes a prescription, official clinical reports are generated and cataloged here.'
              : 'No intake cases match your query.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {relevantCases.map((c) => {
            const isPrescribed = c.status === 'prescribed';
            const medicines = c.prescription_medicines || [];
            const isDownloading = downloadingId === c.id;

            return (
              <div
                key={c.id}
                className="bg-white/95 backdrop-blur-xl rounded-2xl border border-[#E2A3C7]/30 shadow-[0_4px_20px_-4px_rgba(96,67,95,0.06)] p-5 hover:border-[#D67AB1]/40 transition-all flex flex-col gap-4"
              >
                {/* Top Row: Case badge, timestamp, department, status */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2A3C7]/20 pb-3">
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 rounded-xl bg-[#60435F] text-white font-black text-xs tracking-tight">
                      Case #{c.id}
                    </span>
                    <span className="text-xs font-semibold text-[#60435F]/75 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-[#D67AB1]" />
                      {c.prescribed_at
                        ? new Date(c.prescribed_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : c.created_at
                        ? new Date(c.created_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Recent'}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-[#D67AB1]/10 text-[#D67AB1] font-bold text-[11px] border border-[#D67AB1]/30">
                      {c.effective_department || c.department || 'General Physician'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {isPrescribed ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/60">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Official Report Ready
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FDF0F2] text-[#C42239] border border-[#F9B4BF]">
                        <Clock className="w-3.5 h-3.5" />
                        Pending Prescription
                      </span>
                    )}
                  </div>
                </div>

                {/* Middle Row: Patient complaint & Doctor attribution */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs font-bold text-[#60435F]/60 uppercase tracking-wider mb-1">
                      Patient Complaint & Symptoms
                    </h4>
                    <p className="text-sm font-bold text-[#60435F]">
                      {c.chief_complaint || 'General medical inquiry'}
                    </p>
                    <p className="text-xs text-[#60435F]/70 mt-0.5">
                      Target Region: <span className="font-semibold capitalize">{c.symptom_location || 'General'}</span>
                    </p>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-[#60435F]/60 uppercase tracking-wider mb-1">
                      Prescribing Attending Doctor
                    </h4>
                    <div className="flex items-center gap-2 text-xs font-bold text-[#60435F]">
                      <div className="w-6 h-6 rounded-lg bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center">
                        <User className="w-3.5 h-3.5" />
                      </div>
                      <span>{c.doctor_name || c.reviewed_by_doctor_name || 'Physician on Duty'}</span>
                    </div>
                    {c.doctor_notes && (
                      <p className="text-xs text-[#60435F]/80 italic mt-1 bg-[#FDF7FA] p-2 rounded-xl border border-[#E2A3C7]/20">
                        "{c.doctor_notes}"
                      </p>
                    )}
                  </div>
                </div>

                {/* Medicines List */}
                {medicines.length > 0 && (
                  <div className="bg-[#FAF4F8]/60 p-3 rounded-xl border border-[#E2A3C7]/25">
                    <h4 className="text-xs font-bold text-[#60435F]/70 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Pill className="w-3.5 h-3.5 text-[#D67AB1]" />
                      Prescribed Medications ({medicines.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {medicines.map((med, idx) => (
                        <div
                          key={idx}
                          className="bg-white px-3 py-1.5 rounded-lg border border-[#E2A3C7]/40 shadow-xs flex items-center gap-2 text-xs text-[#60435F]"
                        >
                          <span className="font-bold">{med.name}</span>
                          <span className="text-[#D67AB1] font-semibold text-[11px]">
                            • {med.dosage_per_day}
                          </span>
                          {med.remark && (
                            <span className="text-[#60435F]/60 text-[10px]">({med.remark})</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Buttons Footer */}
                <div className="flex items-center justify-between pt-2">
                  <span className="text-[11px] text-[#60435F]/50 font-mono">
                    {c.report_pdf_path ? `File: ${c.report_pdf_path.split('/').pop()}` : 'Digital Report'}
                  </span>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onSelectCase(c)}
                      className="px-3.5 py-1.5 rounded-xl bg-white hover:bg-[#FAF0F6] text-[#60435F] text-xs font-bold border border-[#E2A3C7]/40 transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>View Dossier</span>
                    </button>

                    <button
                      onClick={() => handleDownload(c.id)}
                      disabled={isDownloading || !isPrescribed}
                      className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm cursor-pointer ${
                        isPrescribed
                          ? 'bg-[#60435F] hover:bg-[#4E374D] text-white'
                          : 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed'
                      }`}
                    >
                      {isDownloading ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Downloading...</span>
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          <span>Download PDF</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
