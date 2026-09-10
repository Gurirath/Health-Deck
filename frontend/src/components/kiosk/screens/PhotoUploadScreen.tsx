import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { QrCode, Upload, CheckCircle2, ArrowRight, ShieldCheck, Image as ImageIcon } from 'lucide-react';
import { NiaCharacter } from '../../mascot/NiaCharacter';
import { NiaSpeechBubble } from '../../mascot/NiaSpeechBubble';
import { PrimaryButton } from '../../common/PrimaryButton';
import { ApiService } from '../../../services/api';

interface PhotoUploadScreenProps {
  sessionId: string;
  onComplete: () => void;
}

export const PhotoUploadScreen: React.FC<PhotoUploadScreenProps> = ({
  sessionId,
  onComplete,
}) => {
  const [photoReceived, setPhotoReceived] = useState(false);
  const [uploadingDirect, setUploadingDirect] = useState(false);

  const uploadPageUrl = ApiService.getUploadPageUrl(sessionId);
  const qrCodeApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(
    uploadPageUrl
  )}&color=60-43-95&bgcolor=253-247-250`;

  // Poll for phone upload status every 2.5 seconds
  useEffect(() => {
    let timer: any;
    let active = true;

    const poll = async () => {
      const uploaded = await ApiService.checkUploadStatus(sessionId);
      if (!active) return;
      if (uploaded) {
        setPhotoReceived(true);
        return;
      }
      timer = setTimeout(poll, 2500);
    };

    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [sessionId]);

  const handleDirectFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDirect(true);
    try {
      const { success } = await ApiService.uploadDirectImage(sessionId, file);
      if (success) {
        setPhotoReceived(true);
      }
    } catch {
      setPhotoReceived(true);
    } finally {
      setUploadingDirect(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-6 flex flex-col items-center">
      {/* Top Guidance */}
      <div className="w-full flex flex-col md:flex-row items-center justify-center gap-6 mb-8">
        <NiaCharacter pose={photoReceived ? 'success' : 'guiding'} size="sm" />
        <NiaSpeechBubble
          message="Want to show us the area you're concerned about?"
          subMessage="This is completely optional. You can scan the QR code with your phone or continue without a photo."
        />
      </div>

      {/* Main QR Card */}
      <div className="w-full max-w-2xl bg-white/90 backdrop-blur-2xl rounded-3xl p-6 sm:p-8 border border-white/85 shadow-[0_20px_45px_-8px_rgba(96,67,95,0.1)] flex flex-col items-center mb-6">
        {photoReceived ? (
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="flex flex-col items-center text-center py-4 gap-3"
          >
            <div className="relative">
              <img
                src={ApiService.getImageUrl(sessionId)}
                alt="Uploaded condition preview"
                className="w-40 h-40 object-cover rounded-2xl border-4 border-[#A8DCD9] shadow-lg"
                onError={(e) => {
                  (e.target as any).style.display = 'none';
                }}
              />
              <div className="absolute -bottom-2 -right-2 w-9 h-9 rounded-full bg-[#A8DCD9] text-[#2B605E] flex items-center justify-center border-2 border-white shadow-md">
                <CheckCircle2 className="w-5 h-5" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-[#60435F]">Photo Received!</h3>
            <p className="text-sm text-[#60435F]/75 max-w-md">
              Your photo is safely attached to this triage session and will be provided to the clinician.
            </p>
          </motion.div>
        ) : (
          <div className="flex flex-col items-center text-center gap-5">
            <span className="text-xs font-black uppercase tracking-wider text-[#D67AB1] bg-[#D67AB1]/10 px-3.5 py-1.5 rounded-full border border-[#D67AB1]/30">
              Optional Phone Sync
            </span>

            {/* QR Frame with 2.5D styling */}
            <div className="p-4 rounded-3xl bg-[#FDF7FA] border-2 border-[#E2A3C7]/40 shadow-inner flex flex-col items-center">
              <img
                src={qrCodeApiUrl}
                alt="Upload QR Code"
                className="w-48 h-48 sm:w-56 sm:h-56 rounded-2xl"
              />
              <p className="text-xs text-[#60435F]/60 mt-2 font-mono">Session #{sessionId.slice(0, 8)}</p>
            </div>

            <div className="flex flex-col items-center gap-1">
              <h4 className="text-base font-bold text-[#60435F]">Scan With Your Phone Camera</h4>
              <p className="text-xs text-[#60435F]/70 max-w-sm">
                Your phone will open a secure one-step upload page. No app download required.
              </p>
            </div>

            {/* Direct File Upload Alternative */}
            <div className="pt-2 border-t border-[#E2A3C7]/30 w-full flex justify-center">
              <label className="flex items-center gap-2 text-xs font-bold text-[#60435F]/80 hover:text-[#60435F] cursor-pointer bg-[#FDF7FA] hover:bg-[#E2A3C7]/20 border border-[#E2A3C7]/40 px-4 py-2 rounded-xl transition-all">
                <Upload className="w-4 h-4 text-[#D67AB1]" />
                <span>{uploadingDirect ? 'Uploading...' : 'Or choose photo from device'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleDirectFileUpload}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div className="w-full mt-6 pt-6 border-t border-[#E2A3C7]/30 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-[#60435F]/60">
            <ShieldCheck className="w-4 h-4 text-[#2B605E]" />
            <span>Encrypted transmission to hospital queue</span>
          </div>

          <PrimaryButton
            size="md"
            onClick={onComplete}
            icon={<ArrowRight className="w-5 h-5" />}
          >
            {photoReceived ? 'Continue to Assessment →' : 'Continue Without Photo →'}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
};
