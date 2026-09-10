import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'aqua' | 'ghost' | 'urgent';
  size?: 'md' | 'lg' | 'xl';
  isLoading?: boolean;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

export const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  children,
  variant = 'primary',
  size = 'lg',
  isLoading = false,
  icon,
  fullWidth = false,
  className = '',
  disabled,
  ...props
}) => {
  const sizeStyles = {
    md: 'px-6 py-3 text-base min-h-[48px] rounded-xl',
    lg: 'px-8 py-4 text-lg min-h-[58px] rounded-2xl font-semibold',
    xl: 'px-10 py-5 text-xl min-h-[68px] rounded-3xl font-bold tracking-wide',
  };

  const variantStyles = {
    primary:
      'bg-gradient-to-r from-[#D67AB1] to-[#C7649F] text-white shadow-[0_14px_30px_-6px_rgba(214,122,177,0.45)] hover:shadow-[0_20px_40px_-6px_rgba(214,122,177,0.6)] border border-white/30',
    secondary:
      'bg-white/90 text-[#60435F] border border-[#E2A3C7]/40 shadow-sm hover:bg-white hover:border-[#D67AB1]',
    aqua:
      'bg-gradient-to-r from-[#A8DCD9] to-[#88CAC6] text-[#335654] shadow-[0_12px_28px_-6px_rgba(168,220,217,0.5)] hover:shadow-[0_18px_36px_-6px_rgba(168,220,217,0.7)] border border-white/40 font-bold',
    ghost:
      'bg-transparent text-[#60435F]/80 hover:bg-[#E2A3C7]/15 hover:text-[#60435F]',
    urgent:
      'bg-gradient-to-r from-[#E14D62] to-[#CB394E] text-white shadow-[0_14px_30px_-6px_rgba(225,77,98,0.4)] border border-white/30 font-bold',
  };

  return (
    <motion.button
      whileHover={disabled || isLoading ? undefined : { y: -3, scale: 1.02 }}
      whileTap={disabled || isLoading ? undefined : { y: 0, scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      disabled={disabled || isLoading}
      className={`
        relative inline-flex items-center justify-center gap-3 select-none cursor-pointer
        focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#D67AB1]/40
        disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
        ${sizeStyles[size]}
        ${variantStyles[variant]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...(props as any)}
    >
      {isLoading ? (
        <Loader2 className="w-6 h-6 animate-spin" />
      ) : (
        <>
          {children}
          {icon && <span className="shrink-0 transition-transform group-hover:translate-x-1">{icon}</span>}
        </>
      )}
    </motion.button>
  );
};
