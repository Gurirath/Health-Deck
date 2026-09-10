import React, { useState } from 'react';
import { Search, AlertTriangle, Clock, CheckCircle2, Stethoscope, ChevronRight } from 'lucide-react';
import type { CaseRecord } from '../../types/triage';

interface PatientQueueProps {
  cases: CaseRecord[];
  onSelectCase: (caseRecord: CaseRecord) => void;
  onRefresh: () => void;
  isLoading?: boolean;
}

export const PatientQueue: React.FC<PatientQueueProps> = ({
  cases,
  onSelectCase,
  onRefresh,
  isLoading = false,
}) => {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'pending' | 'urgent' | 'prescribed'>('all');

  const filteredCases = cases.filter((c) => {
    const isUrgent =
      c.escalate || c.escalation_reason === 'red_flag' || (c.red_flags && c.red_flags.length > 0);

    if (filter === 'pending' && c.status === 'prescribed') return false;
    if (filter === 'prescribed' && c.status !== 'prescribed') return false;
    if (filter === 'urgent' && !isUrgent) return false;

    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = String(c.id).includes(q);
      const matchComplaint = (c.chief_complaint || '').toLowerCase().includes(q);
      const matchDept = (c.effective_department || c.department || '').toLowerCase().includes(q);
      return matchId || matchComplaint || matchDept;
    }

    return true;
  });

  return (
    <div className="w-full bg-white/90 backdrop-blur-xl rounded-3xl border border-white/85 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] p-6">
      {/* Queue Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[#60435F]">Triage Patient Queue</h3>
            <p className="text-xs text-[#60435F]/60">
              Sorted chronologically with priority triage tagging.
            </p>
          </div>
        </div>

        {/* Search Input & Action Buttons */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-[#60435F]/40 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search case # or symptom..."
              className="pl-9 pr-4 py-2 text-xs rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] placeholder-[#60435F]/40 focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/30 w-48 sm:w-64"
            />
          </div>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="px-3.5 py-2 text-xs font-bold rounded-xl bg-[#FDF7FA] hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] transition-all cursor-pointer"
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 border-b border-[#E2A3C7]/25 pb-3">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
            filter === 'all'
              ? 'bg-[#60435F] text-white shadow-sm'
              : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
          }`}
        >
          All Cases ({cases.length})
        </button>

        <button
          onClick={() => setFilter('pending')}
          className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
            filter === 'pending'
              ? 'bg-[#D67AB1] text-white shadow-sm'
              : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
          }`}
        >
          Needs Review ({cases.filter((c) => c.status !== 'prescribed').length})
        </button>

        <button
          onClick={() => setFilter('urgent')}
          className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
            filter === 'urgent'
              ? 'bg-[#E14D62] text-white shadow-sm'
              : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
          }`}
        >
          Urgent Red-Flags (
          {
            cases.filter(
              (c) =>
                c.escalate ||
                c.escalation_reason === 'red_flag' ||
                (c.red_flags && c.red_flags.length > 0)
            ).length
          }
          )
        </button>

        <button
          onClick={() => setFilter('prescribed')}
          className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
            filter === 'prescribed'
              ? 'bg-[#2B605E] text-white shadow-sm'
              : 'text-[#60435F]/60 hover:bg-[#E2A3C7]/15'
          }`}
        >
          Prescribed ({cases.filter((c) => c.status === 'prescribed').length})
        </button>
      </div>

      {/* Patient Table / Rows */}
      {filteredCases.length === 0 ? (
        <div className="py-16 text-center text-[#60435F]/60">
          <p className="text-base font-bold text-[#60435F]">No cases found in this queue view.</p>
          <p className="text-xs mt-1">All completed kiosk intakes will appear here in real-time.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#E2A3C7]/25 text-[#60435F]/60 font-bold uppercase tracking-wider">
                <th className="py-3 px-3">Ticket</th>
                <th className="py-3 px-3">Time</th>
                <th className="py-3 px-4">Chief Complaint</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Department</th>
                <th className="py-3 px-3">Priority</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2A3C7]/15">
              {filteredCases.map((caseItem) => {
                const isUrgent =
                  caseItem.escalate ||
                  caseItem.escalation_reason === 'red_flag' ||
                  (caseItem.red_flags && caseItem.red_flags.length > 0);

                const isPrescribed = caseItem.status === 'prescribed';

                return (
                  <tr
                    key={caseItem.id}
                    onClick={() => onSelectCase(caseItem)}
                    className={`
                      transition-all hover:bg-[#FAF0F6]/80 cursor-pointer
                      ${isUrgent ? 'bg-[#FDF0F2]/50' : ''}
                    `}
                  >
                    <td className="py-3.5 px-3 font-black text-[#60435F] text-sm">
                      #{caseItem.id}
                    </td>

                    <td className="py-3.5 px-3 text-[#60435F]/70 font-mono">
                      {caseItem.created_at
                        ? new Date(caseItem.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Just now'}
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-[#60435F] max-w-xs truncate">
                      {caseItem.chief_complaint || 'General intake'}
                    </td>

                    <td className="py-3.5 px-3 capitalize text-[#60435F]/80">
                      {caseItem.symptom_location || 'General'}
                    </td>

                    <td className="py-3.5 px-3 font-semibold text-[#60435F]">
                      <span className="bg-[#D67AB1]/10 text-[#D67AB1] px-2.5 py-1 rounded-full text-[11px] font-bold border border-[#D67AB1]/30">
                        {caseItem.effective_department || caseItem.department || 'General Physician'}
                      </span>
                    </td>

                    <td className="py-3.5 px-3">
                      {isUrgent ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/40">
                          <AlertTriangle className="w-3 h-3 text-[#E14D62]" />
                          Red Flag
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[#A8DCD9]/25 text-[#2B605E]">
                          Routine
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-3">
                      {isPrescribed ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#A8DCD9]/30 text-[#2B605E]">
                          <CheckCircle2 className="w-3 h-3" />
                          Prescribed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#D67AB1]/15 text-[#9C3874]">
                          <Clock className="w-3 h-3" />
                          Needs Review
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCase(caseItem);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white hover:bg-[#D67AB1] text-[#60435F] hover:text-white border border-[#E2A3C7]/40 text-xs font-bold transition-all shadow-sm"
                      >
                        <span>Open Case</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
