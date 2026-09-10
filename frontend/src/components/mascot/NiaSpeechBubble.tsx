import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Volume2 } from 'lucide-react';

interface NiaSpeechBubbleProps {
  message: string;
  subMessage?: string;
  speaking?: boolean;
  className?: string;
}

export const NiaSpeechBubble: React.FC<NiaSpeechBubbleProps> = ({
  message,
  subMessage,
  speaking = false,
  className = '',
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 360, damping: 26 }}
      className={`relative max-w-lg w-full select-none ${className}`}
    >
      <div
        className="
          relative rounded-3xl bg-white/95 backdrop-blur-2xl px-6 py-4 sm:px-7 sm:py-5
          border border-white/90 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.12),0_2px_10px_rgba(214,122,177,0.06)]
          text-center
        "
      >
        {/* Subtle top glossy edge */}
        <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />

        <div className="flex items-center justify-center gap-2 mb-1">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-xl bg-[#D67AB1]/15 text-[#D67AB1]">
            {speaking ? (
              <motion.div
                animate={{ scale: [1, 1.25, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              >
                <Volume2 className="w-3.5 h-3.5 text-[#D67AB1]" />
              </motion.div>
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-[#D67AB1]" />
            )}
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#60435F]">
            {message}
          </h2>
        </div>

        {subMessage && (
          <p className="text-sm sm:text-base font-medium text-[#60435F]/75 leading-relaxed">
            {subMessage}
          </p>
        )}

        {/* Speech Bubble Arrow pointing toward Nia */}
        <div
          className="
            absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-white/95
            border-b border-r border-[#E2A3C7]/30 transform rotate-45
            shadow-[2px_2px_4px_rgba(96,67,95,0.03)]
          "
        />
      </div>
    </motion.div>
  );
};

