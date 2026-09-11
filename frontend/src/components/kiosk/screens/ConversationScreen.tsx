import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Send, ArrowRight, Sparkles, AlertTriangle, Loader2 } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import type { TranscriptTurn } from '../../../types/triage';
import { SpeechService, type SpeechRecordingState, type AudioRecorderSession } from '../../../services/speech';

interface ConversationScreenProps {
  currentQuestion: string;
  questionOptions?: string[];
  questionType?: string;
  transcript: TranscriptTurn[];
  isSubmitting?: boolean;
  onAnswer: (answer: string) => void;
}

export const ConversationScreen: React.FC<ConversationScreenProps> = ({
  currentQuestion,
  questionOptions,
  questionType = 'free_text',
  transcript,
  isSubmitting = false,
  onAnswer,
}) => {
  const [typedAnswer, setTypedAnswer] = useState('');
  const [recState, setRecState] = useState<SpeechRecordingState>('idle');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const activeSessionRef = useRef<AudioRecorderSession | null>(null);

  const hasStructuredOptions = Boolean(questionOptions && questionOptions.length > 0);
  const options = questionOptions || [];

  const isRecording = recState === 'recording';
  const isTranscribing = recState === 'transcribing';

  const toggleVoice = async () => {
    if (isRecording) {
      activeSessionRef.current?.stop();
    } else {
      setVoiceError(null);
      const session = await SpeechService.startRecording(
        (state) => setRecState(state),
        (transcriptText) => {
          setTypedAnswer((prev) => (prev ? `${prev} ${transcriptText}` : transcriptText));
        },
        (err) => {
          setVoiceError(err);
        }
      );
      activeSessionRef.current = session;
    }
  };

  useEffect(() => {
    return () => {
      activeSessionRef.current?.cancel();
      activeSessionRef.current = null;
    };
  }, []);

  const handleSend = (textToSend?: string) => {
    const finalAnswer = textToSend || typedAnswer;
    if (!finalAnswer.trim() || isSubmitting || isTranscribing) return;
    if (isRecording) {
      activeSessionRef.current?.cancel();
      activeSessionRef.current = null;
    }
    onAnswer(finalAnswer.trim());
    setTypedAnswer('');
  };

  // Keep recent 2 turns of history for minimal, clean context
  const recentHistory = transcript.slice(-3);

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6 flex flex-col items-center">
      {/* Central Focused Question & Nia Anchor */}
      <div className="w-full flex flex-col md:flex-row items-center justify-center gap-6 mb-8">
        <NiaCharacter
          pose={isRecording ? 'listening' : isSubmitting || isTranscribing ? 'thinking' : 'guiding'}
          size="md"
        />
        <NiaSpeechBubble
          message={currentQuestion || "How would you describe what you're experiencing?"}
          subMessage={
            hasStructuredOptions
              ? 'Select the closest option below or speak directly with Nia.'
              : 'Tap to speak with Nia or type your response below.'
          }
          speaking={isRecording}
        />
      </div>

      {/* Main Focus Card: Structured Selections (if provided) + Voice/Text Input */}
      <div className="w-full max-w-2xl bg-white/90 backdrop-blur-2xl rounded-3xl p-6 sm:p-8 border border-white/85 shadow-[0_20px_45px_-8px_rgba(96,67,95,0.1)] mb-6 flex flex-col gap-6">
        {hasStructuredOptions && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70 block">
                {questionType === 'single_choice' ? 'Choose an option' : 'Suggested responses'}
              </label>
              <span className="text-[11px] font-medium text-[#60435F]/50">Tap to select</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {options.map((optionText) => (
                <motion.button
                  key={optionText}
                  type="button"
                  whileHover={{ y: -2, scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleSend(optionText)}
                  disabled={isSubmitting || isTranscribing}
                  className="p-4 rounded-2xl bg-[#FDF7FA] hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 text-[#60435F] font-bold text-sm text-left transition-all hover:border-[#D67AB1] hover:shadow-md cursor-pointer disabled:opacity-50 flex items-center justify-between group"
                >
                  <span className="leading-snug">{optionText}</span>
                  <ArrowRight className="w-4 h-4 text-[#D67AB1] shrink-0 opacity-40 group-hover:opacity-100 transition-opacity ml-2" />
                </motion.button>
              ))}
            </div>
          </div>
        )}

        {/* Voice Option Divider */}
        {hasStructuredOptions && (
          <div className="flex items-center gap-4 my-0">
            <div className="flex-1 h-px bg-[#E2A3C7]/30" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#60435F]/40">or speak naturally</span>
            <div className="flex-1 h-px bg-[#E2A3C7]/30" />
          </div>
        )}

        {/* Spoken / Typed Input Bar */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleVoice}
              disabled={isSubmitting || isTranscribing}
              className={`
                h-14 px-5 rounded-2xl flex items-center gap-2.5 font-bold text-sm shrink-0 transition-all cursor-pointer border
                ${
                  isRecording
                    ? 'bg-[#E14D62] text-white border-[#E14D62] shadow-lg animate-pulse'
                    : isTranscribing
                    ? 'bg-[#A8DCD9] text-[#2B605E] border-[#A8DCD9]'
                    : 'bg-[#A8DCD9]/30 text-[#2B605E] hover:bg-[#A8DCD9]/50 border-[#A8DCD9]/70'
                }
              `}
            >
              {isTranscribing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Transcribing...</span>
                </>
              ) : isRecording ? (
                <>
                  <MicOff className="w-5 h-5 animate-pulse" />
                  <span>Stop</span>
                </>
              ) : (
                <>
                  <Mic className="w-5 h-5" />
                  <span>Tell Nia</span>
                </>
              )}
            </button>

            <input
              type="text"
              value={typedAnswer}
              onChange={(e) => setTypedAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend();
              }}
              placeholder="Type your reply..."
              disabled={isSubmitting || isTranscribing}
              className="flex-1 h-14 rounded-2xl px-4 bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] text-sm focus:outline-none focus:ring-3 focus:ring-[#D67AB1]/30 focus:border-[#D67AB1]"
            />

            <PrimaryButton
              size="md"
              disabled={!typedAnswer.trim() || isSubmitting || isTranscribing}
              isLoading={isSubmitting}
              onClick={() => handleSend()}
              icon={<Send className="w-4 h-4" />}
            >
              Send
            </PrimaryButton>
          </div>

          {voiceError && (
            <p className="text-xs text-[#E14D62] font-medium bg-[#E14D62]/10 px-3 py-1 rounded-full w-fit">
              {voiceError}
            </p>
          )}
        </div>
      </div>


      {/* Clean Minimalist Context History (shows only recent turns) */}
      {recentHistory.length > 0 && (
        <div className="w-full max-w-2xl bg-white/50 backdrop-blur-md rounded-2xl p-4 border border-[#E2A3C7]/20 flex flex-col gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#60435F]/50">
            Recent Context
          </span>
          <div className="flex flex-col gap-1.5 text-xs text-[#60435F]/75">
            {recentHistory.map((turn, i) => (
              <div key={i} className="flex gap-2">
                <span className="font-bold shrink-0 text-[#60435F]">
                  {turn.role === 'user' ? 'You:' : 'Nia:'}
                </span>
                <span className="line-clamp-1">{turn.content}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
