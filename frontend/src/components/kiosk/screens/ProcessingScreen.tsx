import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { MascotStage } from '../../mascot/MascotStage';

const PROCESSING_STEPS = [
  'Synthesizing reported symptoms & vitals...',
  'Evaluating clinical guideline indicators...',
  'Checking safety thresholds & emergency rules...',
  'Preparing doctor review summary...',
];

export const ProcessingScreen: React.FC = () => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev < PROCESSING_STEPS.length - 1 ? prev + 1 : prev));
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <MascotStage className="min-h-[calc(100vh-140px)] py-8">
      <div className="w-full max-w-2xl mx-auto px-4 flex flex-col items-center justify-center text-center">
        {/* Nia in Thinking Pose */}
        <div className="mb-4">
          <NiaSpeechBubble
            message="Thanks. I'm putting everything together."
            subMessage="Analyzing your vitals and answers to prepare a clinical summary for the physician."
          />
        </div>

        <div className="my-2">
          <NiaCharacter pose="thinking" size="lg" />
        </div>

        {/* Circular Calm Medical Processing Wave */}
        <div className="w-full max-w-md bg-white/80 backdrop-blur-xl rounded-3xl p-6 border border-white/90 shadow-[0_16px_36px_-8px_rgba(96,67,95,0.08)] mt-4 flex flex-col items-center gap-4">
          {/* Circular Progress Meter */}
          <div className="relative w-16 h-16 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="32"
                cy="32"
                r="26"
                stroke="#E2A3C7"
                strokeWidth="4"
                strokeOpacity="0.3"
                fill="none"
              />
              <motion.circle
                cx="32"
                cy="32"
                r="26"
                stroke="#D67AB1"
                strokeWidth="4"
                strokeLinecap="round"
                fill="none"
                initial={{ pathLength: 0.15 }}
                animate={{ pathLength: [0.15, 0.85, 0.15], rotate: [0, 360] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              />
            </svg>
            <span className="absolute text-xs font-bold text-[#D67AB1]">✦</span>
          </div>

          {/* Dynamic Status Text */}
          <div className="h-6">
            <motion.p
              key={stepIndex}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="text-sm font-semibold text-[#60435F]"
            >
              {PROCESSING_STEPS[stepIndex]}
            </motion.p>
          </div>

          {/* Calming reassurance */}
          <p className="text-xs text-[#60435F]/60">
            Secure, encrypted session. A doctor will inspect this case shortly.
          </p>
        </div>
      </div>
    </MascotStage>
  );
};
