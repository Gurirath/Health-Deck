import React from 'react';
import { motion } from 'framer-motion';

interface FloatingHealthCardProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  yOffset?: number;
  className?: string;
  onClick?: () => void;
}

export const FloatingHealthCard: React.FC<FloatingHealthCardProps> = ({
  children,
  delay = 0,
  duration = 5,
  yOffset = 10,
  className = '',
  onClick,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{
        opacity: 1,
        y: [0, -yOffset, 0],
      }}
      transition={{
        opacity: { duration: 0.5, delay },
        y: {
          duration,
          repeat: Infinity,
          ease: 'easeInOut',
          delay,
        },
      }}
      whileHover={{ scale: 1.03, y: -yOffset - 3 }}
      onClick={onClick}
      className={`
        relative rounded-3xl bg-white/90 backdrop-blur-xl border border-white/80
        p-4 sm:p-5 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.1),0_4px_16px_rgba(214,122,177,0.05)]
        transition-all duration-300 hover:shadow-[0_24px_48px_-10px_rgba(96,67,95,0.16),0_0_24px_rgba(168,220,217,0.25)]
        select-none
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      {/* 2.5D Subtle Highlight Edge */}
      <div className="absolute inset-0 rounded-3xl pointer-events-none border border-white/80 bg-gradient-to-b from-white/50 to-transparent" />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
};

