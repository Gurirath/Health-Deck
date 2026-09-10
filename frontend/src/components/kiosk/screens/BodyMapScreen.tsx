import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Check, Sparkles } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import { BODY_REGIONS } from '../../../constants/bodyRegions';

interface BodyMapScreenProps {
  initialLocation?: string;
  onConfirm: (location: string) => void;
}

export const BodyMapScreen: React.FC<BodyMapScreenProps> = ({
  initialLocation = 'head',
  onConfirm,
}) => {
  const [selectedId, setSelectedId] = useState<string>(initialLocation);

  const activeRegion = BODY_REGIONS.find((r) => r.id === selectedId) || BODY_REGIONS[0];

  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  const handleContinue = () => {
    onConfirm(activeRegion.backendRegion);
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-6 flex flex-col items-center">
      {/* Top Nia Dialogue */}
      <div className="w-full flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
        <div className="flex items-center gap-4">
          <NiaCharacter pose="guiding" size="sm" />
          <NiaSpeechBubble
            message="Where are you feeling the discomfort?"
            subMessage="Tap on the body map or choose from the list to pin the location."
          />
        </div>

        {/* Current Active Selection Pill */}
        <div className="flex items-center gap-2.5 px-4 py-2 rounded-2xl bg-white/90 backdrop-blur-md border border-[#D67AB1]/40 shadow-sm">
          <Sparkles className="w-4 h-4 text-[#D67AB1]" />
          <span className="text-xs font-bold text-[#60435F]">Selected:</span>
          <span className="text-sm font-black text-[#D67AB1]">{activeRegion.label}</span>
        </div>
      </div>

      {/* Main Interactive Grid: 2.5D Body Visualizer + Region Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full items-center mb-8">
        {/* Left Column: Soft 2.5D Body Silhouette */}
        <div className="lg:col-span-6 flex flex-col items-center justify-center relative">
          <div className="relative w-[300px] h-[460px] rounded-3xl bg-white/80 backdrop-blur-xl border border-white/90 p-4 shadow-[0_20px_50px_-10px_rgba(96,67,95,0.12)] flex items-center justify-center overflow-hidden">
            {/* Soft Ambient Depth Background */}
            <div className="absolute inset-0 bg-gradient-to-b from-[#FDF7FA] via-white to-[#F6E3EE]/40 pointer-events-none" />

            {/* Stylized Friendly Abstract Human Figure SVG */}
            <svg
              viewBox="0 0 200 360"
              className="w-full h-full max-h-[420px] drop-shadow-[0_8px_16px_rgba(96,67,95,0.06)] relative z-10"
            >
              <defs>
                <linearGradient id="bodyBaseGrad" x1="50" y1="20" x2="150" y2="340" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#FAF0F5" />
                  <stop offset="100%" stopColor="#F1D7E6" />
                </linearGradient>

                <linearGradient id="activeRegionGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#A8DCD9" />
                  <stop offset="100%" stopColor="#6DBEB8" />
                </linearGradient>
              </defs>

              {/* Head */}
              <circle
                cx="100"
                cy="42"
                r="24"
                onClick={() => handleSelect('head')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'head'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Throat / Neck */}
              <rect
                x="92"
                y="68"
                width="16"
                height="18"
                rx="4"
                onClick={() => handleSelect('throat')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'throat'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Chest */}
              <path
                d="M74 88C82 85 118 85 126 88L130 134C120 138 80 138 70 134L74 88Z"
                onClick={() => handleSelect('chest')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'chest'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Abdomen / Stomach */}
              <path
                d="M71 138C80 136 120 136 129 138L127 185C118 190 82 190 73 185L71 138Z"
                onClick={() => handleSelect('abdomen')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'abdomen'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Left Arm & Hand */}
              <path
                d="M70 92L42 165C38 175 44 186 54 182L62 178L72 125"
                onClick={() => handleSelect('arm')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'arm'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Right Arm & Hand */}
              <path
                d="M130 92L158 165C162 175 156 186 146 182L138 178L128 125"
                onClick={() => handleSelect('arm')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'arm'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Left Leg & Foot */}
              <path
                d="M76 190L72 315C72 325 82 332 90 326L92 322L98 190"
                onClick={() => handleSelect('leg')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'leg'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Right Leg & Foot */}
              <path
                d="M102 190L108 322C110 330 120 326 122 315L124 190"
                onClick={() => handleSelect('leg')}
                className={`cursor-pointer transition-all duration-300 ${
                  selectedId === 'leg'
                    ? 'fill-[#D67AB1] stroke-white stroke-2 filter drop-shadow-[0_0_12px_rgba(214,122,177,0.8)]'
                    : 'fill-[url(#bodyBaseGrad)] hover:fill-[#E2A3C7]/60 stroke-[#E2A3C7]'
                }`}
              />

              {/* Hotspot Pulsing Indicator on selected zone */}
              <circle
                cx={activeRegion.x * 2}
                cy={activeRegion.y * 3.6}
                r="7"
                fill="#A8DCD9"
                className="animate-ping pointer-events-none"
              />
              <circle
                cx={activeRegion.x * 2}
                cy={activeRegion.y * 3.6}
                r="4.5"
                fill="#FFFFFF"
                stroke="#2B605E"
                strokeWidth="2"
                className="pointer-events-none"
              />
            </svg>
          </div>
          <p className="text-xs text-[#60435F]/60 mt-3">Interactive Anatomical Map</p>
        </div>

        {/* Right Column: Region Selection Cards */}
        <div className="lg:col-span-6 flex flex-col gap-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {BODY_REGIONS.map((region) => {
              const isSelected = region.id === selectedId;

              return (
                <motion.button
                  key={region.id}
                  type="button"
                  whileHover={{ y: -2, scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleSelect(region.id)}
                  className={`
                    p-3.5 rounded-2xl text-left transition-all flex items-start justify-between cursor-pointer border
                    ${
                      isSelected
                        ? 'bg-white shadow-[0_12px_28px_-6px_rgba(214,122,177,0.35)] border-[#D67AB1] ring-2 ring-[#D67AB1]/40'
                        : 'bg-white/80 hover:bg-white border-[#E2A3C7]/35 text-[#60435F]'
                    }
                  `}
                >
                  <div>
                    <h4
                      className={`text-sm font-bold ${
                        isSelected ? 'text-[#D67AB1]' : 'text-[#60435F]'
                      }`}
                    >
                      {region.label}
                    </h4>
                    <p className="text-xs text-[#60435F]/65 line-clamp-1 mt-0.5">
                      {region.description}
                    </p>
                  </div>

                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ml-2 mt-0.5 border ${
                      isSelected
                        ? 'bg-[#D67AB1] border-[#D67AB1] text-white'
                        : 'border-[#E2A3C7]/50'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </div>
                </motion.button>
              );
            })}
          </div>

          {/* Detailed Active Selection Confirmation Box */}
          <div className="mt-2 p-4 rounded-2xl bg-[#A8DCD9]/20 border border-[#A8DCD9]/60 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider font-bold text-[#2B605E]">
                Active Location
              </p>
              <p className="text-base font-extrabold text-[#60435F]">
                {activeRegion.label}
              </p>
            </div>
            <PrimaryButton size="md" onClick={handleContinue} icon={<ArrowRight className="w-4 h-4" />}>
              Confirm & Continue →
            </PrimaryButton>
          </div>
        </div>
      </div>
    </div>
  );
};
