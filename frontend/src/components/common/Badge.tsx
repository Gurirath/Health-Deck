import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'aqua' | 'pink' | 'urgent' | 'warning' | 'grape';
  icon?: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  icon,
  className = '',
  size = 'md',
}) => {
  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs font-medium rounded-full',
    md: 'px-3.5 py-1.5 text-sm font-semibold rounded-full',
    lg: 'px-4 py-2 text-base font-bold rounded-2xl',
  };

  const variantStyles = {
    neutral: 'bg-white/80 text-[#60435F] border border-[#E2A3C7]/30 shadow-sm',
    aqua: 'bg-[#A8DCD9]/30 text-[#2B605E] border border-[#A8DCD9]/60 shadow-sm',
    pink: 'bg-[#D67AB1]/15 text-[#9C3874] border border-[#D67AB1]/40 shadow-sm',
    urgent: 'bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/40 shadow-sm',
    warning: 'bg-[#D9822B]/15 text-[#9B5510] border border-[#D9822B]/40 shadow-sm',
    grape: 'bg-[#60435F]/15 text-[#473146] border border-[#60435F]/30 shadow-sm',
  };

  return (
    <span
      className={`inline-flex items-center gap-2 backdrop-blur-md ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
