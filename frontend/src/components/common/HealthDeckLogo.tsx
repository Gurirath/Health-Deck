import React from 'react';

interface HealthDeckLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showSubtitle?: boolean;
  className?: string;
}

export const HealthDeckLogo: React.FC<HealthDeckLogoProps> = ({
  size = 'md',
  showSubtitle = true,
  className = '',
}) => {
  const iconSizes = {
    sm: 'w-8 h-8 min-w-[32px] max-w-[32px] min-h-[32px] max-h-[32px]',
    md: 'w-10 h-10 min-w-[40px] max-w-[40px] min-h-[40px] max-h-[40px]',
    lg: 'w-12 h-12 min-w-[48px] max-w-[48px] min-h-[48px] max-h-[48px]',
    xl: 'w-16 h-16 min-w-[64px] max-w-[64px] min-h-[64px] max-h-[64px]',
  };

  const textSizes = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-3xl',
  };

  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`}>
      {/* Rigid 2.5D Brand Mark */}
      <div
        className={`relative ${iconSizes[size]} rounded-2xl flex items-center justify-center shrink-0 overflow-visible`}
        style={{
          background: 'linear-gradient(135deg, #D67AB1 0%, #60435F 100%)',
          boxShadow: '0 6px 16px -2px rgba(214, 122, 177, 0.4), inset 0 1px 1px rgba(255, 255, 255, 0.45)',
        }}
      >
        {/* Medical Sparkle Cross with strict bounds */}
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          style={{ width: '20px', height: '20px', maxWidth: '20px', maxHeight: '20px' }}
          className="text-white shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 5v14M5 12h14" />
          <circle cx="12" cy="12" r="2.5" fill="#A8DCD9" stroke="none" />
        </svg>

        {/* Ambient Aqua Corner Dot */}
        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-[#A8DCD9] border-2 border-white shadow-xs" />
      </div>

      <div className="flex flex-col">
        <div className="flex items-center gap-1.5 leading-none">
          <span className={`font-black tracking-tight text-[#60435F] ${textSizes[size]}`}>
            HEALTH
          </span>
          <span className={`font-black tracking-tight text-[#D67AB1] ${textSizes[size]}`}>
            DECK
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-[#A8DCD9] inline-block mb-0.5" />
        </div>
        {showSubtitle && (
          <p className="text-[10px] font-semibold tracking-wider uppercase text-[#60435F]/60 mt-1">
            Intelligent Triage Kiosk
          </p>
        )}
      </div>
    </div>
  );
};

