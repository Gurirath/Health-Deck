import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Lock, Heart, Mic, Activity, ShieldCheck } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { MascotStage } from '../../mascot/MascotStage';
import { PrimaryButton } from '../../common/PrimaryButton';
import { FloatingHealthCard } from '../../common/FloatingHealthCard';

interface WelcomeScreenProps {
  onStart: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onStart }) => {
  return (
    <MascotStage className="w-full flex-1 flex flex-col items-center justify-center py-4 px-4 sm:px-6">
      <div className="w-full max-w-5xl mx-auto flex flex-col items-center justify-center">
        
        {/* Nia Welcoming Speech Bubble */}
        <div className="mb-4 sm:mb-6 z-20">
          <NiaSpeechBubble
            message="Hi, I'm Nia 👋"
            subMessage="I'll guide you through a quick health check."
          />
        </div>

        {/* Central Kiosk Hero Stage with Nia & 4 Floating Cards */}
        <div className="relative w-full max-w-3xl flex items-center justify-center my-2">
          {/* Card 1: Top Left - Heart Rate */}
          <div className="hidden md:block absolute -left-4 lg:left-0 top-6 z-20">
            <FloatingHealthCard delay={0.2} duration={5.5} yOffset={10}>
              <div className="flex items-center gap-3.5 min-w-[165px]">
                <div className="w-11 h-11 rounded-2xl bg-[#D67AB1]/15 text-[#D67AB1] flex items-center justify-center shrink-0">
                  <Heart className="w-5 h-5 fill-[#D67AB1]/25 text-[#D67AB1]" />
                </div>
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-[#60435F]/60 font-bold block leading-none">
                    Heart Rate
                  </span>
                  <div className="flex items-baseline gap-1 mt-1 leading-none">
                    <span className="text-2xl font-black text-[#60435F]">78</span>
                    <span className="text-xs font-bold text-[#60435F]/60">BPM</span>
                  </div>
                </div>
              </div>
            </FloatingHealthCard>
          </div>

          {/* Card 2: Bottom Left - Voice Ready */}
          <div className="hidden md:block absolute -left-2 lg:left-4 bottom-10 z-20">
            <FloatingHealthCard delay={1.2} duration={6} yOffset={8}>
              <div className="flex items-center gap-3 min-w-[165px]">
                <div className="w-11 h-11 rounded-2xl bg-[#A8DCD9]/30 text-[#2C6260] flex items-center justify-center shrink-0">
                  <Mic className="w-5 h-5 text-[#2C6260]" />
                </div>
                <div>
                  <p className="text-sm font-bold text-[#60435F] leading-snug">Voice Ready</p>
                  <p className="text-xs font-medium text-[#60435F]/70">Tap to speak anytime</p>
                </div>
              </div>
            </FloatingHealthCard>
          </div>

          {/* Card 3: Top Right - SpO2 Blood Oxygen */}
          <div className="hidden md:block absolute -right-4 lg:right-0 top-6 z-20">
            <FloatingHealthCard delay={0.7} duration={5.2} yOffset={12}>
              <div className="flex items-center gap-3.5 min-w-[165px]">
                <div className="w-11 h-11 rounded-2xl bg-[#A8DCD9]/30 text-[#2B605E] flex items-center justify-center shrink-0">
                  <Activity className="w-5 h-5 text-[#2B605E]" />
                </div>
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-[#60435F]/60 font-bold block leading-none">
                    SpO₂
                  </span>
                  <div className="flex items-baseline gap-1 mt-1 leading-none">
                    <span className="text-2xl font-black text-[#2B605E]">98%</span>
                    <span className="text-xs font-bold text-[#2B605E]/70">Optimal</span>
                  </div>
                </div>
              </div>
            </FloatingHealthCard>
          </div>

          {/* Card 4: Bottom Right - Doctor Reviewed */}
          <div className="hidden md:block absolute -right-2 lg:right-4 bottom-10 z-20">
            <FloatingHealthCard delay={1.8} duration={6.5} yOffset={9}>
              <div className="flex items-center gap-3 min-w-[165px]">
                <div className="w-11 h-11 rounded-2xl bg-[#60435F]/10 text-[#60435F] flex items-center justify-center shrink-0">
                  <ShieldCheck className="w-5 h-5 text-[#60435F]" />
                </div>
                <div>
                  <p className="text-sm font-bold text-[#60435F] leading-snug">Doctor Reviewed</p>
                  <p className="text-xs font-medium text-[#60435F]/70">Physician validated</p>
                </div>
              </div>
            </FloatingHealthCard>
          </div>

          {/* Central Nia Mascot & Pedestal */}
          <div className="flex flex-col items-center justify-center z-10 my-1">
            <NiaCharacter pose="welcome" size="xl" />
          </div>
        </div>

        {/* Primary Kiosk Call To Action */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5 }}
          className="flex flex-col items-center mt-4 sm:mt-6 w-full max-w-sm gap-3.5 z-20"
        >
          <PrimaryButton
            size="xl"
            fullWidth
            onClick={onStart}
            icon={<ArrowRight className="w-6 h-6 ml-1" />}
            className="text-xl font-extrabold tracking-wide min-h-[64px] rounded-3xl shadow-[0_18px_36px_-6px_rgba(214,122,177,0.5)]"
          >
            Let's Begin
          </PrimaryButton>

          {/* Reassurance Tagline */}
          <div className="flex items-center justify-center gap-2.5 text-sm font-semibold text-[#60435F]/75">
            <Lock className="w-3.5 h-3.5 text-[#2C6260]" />
            <span>Private</span>
            <span className="text-[#D67AB1] font-bold">•</span>
            <span>Secure</span>
            <span className="text-[#D67AB1] font-bold">•</span>
            <span>Doctor Reviewed</span>
          </div>
        </motion.div>

      </div>
    </MascotStage>
  );
};

