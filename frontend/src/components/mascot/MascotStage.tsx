import React from 'react';
import { motion } from 'framer-motion';

interface MascotStageProps {
  children: React.ReactNode;
  showBackdropOrbs?: boolean;
  className?: string;
}

export const MascotStage: React.FC<MascotStageProps> = ({
  children,
  showBackdropOrbs = true,
  className = '',
}) => {
  return (
    <div className={`relative w-full flex flex-col items-center justify-center overflow-visible ${className}`}>
      {/* 2.5D Ambient Background Orbs */}
      {showBackdropOrbs && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden select-none -z-10 flex items-center justify-center">
          {/* Main Soft Pink / Blush Orb Behind Mascot */}
          <motion.div
            animate={{
              scale: [1, 1.06, 1],
              opacity: [0.35, 0.45, 0.35],
            }}
            transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-[#E2A3C7]/40 via-[#D67AB1]/25 to-transparent blur-3xl pointer-events-none"
          />

          {/* Calming Pearl Aqua Glow */}
          <motion.div
            animate={{
              scale: [1, 1.1, 1],
              opacity: [0.3, 0.45, 0.3],
            }}
            transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
            className="absolute -top-12 right-[15%] w-[360px] h-[360px] rounded-full bg-[#A8DCD9]/35 blur-3xl pointer-events-none"
          />

          {/* Secondary Soft Ambient Blush Orb */}
          <motion.div
            animate={{
              scale: [0.95, 1.05, 0.95],
              opacity: [0.25, 0.35, 0.25],
            }}
            transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut', delay: 4 }}
            className="absolute -bottom-10 left-[18%] w-[340px] h-[340px] rounded-full bg-[#E2A3C7]/30 blur-2xl pointer-events-none"
          />

          {/* Soft Floating Micro Glows */}
          <motion.div
            animate={{ y: [0, -12, 0], opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute top-20 left-[24%] w-3 h-3 rounded-full bg-[#A8DCD9]/50 pointer-events-none"
          />
          <motion.div
            animate={{ y: [0, -14, 0], opacity: [0.25, 0.5, 0.25] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
            className="absolute bottom-28 right-[24%] w-2.5 h-2.5 rounded-full bg-[#D67AB1]/45 pointer-events-none"
          />
        </div>
      )}

      {/* Stage Content */}
      <div className="relative z-10 w-full flex flex-col items-center justify-center">
        {children}
      </div>
    </div>
  );
};
