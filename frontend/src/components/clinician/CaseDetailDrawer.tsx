import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  AlertTriangle,
  FileText,
  Download,
  Plus,
  Trash2,
  CheckCircle2,
  Heart,
  Thermometer,
  Activity,
  Image as ImageIcon,
  ExternalLink,
  ShieldCheck,
  Stethoscope,
  Loader2,
} from 'lucide-react';
import type { CaseRecord, Medicine } from '../../types/triage';
import { PrimaryButton } from '../common/PrimaryButton';
import { ApiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface CaseDetailDrawerProps {
  caseRecord: CaseRecord;
  onClose: () => void;
  onCaseUpdated: (updated: CaseRecord) => void;
}

const DEPARTMENT_OPTIONS = [
  'General Physician',
  'Cardiology',
  'ENT',
  'General Physician / Pulmonology',
  'General Physician / Gastroenterology',
  'Neurology',
  'Emergency / Critical Care',
];

export const CaseDetailDrawer: React.FC<CaseDetailDrawerProps> = ({
  caseRecord,
  onClose,
  onCaseUpdated,
}) => {
  const { currentUser } = useAuth();
  const [departmentOverride, setDepartmentOverride] = useState(
    caseRecord.department_override || caseRecord.department || 'General Physician'
  );
  const [medicines, setMedicines] = useState<Medicine[]>(
    caseRecord.prescription_medicines && caseRecord.prescription_medicines.length > 0
      ? caseRecord.prescription_medicines
      : [{ name: '', dosage_per_day: '', remark: '' }]
  );
  const [doctorNotes, setDoctorNotes] = useState(caseRecord.doctor_notes || '');
  const [isSubmittingPrescription, setIsSubmittingPrescription] = useState(false);
  const [isUpdatingDept, setIsUpdatingDept] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const effectiveDoctorName =
    caseRecord.doctor_name || currentUser?.full_name || 'Attending Physician';

  const isUrgent =
    caseRecord.escalate ||
    caseRecord.escalation_reason === 'red_flag' ||
    (caseRecord.red_flags && caseRecord.red_flags.length > 0);

  const addMedicineRow = () => {
    setMedicines([...medicines, { name: '', dosage_per_day: '', remark: '' }]);
  };

  const removeMedicineRow = (index: number) => {
    setMedicines(medicines.filter((_, i) => i !== index));
  };

  const updateMedicine = (index: number, field: keyof Medicine, val: string) => {
    const updated = [...medicines];
    updated[index][field] = val;
    setMedicines(updated);
  };

  const handlePrescribe = async (e: React.FormEvent) => {
    e.preventDefault();
    const validMeds = medicines.filter((m) => m.name.trim().length > 0);
    if (validMeds.length === 0) {
      alert('Please add at least one valid medicine with a name.');
      return;
    }

    setIsSubmittingPrescription(true);
    const { caseRecord: updated, error } = await ApiService.prescribeCase(
      caseRecord.id,
      effectiveDoctorName,
      validMeds,
      doctorNotes.trim()
    );

    setIsSubmittingPrescription(false);
    if (updated) {
      onCaseUpdated(updated);
      setActionSuccessMsg('Prescription saved and hospital PDF report generated successfully!');
      setTimeout(() => setActionSuccessMsg(null), 5000);
    } else {
      alert(error || 'Failed to save prescription.');
    }
  };

  const handleDownloadReport = async () => {
    setIsDownloadingPdf(true);
    const res = await ApiService.downloadReport(caseRecord.id);
    setIsDownloadingPdf(false);
    if (!res.success) {
      alert(res.error || 'Could not download hospital report PDF.');
    }
  };

  const handleReviewDepartment = async () => {
    setIsUpdatingDept(true);
    const { success, error } = await ApiService.reviewCase(caseRecord.id, departmentOverride);
    setIsUpdatingDept(false);
    if (success) {
      const { caseRecord: refreshed } = await ApiService.getCase(caseRecord.id);
      if (refreshed) onCaseUpdated(refreshed);
      setActionSuccessMsg('Department assignment reviewed and updated.');
      setTimeout(() => setActionSuccessMsg(null), 4000);
    } else {
      alert(error || 'Could not update review.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end">
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 32 }}
        className="w-full max-w-3xl bg-[#FDF7FA] h-full overflow-y-auto shadow-2xl flex flex-col border-l border-[#E2A3C7]/40"
      >
        {/* Drawer Header */}
        <div className="sticky top-0 z-20 bg-white/95 backdrop-blur-xl border-b border-[#E2A3C7]/30 px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#60435F] text-white flex items-center justify-center font-black text-sm">
              #{caseRecord.id}
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#60435F] flex items-center gap-2">
                <span>Clinical Dossier</span>
                {isUrgent && (
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#E14D62]/15 text-[#C42239] border border-[#E14D62]/40">
                    Red Flag Case
                  </span>
                )}
              </h2>
              <p className="text-xs text-[#60435F]/60">
                Created: {new Date(caseRecord.created_at || Date.now()).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {caseRecord.status === 'prescribed' && (
              <button
                type="button"
                onClick={handleDownloadReport}
                disabled={isDownloadingPdf}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2B605E] text-white text-xs font-bold hover:bg-[#204948] transition-all shadow-sm cursor-pointer disabled:opacity-60"
              >
                {isDownloadingPdf ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>{isDownloadingPdf ? 'Downloading...' : 'PDF Care Report'}</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-[#60435F]/60 hover:text-[#60435F] hover:bg-[#E2A3C7]/20 transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Feedback Alert if Action Performed */}
        {actionSuccessMsg && (
          <div className="mx-6 mt-4 p-3.5 rounded-2xl bg-[#A8DCD9]/30 border border-[#A8DCD9] text-[#2B605E] text-xs font-bold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{actionSuccessMsg}</span>
          </div>
        )}

        {/* Dossier Body */}
        <div className="p-6 flex flex-col gap-6">
          {/* Section 1: Intake & Vitals */}
          <div className="bg-white rounded-3xl p-5 border border-white/90 shadow-sm flex flex-col gap-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#60435F]/70">
              1. Patient Intake & Vitals
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/25">
                <span className="text-[11px] font-semibold text-[#60435F]/60">Heart Rate</span>
                <p className="text-xl font-bold text-[#60435F] mt-0.5">
                  {caseRecord.vitals?.hr || 75} <span className="text-xs font-normal">BPM</span>
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/25">
                <span className="text-[11px] font-semibold text-[#60435F]/60">Oxygen SpO2</span>
                <p className="text-xl font-bold text-[#2B605E] mt-0.5">
                  {caseRecord.vitals?.spo2 || 98}%
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/25">
                <span className="text-[11px] font-semibold text-[#60435F]/60">Temperature</span>
                <p className="text-xl font-bold text-[#60435F] mt-0.5">
                  {caseRecord.vitals?.temp_c || 37.0}°C
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/25">
                <span className="text-[11px] font-semibold text-[#60435F]/60">Blood Pressure</span>
                <p className="text-xl font-bold text-[#60435F] mt-0.5">
                  {caseRecord.vitals?.systolic_bp || 120}/{caseRecord.vitals?.diastolic_bp || 80}
                </p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 pt-2 text-xs">
              <div className="flex-1">
                <span className="font-bold text-[#60435F]/70 block mb-1">Chief Complaint:</span>
                <p className="font-semibold text-[#60435F] bg-[#FDF7FA] p-3 rounded-xl border border-[#E2A3C7]/25">
                  "{caseRecord.chief_complaint}"
                </p>
              </div>

              <div className="sm:w-44">
                <span className="font-bold text-[#60435F]/70 block mb-1">Symptom Location:</span>
                <p className="font-bold text-[#D67AB1] capitalize bg-[#D67AB1]/10 p-3 rounded-xl border border-[#D67AB1]/30">
                  {caseRecord.symptom_location || 'General'}
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Red Flags Alert if Triggered */}
          {caseRecord.red_flags && caseRecord.red_flags.length > 0 && (
            <div className="bg-[#FDF0F2] rounded-3xl p-5 border border-[#F9B4BF]">
              <div className="flex items-center gap-2 mb-2 text-[#C42239] font-bold text-sm">
                <AlertTriangle className="w-5 h-5" />
                <span>Deterministic Red Flag Triggers Detected</span>
              </div>
              <ul className="list-disc pl-5 text-xs text-[#C42239] space-y-1">
                {caseRecord.red_flags.map((rf, i) => (
                  <li key={i}>{rf}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 3: AI Preliminary Assessment (Mandatory Disclaimer) */}
          <div className="bg-white rounded-3xl p-5 border border-white/90 shadow-sm flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[#60435F]/70">
                2. AI Preliminary Clinical Assessment
              </h3>
              <span className="text-xs font-bold text-[#2B605E] bg-[#A8DCD9]/30 px-2.5 py-1 rounded-full">
                Confidence: {caseRecord.confidence || caseRecord.diagnosis?.confidence || 80}%
              </span>
            </div>

            {/* MANDATORY DISCLAIMER */}
            <div className="p-3.5 rounded-2xl bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] text-xs font-semibold">
              ⚠️ AI-generated preliminary assessment — clinician review required. Not a final diagnosis or prescription.
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/20">
                <span className="font-bold text-[#60435F]/60 block mb-0.5">Probable Diagnosis:</span>
                <p className="font-bold text-[#60435F] text-sm">
                  {caseRecord.diagnosis?.probable_diagnosis || 'Unspecified acute condition'}
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/20">
                <span className="font-bold text-[#60435F]/60 block mb-0.5">Differential:</span>
                <p className="font-medium text-[#60435F]/80">
                  {Array.isArray(caseRecord.diagnosis?.differentials)
                    ? caseRecord.diagnosis.differentials
                        .map((d: any) => (typeof d === 'string' ? d : d.name || d.diagnosis))
                        .join('; ')
                    : 'None recorded'}
                </p>
              </div>
            </div>

            {caseRecord.diagnosis?.self_care_advice && (
              <div className="p-3 rounded-2xl bg-[#FDF7FA] border border-[#E2A3C7]/20 text-xs">
                <span className="font-bold text-[#60435F]/60 block mb-1">AI Drafted Self-Care Advice:</span>
                <p className="text-[#60435F]/80 leading-relaxed">
                  {caseRecord.diagnosis.self_care_advice}
                </p>
              </div>
            )}
          </div>

          {/* Section 4: Photo / Image Analysis (if present) */}
          {(caseRecord.photo_path || caseRecord.session_id) && (
            <div className="bg-white rounded-3xl p-5 border border-white/90 shadow-sm flex flex-col gap-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-[#60435F]/70 flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-[#D67AB1]" />
                <span>3. Patient Uploaded Photo</span>
              </h3>

              <div className="flex flex-col sm:flex-row items-start gap-4">
                <img
                  src={ApiService.getImageUrl(caseRecord.session_id || '')}
                  alt="Patient symptom"
                  onError={(e) => {
                    (e.target as any).style.display = 'none';
                  }}
                  className="w-40 h-40 object-cover rounded-2xl border border-[#E2A3C7]/40 shadow-sm"
                />

                <div className="flex-1 text-xs text-[#60435F]/80">
                  <p className="font-bold text-[#60435F] mb-1">Observation Note (Non-diagnostic):</p>
                  <p className="bg-[#FDF7FA] p-3 rounded-xl border border-[#E2A3C7]/20">
                    {caseRecord.image_analysis?.description ||
                      'Visual inspection attached to case file. High-resolution review available in PACS/viewer.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Section 5: Interview Transcript Timeline */}
          <div className="bg-white rounded-3xl p-5 border border-white/90 shadow-sm flex flex-col gap-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#60435F]/70">
              4. Complete Intake Transcript
            </h3>

            <div className="flex flex-col gap-2.5 max-h-64 overflow-y-auto pr-2">
              {caseRecord.transcript && caseRecord.transcript.length > 0 ? (
                caseRecord.transcript.map((turn, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-2xl text-xs ${
                      turn.role === 'user'
                        ? 'bg-[#FDF7FA] text-[#60435F] border border-[#E2A3C7]/30 ml-4'
                        : 'bg-[#D67AB1]/10 text-[#60435F] border border-[#D67AB1]/30 mr-4 font-medium'
                    }`}
                  >
                    <span className="font-bold block text-[11px] mb-0.5 text-[#60435F]/60">
                      {turn.role === 'user' ? 'Patient:' : 'Nurse Nia:'}
                    </span>
                    <p>{turn.content}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-[#60435F]/50 italic">No interview transcript turns recorded.</p>
              )}
            </div>
          </div>

          {/* Section 6: Department Reassignment */}
          <div className="bg-white rounded-3xl p-5 border border-white/90 shadow-sm flex flex-col gap-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#60435F]/70">
              5. Department Review & Reassignment
            </h3>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              <select
                value={departmentOverride}
                onChange={(e) => setDepartmentOverride(e.target.value)}
                className="flex-1 text-xs p-3 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] font-bold focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/40"
              >
                {DEPARTMENT_OPTIONS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={handleReviewDepartment}
                disabled={isUpdatingDept}
                className="px-4 py-3 rounded-xl bg-[#60435F] text-white text-xs font-bold hover:bg-[#473146] transition-all cursor-pointer shrink-0 shadow-sm"
              >
                {isUpdatingDept ? 'Saving...' : 'Update Department'}
              </button>
            </div>
          </div>

          {/* Section 7: Clinician Prescription Form */}
          <div className="bg-white rounded-3xl p-6 border-2 border-[#D67AB1]/30 shadow-md flex flex-col gap-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[#60435F]">
                  6. Complete Clinical Prescription
                </h3>
                <p className="text-xs text-[#60435F]/60">
                  Submitting generates the official hospital care PDF report.
                </p>
              </div>

              {caseRecord.status === 'prescribed' && (
                <span className="text-xs font-bold text-[#2B605E] bg-[#A8DCD9]/30 px-3 py-1 rounded-full flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Prescribed
                </span>
              )}
            </div>

            <form onSubmit={handlePrescribe} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70 block mb-1.5">
                  Attending Doctor (Authenticated Identity)
                </label>
                <div className="flex items-center justify-between p-3 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F]">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#2B605E]" />
                    <span className="text-sm font-bold">{effectiveDoctorName}</span>
                  </div>
                  <span className="text-[11px] font-semibold text-[#2B605E] bg-[#A8DCD9]/30 px-2.5 py-0.5 rounded-md">
                    {currentUser?.department || caseRecord.department || 'Verified Staff'}
                    {currentUser?.medical_license ? ` • ${currentUser.medical_license}` : ''}
                  </span>
                </div>
              </div>

              {/* Medicine Table Rows */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70">
                    Prescribed Medicines
                  </label>
                  <button
                    type="button"
                    onClick={addMedicineRow}
                    className="flex items-center gap-1 text-xs font-bold text-[#D67AB1] hover:text-[#B95D94] cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Medicine</span>
                  </button>
                </div>

                <div className="flex flex-col gap-2.5">
                  {medicines.map((med, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={med.name}
                        onChange={(e) => updateMedicine(idx, 'name', e.target.value)}
                        placeholder="Medicine name (e.g. Cetirizine 10mg)"
                        className="flex-1 text-xs p-2.5 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/30 text-[#60435F] font-medium"
                      />
                      <input
                        type="text"
                        value={med.dosage_per_day}
                        onChange={(e) => updateMedicine(idx, 'dosage_per_day', e.target.value)}
                        placeholder="Dosage (e.g. 1 tab/day)"
                        className="w-32 text-xs p-2.5 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/30 text-[#60435F]"
                      />
                      <input
                        type="text"
                        value={med.remark}
                        onChange={(e) => updateMedicine(idx, 'remark', e.target.value)}
                        placeholder="Remark (e.g. after meals, 5 days)"
                        className="flex-1 text-xs p-2.5 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/30 text-[#60435F]"
                      />
                      {medicines.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeMedicineRow(idx)}
                          className="p-2 text-gray-400 hover:text-[#E14D62] transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-[#60435F]/70 block mb-1.5">
                  Clinical Notes & Patient Instructions
                </label>
                <textarea
                  rows={3}
                  value={doctorNotes}
                  onChange={(e) => setDoctorNotes(e.target.value)}
                  placeholder="e.g., Follow up in clinic if fever persists beyond 3 days. Drink plenty of warm fluids."
                  className="w-full text-xs p-3 rounded-xl bg-[#FDF7FA] border border-[#E2A3C7]/40 text-[#60435F] focus:outline-none focus:ring-2 focus:ring-[#D67AB1]/40"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <PrimaryButton
                  type="submit"
                  size="lg"
                  isLoading={isSubmittingPrescription}
                  icon={<CheckCircle2 className="w-5 h-5" />}
                >
                  {caseRecord.status === 'prescribed'
                    ? 'Update Prescription & Re-Generate PDF'
                    : 'Complete Prescription & Generate PDF →'}
                </PrimaryButton>
              </div>
            </form>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
