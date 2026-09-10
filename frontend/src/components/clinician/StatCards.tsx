import React from 'react';
import { motion } from 'framer-motion';
import { Users, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { CaseRecord } from '../../types/triage';

interface StatCardsProps {
  cases: CaseRecord[];
}

export const StatCards: React.FC<StatCardsProps> = ({ cases }) => {
  const totalToday = cases.length;
  const needsReview = cases.filter((c) => c.status !== 'prescribed').length;
  const urgentCount = cases.filter(
    (c) => c.escalate || c.escalation_reason === 'red_flag' || (c.red_flags && c.red_flags.length > 0)
  ).length;
  const completedCount = cases.filter((c) => c.status === 'prescribed').length;

  const cards = [
    {
      label: 'Cases Active',
      value: totalToday,
      icon: <Users className="w-5 h-5 text-[#60435F]" />,
      bg: 'bg-white',
      border: 'border-[#E2A3C7]/40',
      badge: 'Today',
      badgeColor: 'bg-[#60435F]/10 text-[#60435F]',
    },
    {
      label: 'Needs Review',
      value: needsReview,
      icon: <Clock className="w-5 h-5 text-[#D67AB1]" />,
      bg: 'bg-white',
      border: 'border-[#D67AB1]/40',
      badge: 'Waiting',
      badgeColor: 'bg-[#D67AB1]/15 text-[#9C3874]',
    },
    {
      label: 'Urgent / Red Flags',
      value: urgentCount,
      icon: <AlertTriangle className="w-5 h-5 text-[#E14D62]" />,
      bg: 'bg-[#FDF0F2]',
      border: 'border-[#F9B4BF]',
      badge: 'High Priority',
      badgeColor: 'bg-[#E14D62]/15 text-[#C42239]',
    },
    {
      label: 'Prescribed',
      value: completedCount,
      icon: <CheckCircle2 className="w-5 h-5 text-[#2B605E]" />,
      bg: 'bg-white',
      border: 'border-[#A8DCD9]/70',
      badge: 'Completed',
      badgeColor: 'bg-[#A8DCD9]/30 text-[#2B605E]',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          className={`rounded-3xl p-5 border shadow-[0_8px_24px_-4px_rgba(96,67,95,0.06)] flex flex-col justify-between ${card.bg} ${card.border}`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="p-2.5 rounded-2xl bg-white/80 shadow-sm border border-black/5">
              {card.icon}
            </div>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${card.badgeColor}`}>
              {card.badge}
            </span>
          </div>

          <div>
            <span className="text-xs font-semibold text-[#60435F]/60 uppercase tracking-wider">
              {card.label}
            </span>
            <p className="text-3xl font-black text-[#60435F] tracking-tight mt-0.5">
              {card.value}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  );
};
