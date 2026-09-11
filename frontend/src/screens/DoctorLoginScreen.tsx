import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Lock, User, ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';
import { HealthDeckLogo } from '../components/common/HealthDeckLogo';
import { useAuth } from '../context/AuthContext';

interface DoctorLoginScreenProps {
  onBackToKiosk: () => void;
}

export const DoctorLoginScreen: React.FC<DoctorLoginScreenProps> = ({ onBackToKiosk }) => {
  const { login, sessionExpired, clearSessionExpired } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage('Please enter both username/email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    clearSessionExpired();

    const result = await login({
      username: username.trim(),
      password,
    });

    setIsSubmitting(false);

    if (!result.success) {
      setErrorMessage(result.error || 'Authentication failed. Please check your credentials.');
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#FDF7FA] flex flex-col items-center justify-center p-4 sm:p-6 text-[#60435F] relative selection:bg-[#D67AB1]/20">
      {/* Background Soft Orbs for 2.5D Depth */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#D67AB1]/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#A8DCD9]/15 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Main Login Card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        className="w-full max-w-md bg-white/90 backdrop-blur-2xl rounded-3xl p-7 sm:p-9 border border-white/90 shadow-[0_20px_50px_-10px_rgba(96,67,95,0.12)] flex flex-col gap-6"
      >
        {/* Header & Logo */}
        <div className="flex flex-col items-center text-center gap-3">
          <HealthDeckLogo size="md" />

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#60435F]/5 border border-[#E2A3C7]/40 text-[#60435F] text-[11px] font-bold uppercase tracking-wider mt-1">
            <ShieldCheck className="w-3.5 h-3.5 text-[#D67AB1]" />
            <span>Clinician Portal</span>
          </div>

          <h1 className="text-2xl font-black text-[#60435F] tracking-tight">
            Doctor Authentication
          </h1>
          <p className="text-xs text-[#60435F]/65 leading-relaxed">
            Authorized medical staff sign-in to review intake cases and issue clinical prescriptions.
          </p>
        </div>

        {/* Session Expired Banner */}
        {sessionExpired && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-3.5 rounded-2xl bg-[#FFF6E5] border border-[#FCD385] flex items-start gap-2.5 text-xs text-[#8A5B00]"
          >
            <AlertCircle className="w-4 h-4 text-[#D97706] shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Session Expired</p>
              <p className="text-[11px] text-[#8A5B00]/90 mt-0.5">
                Your session has timed out or authorization was revoked. Please log in again.
              </p>
            </div>
          </motion.div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-3.5 rounded-2xl bg-[#FDF0F2] border border-[#F9B4BF] flex items-start gap-2.5 text-xs text-[#C42239]"
          >
            <AlertCircle className="w-4 h-4 text-[#E14D62] shrink-0 mt-0.5" />
            <p className="font-medium">{errorMessage}</p>
          </motion.div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="username"
              className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70 block mb-1.5"
            >
              Username or Hospital Email
            </label>
            <div className="relative flex items-center">
              <User className="w-4 h-4 text-[#60435F]/40 absolute left-3.5 pointer-events-none" />
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. dr.chen or name@hospital.internal"
                required
                disabled={isSubmitting}
                className="w-full text-sm pl-10 pr-3.5 py-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] placeholder-[#60435F]/35 font-medium focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/40 focus:border-[#D67AB1] transition-all disabled:opacity-60"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70 block mb-1.5"
            >
              Password
            </label>
            <div className="relative flex items-center">
              <Lock className="w-4 h-4 text-[#60435F]/40 absolute left-3.5 pointer-events-none" />
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your doctor password"
                required
                disabled={isSubmitting}
                className="w-full text-sm pl-10 pr-3.5 py-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] placeholder-[#60435F]/35 font-medium focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/40 focus:border-[#D67AB1] transition-all disabled:opacity-60"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3.5 px-5 rounded-2xl bg-gradient-to-r from-[#D67AB1] to-[#B95D94] text-white font-black text-sm tracking-wide shadow-[0_8px_20px_-4px_rgba(214,122,177,0.45)] hover:shadow-[0_12px_24px_-4px_rgba(214,122,177,0.55)] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-65 disabled:pointer-events-none"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Verifying Credentials...</span>
              </>
            ) : (
              <span>Sign In to Clinician Workspace</span>
            )}
          </button>
        </form>

        {/* Back to Kiosk Action */}
        <div className="pt-3 border-t border-[#E2A3C7]/30 flex justify-center">
          <button
            type="button"
            onClick={onBackToKiosk}
            className="flex items-center gap-2 text-xs font-bold text-[#60435F]/70 hover:text-[#60435F] transition-colors py-1 px-3 rounded-xl hover:bg-[#60435F]/5 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Patient Kiosk</span>
          </button>
        </div>
      </motion.div>

      <p className="text-[11px] text-[#60435F]/50 mt-6 text-center">
        Protected Health Information (PHI) • Clinical Access Encrypted (HS256)
      </p>
    </div>
  );
};
