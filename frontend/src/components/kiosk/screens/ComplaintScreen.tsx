import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, ArrowRight, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import { SpeechService, type SpeechRecordingState, type AudioRecorderSession } from '../../../services/speech';

interface ComplaintScreenProps {
  symptomLocation?: string;
  initialComplaint?: string;
  errorMessage?: string | null;
  onSubmit: (complaint: string) => void;
}

const LOCATION_CHIPS: Record<string, string[]> = {
  chest: [
    'Chest tightness and shortness of breath',
    'Sharp chest pain when inhaling',
    'Palpitations and racing heart',
    'Mild discomfort in chest for 2 days',
  ],
  head: [
    'Throbbing headache with light sensitivity',
    'Dizziness and lightheadedness',
    'Sinus pressure around forehead and eyes',
    'Tension headache since morning',
  ],
  throat: [
    'Severe sore throat and painful swallowing',
    'Dry persistent hacking cough',
    'Hoarseness and scratchy throat',
    'Swollen neck glands and mild fever',
  ],
  abdomen: [
    'Cramping stomach pain and nausea',
    'Burning indigestion after meals',
    'Sharp lower abdominal ache',
    'Bloating and loss of appetite',
  ],
  general: [
    'Mild fever with whole body chills',
    'Persistent tiredness and fatigue',
    'Body aches and mild weakness',
    'Trouble sleeping due to general discomfort',
  ],
};

const LOCATION_NAMES: Record<string, string> = {
  head: 'head',
  throat: 'throat or neck',
  chest: 'chest area',
  abdomen: 'stomach / abdomen',
  arm: 'arm or shoulder',
  leg: 'leg or foot',
  skin: 'skin',
  general: 'body',
};

export const ComplaintScreen: React.FC<ComplaintScreenProps> = ({
  symptomLocation = 'general',
  initialComplaint = '',
  errorMessage,
  onSubmit,
}) => {
  const [text, setText] = useState(initialComplaint);
  const [recState, setRecState] = useState<SpeechRecordingState>('idle');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<AudioRecorderSession | null>(null);

  const locKey = symptomLocation.toLowerCase();
  const locationLabel = LOCATION_NAMES[locKey] || symptomLocation;
  const chips = LOCATION_CHIPS[locKey] || LOCATION_CHIPS.general;

  const isRecording = recState === 'recording';
  const isTranscribing = recState === 'transcribing';

  const toggleVoice = async () => {
    if (isRecording) {
      activeSession?.stop();
    } else {
      setVoiceError(null);
      const session = await SpeechService.startRecording(
        (state) => setRecState(state),
        (transcriptText) => {
          setText((prev) => (prev ? `${prev} ${transcriptText}` : transcriptText));
        },
        (err) => {
          setVoiceError(err);
        }
      );
      setActiveSession(session);
    }
  };

  useEffect(() => {
    return () => {
      activeSession?.cancel();
    };
  }, [activeSession]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isTranscribing) return;
    if (isRecording) activeSession?.cancel();
    onSubmit(text.trim());
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6 flex flex-col items-center">
      {/* Nia Location-Aware Dialogue */}
      <div className="w-full flex flex-col md:flex-row items-center justify-center gap-6 mb-8">
        <NiaCharacter pose={isRecording ? 'listening' : isTranscribing ? 'thinking' : 'guiding'} size="md" />
        <NiaSpeechBubble
          message={`Got it. Tell me what's bothering you in your ${locationLabel}.`}
          subMessage="Tap the microphone to speak naturally, or type your symptoms below."
          speaking={isRecording}
        />
      </div>

      {/* Backend / Network Error Banner if any */}
      {errorMessage && (
        <div className="w-full max-w-2xl mb-6 p-4 rounded-2xl bg-[#FDF0F2] border border-[#F9B4BF] text-[#C42239] text-xs font-semibold flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div className="flex-1">
            <p className="font-bold">Service Notice</p>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Voice "Tap to Speak" Centerpiece */}
      <div className="w-full flex flex-col items-center mb-8">
        <motion.button
          type="button"
          onClick={toggleVoice}
          disabled={isTranscribing}
          whileHover={{ scale: isTranscribing ? 1 : 1.04 }}
          whileTap={{ scale: isTranscribing ? 1 : 0.96 }}
          className={`
            relative w-28 h-28 sm:w-32 sm:h-32 rounded-full flex flex-col items-center justify-center gap-2
            shadow-[0_20px_45px_-8px_rgba(214,122,177,0.45)] cursor-pointer transition-all border-4 border-white
            ${
              isRecording
                ? 'bg-gradient-to-tr from-[#E14D62] to-[#FF758C] text-white shadow-[0_0_30px_rgba(225,77,98,0.5)]'
                : isTranscribing
                ? 'bg-[#A8DCD9] text-[#2B605E]'
                : 'bg-gradient-to-tr from-[#D67AB1] to-[#60435F] text-white hover:shadow-[0_24px_55px_-6px_rgba(214,122,177,0.65)]'
            }
          `}
        >
          {/* Animated Waveform Rings when actively recording */}
          <AnimatePresence>
            {isRecording && (
              <>
                <motion.span
                  initial={{ scale: 1, opacity: 0.8 }}
                  animate={{ scale: 1.6, opacity: 0 }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
                  className="absolute inset-0 rounded-full border-2 border-[#A8DCD9]"
                />
                <motion.span
                  initial={{ scale: 1, opacity: 0.6 }}
                  animate={{ scale: 1.9, opacity: 0 }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut', delay: 0.4 }}
                  className="absolute inset-0 rounded-full border-2 border-[#D67AB1]"
                />
              </>
            )}
          </AnimatePresence>

          {isTranscribing ? (
            <>
              <Loader2 className="w-8 h-8 animate-spin" />
              <span className="text-[10px] font-bold tracking-wider uppercase text-center px-2">Transcribing...</span>
            </>
          ) : isRecording ? (
            <>
              <MicOff className="w-8 h-8 animate-pulse" />
              <span className="text-[10px] font-bold tracking-wider uppercase">Tap to Finish</span>
            </>
          ) : (
            <>
              <Mic className="w-8 h-8" />
              <span className="text-[10px] font-bold tracking-wider uppercase">Tap to Speak</span>
            </>
          )}
        </motion.button>

        {isRecording && (
          <p className="text-xs font-bold text-[#E14D62] mt-3 animate-pulse">
            ● Recording audio with faster-whisper... Speak naturally
          </p>
        )}

        {isTranscribing && (
          <p className="text-xs font-bold text-[#2B605E] mt-3">
            Processing voice with local Whisper engine...
          </p>
        )}

        {voiceError && (
          <p className="text-xs text-[#E14D62] mt-3 font-medium bg-[#E14D62]/10 px-3 py-1 rounded-full">
            {voiceError}
          </p>
        )}
      </div>

      {/* Text Area & Quick Chips */}
      <div className="w-full max-w-2xl bg-white/90 backdrop-blur-xl rounded-3xl p-6 border border-white/80 shadow-[0_16px_40px_-8px_rgba(96,67,95,0.08)] mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70">
              Describe your symptoms
            </label>
            <span className="text-xs text-[#60435F]/50 font-medium">Spoken or typed</span>
          </div>

          <div className="relative">
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={`e.g., I've had a discomfort in my ${locationLabel} since yesterday morning...`}
              className="w-full rounded-2xl p-4 bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] placeholder-[#60435F]/40 focus:outline-none focus:ring-4 focus:ring-[#D67AB1]/30 focus:border-[#D67AB1] text-base resize-none"
            />
          </div>

          {/* Quick Common Chips for this Location */}
          <div>
            <p className="text-xs font-semibold text-[#60435F]/60 mb-2.5 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#D67AB1]" />
              <span>Or choose a common symptom:</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {chips.map((symptom) => (
                <button
                  key={symptom}
                  type="button"
                  onClick={() => setText(symptom)}
                  className="text-xs font-medium px-3.5 py-2 rounded-xl bg-[#FDF7FA] hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] transition-all cursor-pointer hover:border-[#D67AB1]"
                >
                  {symptom}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-2 flex justify-end">
            <PrimaryButton
              size="lg"
              disabled={!text.trim() || isTranscribing}
              onClick={handleSubmit}
              icon={<ArrowRight className="w-5 h-5" />}
            >
              Continue to Questions →
            </PrimaryButton>
          </div>
        </form>
      </div>
    </div>
  );
};

