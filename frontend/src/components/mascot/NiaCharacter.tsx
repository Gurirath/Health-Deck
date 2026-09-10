import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MascotPose } from '../../types/mascot';

interface NiaCharacterProps {
  pose?: MascotPose;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  onClick?: () => void;
}

export const NiaCharacter: React.FC<NiaCharacterProps> = ({
  pose = 'idle',
  size = 'lg',
  className = '',
  onClick,
}) => {
  const [blink, setBlink] = useState(false);

  // Natural spontaneous blinking
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 180);
    }, 3600);
    return () => clearInterval(blinkInterval);
  }, []);

  const sizeDimensions = {
    sm: { w: 180, h: 230 },
    md: { w: 260, h: 340 },
    lg: { w: 310, h: 410 },
    xl: { w: 360, h: 470 },
  };

  const { w, h } = sizeDimensions[size];

  // Arm/gesture variations based on pose
  const isWaving = pose === 'welcome';
  const isListening = pose === 'listening';
  const isThinking = pose === 'thinking';
  const isGuiding = pose === 'guiding';
  const isSuccess = pose === 'success';
  const isUrgent = pose === 'urgent';

  return (
    <div
      onClick={onClick}
      className={`relative select-none flex items-center justify-center shrink-0 ${className}`}
      style={{ width: w, height: h }}
    >
      {/* 2.5D Ambient Back Glow / Aura */}
      <AnimatePresence mode="wait">
        {isListening && (
          <motion.div
            key="listening-aura"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.25, 1], opacity: [0.35, 0.7, 0.35] }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -inset-8 rounded-full bg-[#A8DCD9]/40 blur-3xl pointer-events-none"
          />
        )}
        {isUrgent && (
          <motion.div
            key="urgent-aura"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.55, 0.3] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -inset-8 rounded-full bg-[#E14D62]/20 blur-3xl pointer-events-none"
          />
        )}
        {isSuccess && (
          <motion.div
            key="success-aura"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0.75, 0.4] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute -inset-8 rounded-full bg-[#A8DCD9]/50 blur-3xl pointer-events-none"
          />
        )}
      </AnimatePresence>

      {/* Floating Sparkles in Success / Thinking Mode */}
      {isSuccess && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 pointer-events-none"
        >
          <span className="absolute top-4 left-6 text-xl">✨</span>
          <span className="absolute top-12 right-6 text-lg text-[#A8DCD9]">✦</span>
          <span className="absolute bottom-16 right-4 text-xl">✨</span>
        </motion.div>
      )}

      {/* Breathing & Bobbing Base Container */}
      <motion.div
        animate={
          isListening
            ? { y: [-2, 2, -2], rotate: [-1, 1, -1] }
            : isThinking
            ? { y: [0, -4, 0], rotate: [0, -1.5, 0] }
            : isGuiding
            ? { x: [0, 4, 0], y: [-3, 0, -3] }
            : { y: [0, -6, 0] }
        }
        transition={{
          duration: isListening ? 2.2 : 4,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="w-full h-full relative flex items-center justify-center"
      >
        <svg
          viewBox="0 0 320 420"
          className="w-full h-full drop-shadow-[0_16px_30px_rgba(96,67,95,0.14)]"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Linear & Radial Gradients for 2.5D Soft Depth */}
            <linearGradient id="hairGrad" x1="60" y1="40" x2="260" y2="180" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#4A344A" />
              <stop offset="50%" stopColor="#60435F" />
              <stop offset="100%" stopColor="#3B263B" />
            </linearGradient>

            <linearGradient id="skinGrad" x1="120" y1="70" x2="200" y2="180" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FFEDE6" />
              <stop offset="60%" stopColor="#F9DBCF" />
              <stop offset="100%" stopColor="#F0C7B7" />
            </linearGradient>

            <linearGradient id="scrubsGrad" x1="80" y1="180" x2="240" y2="400" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#E992C6" />
              <stop offset="40%" stopColor="#D67AB1" />
              <stop offset="100%" stopColor="#B3588E" />
            </linearGradient>

            <linearGradient id="stethoscopeGrad" x1="100" y1="200" x2="220" y2="320" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#A8DCD9" />
              <stop offset="100%" stopColor="#6AB8B4" />
            </linearGradient>

            <radialGradient id="blushGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#FF9EB5" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#FF9EB5" stopOpacity="0" />
            </radialGradient>

            <filter id="softShadow" x="-10%" y="-10%" width="120%" height="130%">
              <feDropShadow dx="0" dy="8" stdDeviation="6" floodColor="#60435F" floodOpacity="0.16" />
            </filter>
          </defs>

          {/* 2.5D Ground Platform Pedestal */}
          <ellipse cx="160" cy="406" rx="92" ry="14" fill="#FFFFFF" fillOpacity="0.75" stroke="#E2A3C7" strokeWidth="1" strokeOpacity="0.4" />
          <ellipse cx="160" cy="406" rx="72" ry="9" fill="#D67AB1" fillOpacity="0.1" />
          <ellipse cx="160" cy="406" rx="48" ry="6" fill="#60435F" fillOpacity="0.16" />

          {/* Back Hair Volume */}
          <path
            d="M95 110C80 150 78 220 102 260C110 240 120 230 130 220L85 110Z"
            fill="url(#hairGrad)"
          />
          <path
            d="M225 110C240 150 242 220 218 260C210 240 200 230 190 220L235 110Z"
            fill="url(#hairGrad)"
          />

          {/* Neck */}
          <path d="M142 165H178V200C178 206 168 210 160 210C152 210 142 206 142 200V165Z" fill="#F0C7B7" />

          {/* Body / Nurse Scrub Top */}
          <g filter="url(#softShadow)">
            {/* Main Scrub Torso */}
            <path
              d="M108 205C125 198 142 195 160 195C178 195 195 198 212 205L232 360C232 372 222 382 210 382H110C98 382 88 372 88 360L108 205Z"
              fill="url(#scrubsGrad)"
            />

            {/* Scrub Collar V-Neck */}
            <path d="M136 195L160 232L184 195H202L160 252L118 195H136Z" fill="#FAF0F6" />
            <path d="M142 195L160 224L178 195" stroke="#D67AB1" strokeWidth="2.5" strokeLinecap="round" />

            {/* Health Deck Nurse Emblem / Pocket */}
            <rect x="180" y="255" width="28" height="34" rx="6" fill="#FAF0F6" fillOpacity="0.95" />
            <path d="M194 263V277M187 270H201" stroke="#D67AB1" strokeWidth="3" strokeLinecap="round" />
            <circle cx="194" cy="270" r="1.5" fill="#A8DCD9" />
          </g>

          {/* Stethoscope */}
          <path
            d="M130 202C128 240 134 290 152 305C158 310 166 310 172 305C188 292 192 240 190 202"
            stroke="url(#stethoscopeGrad)"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <circle cx="162" cy="310" r="10" fill="#FFFFFF" stroke="#6AB8B4" strokeWidth="3" />
          <circle cx="162" cy="310" r="4.5" fill="#A8DCD9" />

          {/* Left Arm / Hand State */}
          <g>
            {isWaving ? (
              // Waving Arm (Welcoming gesture)
              <motion.g
                animate={{ rotate: [-8, 14, -8] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
                style={{ originX: '90px', originY: '215px' }}
              >
                <path d="M96 212L65 170C60 163 50 165 47 172L42 186C40 192 44 200 50 204L88 240Z" fill="url(#scrubsGrad)" />
                {/* Waving Hand */}
                <circle cx="50" cy="155" r="14" fill="url(#skinGrad)" />
                <path d="M42 152C40 144 48 140 54 145" stroke="#F0C7B7" strokeWidth="3" strokeLinecap="round" />
              </motion.g>
            ) : isGuiding ? (
              // Guiding Arm (Pointing gracefully forward)
              <g>
                <path d="M98 212L68 250C62 258 50 262 42 254L35 248C28 242 28 232 35 226L78 185" fill="url(#scrubsGrad)" />
                <circle cx="34" cy="235" r="14" fill="url(#skinGrad)" />
              </g>
            ) : (
              // Resting Natural Arm
              <path
                d="M102 210C90 240 85 285 96 335C98 345 106 352 116 350C124 348 128 340 126 332L116 260"
                stroke="url(#scrubsGrad)"
                strokeWidth="24"
                strokeLinecap="round"
              />
            )}
          </g>

          {/* Right Arm / Hand State */}
          <g>
            {isThinking ? (
              // Thinking Arm (Hand on chin)
              <g>
                <path d="M216 215L230 265C234 278 226 292 214 294L185 260" stroke="url(#scrubsGrad)" strokeWidth="22" strokeLinecap="round" />
                <circle cx="178" cy="180" r="13" fill="url(#skinGrad)" />
              </g>
            ) : isGuiding ? (
              // Guiding Palm Extended
              <motion.g
                animate={{ x: [0, 8, 0] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
              >
                <path d="M218 212L255 240C265 248 275 242 278 232L282 220C285 210 278 200 268 196L222 185" fill="url(#scrubsGrad)" />
                <ellipse cx="288" cy="216" rx="14" ry="12" fill="url(#skinGrad)" />
                <path d="M285 212H302" stroke="#FAF0F6" strokeWidth="3" strokeLinecap="round" />
              </motion.g>
            ) : (
              // Resting Natural Arm
              <path
                d="M218 210C230 240 235 285 224 335C222 345 214 352 204 350C196 348 192 340 194 332L204 260"
                stroke="url(#scrubsGrad)"
                strokeWidth="24"
                strokeLinecap="round"
              />
            )}
          </g>

          {/* Head & Facial Silhouette */}
          <g filter="url(#softShadow)">
            {/* Ears */}
            <ellipse cx="112" cy="120" rx="9" ry="14" fill="#F0C7B7" />
            <ellipse cx="208" cy="120" rx="9" ry="14" fill="#F0C7B7" />

            {/* Head Contour */}
            <path
              d="M120 90C120 60 140 45 160 45C180 45 200 60 200 90V125C200 152 182 170 160 170C138 170 120 152 120 125V90Z"
              fill="url(#skinGrad)"
            />

            {/* Soft Cheeks Blush */}
            <ellipse cx="132" cy="132" rx="14" ry="8" fill="url(#blushGrad)" />
            <ellipse cx="188" cy="132" rx="14" ry="8" fill="url(#blushGrad)" />

            {/* Eyebrows */}
            {isThinking ? (
              <>
                <path d="M132 94C137 92 144 95 148 97" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
                <path d="M172 98C176 95 183 92 188 94" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
              </>
            ) : isUrgent ? (
              <>
                <path d="M134 98C139 96 145 97 149 99" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
                <path d="M171 99C175 97 181 96 186 98" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
              </>
            ) : (
              <>
                <path d="M133 95C138 92 145 93 149 95" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
                <path d="M171 95C175 93 182 92 187 95" stroke="#4A344A" strokeWidth="2.5" strokeLinecap="round" />
              </>
            )}

            {/* Eyes (With Blinking Animation) */}
            {blink ? (
              <>
                <path d="M134 112C138 116 144 116 148 112" stroke="#3B263B" strokeWidth="3" strokeLinecap="round" />
                <path d="M172 112C176 116 182 116 186 112" stroke="#3B263B" strokeWidth="3" strokeLinecap="round" />
              </>
            ) : (
              <>
                {/* Left Eye */}
                <ellipse cx="141" cy="112" rx="7.5" ry="9" fill="#3B263B" />
                <circle cx="138.5" cy="109" r="3" fill="#FFFFFF" />
                <circle cx="143" cy="114.5" r="1.5" fill="#FFFFFF" />

                {/* Right Eye */}
                <ellipse cx="179" cy="112" rx="7.5" ry="9" fill="#3B263B" />
                <circle cx="176.5" cy="109" r="3" fill="#FFFFFF" />
                <circle cx="181" cy="114.5" r="1.5" fill="#FFFFFF" />
              </>
            )}

            {/* Gentle Cute Nose */}
            <path d="M158 122C160 124 162 124 163 122" stroke="#E2A3C7" strokeWidth="2" strokeLinecap="round" />

            {/* Mouth */}
            {isSuccess || isWaving ? (
              // Broad warm smile
              <path
                d="M148 138C154 148 166 148 172 138"
                fill="#FF7E9C"
                stroke="#C4496E"
                strokeWidth="2"
                strokeLinecap="round"
              />
            ) : isUrgent ? (
              // Reassuring calm serious line
              <path d="M152 142C157 141 163 141 168 142" stroke="#A85773" strokeWidth="2.5" strokeLinecap="round" />
            ) : isThinking ? (
              // Small thoughtful pout
              <circle cx="160" cy="142" r="3" fill="#C4496E" />
            ) : (
              // Friendly gentle smile
              <path d="M150 140C155 146 165 146 170 140" stroke="#C4496E" strokeWidth="2.5" strokeLinecap="round" />
            )}
          </g>

          {/* Front Hair & Nurse Cap */}
          <g>
            {/* Front Bangs & Framing */}
            <path
              d="M120 90C125 72 145 62 160 62C178 62 195 72 200 90C192 84 178 82 165 88C152 94 135 92 120 90Z"
              fill="url(#hairGrad)"
            />
            {/* Left Strand */}
            <path d="M116 88C110 115 112 145 122 160C120 140 120 115 124 95Z" fill="url(#hairGrad)" />
            {/* Right Strand */}
            <path d="M204 88C210 115 208 145 198 160C200 140 200 115 196 95Z" fill="url(#hairGrad)" />

            {/* Modern Healthcare Headband / Cap */}
            <path
              d="M130 54C140 48 180 48 190 54C192 60 188 66 186 68C174 62 146 62 134 68C132 66 128 60 130 54Z"
              fill="#FFFFFF"
              stroke="#D67AB1"
              strokeWidth="2"
            />
            {/* Medical Cross on Cap */}
            <path d="M160 56V64M156 60H164" stroke="#D67AB1" strokeWidth="2" strokeLinecap="round" />
          </g>
        </svg>
      </motion.div>
    </div>
  );
};
