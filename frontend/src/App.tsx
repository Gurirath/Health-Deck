import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import { KioskShell } from './components/kiosk/KioskShell';
import { ClinicianShell } from './components/clinician/ClinicianShell';
import { DoctorLoginScreen } from './screens/DoctorLoginScreen';
import { WelcomeScreen } from './components/kiosk/screens/WelcomeScreen';
import { VitalsScreen } from './components/kiosk/screens/VitalsScreen';
import { ComplaintScreen } from './components/kiosk/screens/ComplaintScreen';
import { BodyMapScreen } from './components/kiosk/screens/BodyMapScreen';
import { ConversationScreen } from './components/kiosk/screens/ConversationScreen';
import { PhotoUploadScreen } from './components/kiosk/screens/PhotoUploadScreen';
import { ProcessingScreen } from './components/kiosk/screens/ProcessingScreen';
import { CompletionScreen } from './components/kiosk/screens/CompletionScreen';
import type { AppMode, KioskScreen, Vitals, TriageState } from './types/triage';
import { DEFAULT_VITALS } from './constants/vitalsDefaults';
import { ApiService } from './services/api';
import { AuthProvider, useAuth } from './context/AuthContext';

function HealthDeckContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const [mode, setMode] = useState<AppMode>('kiosk');
  const [kioskScreen, setKioskScreen] = useState<KioskScreen>('welcome');

  // Intake State
  const [sessionId, setSessionId] = useState<string>(() =>
    'sess-' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36)
  );
  const [vitals, setVitals] = useState<Vitals>(DEFAULT_VITALS);
  const [chiefComplaint, setChiefComplaint] = useState<string>('');
  const [symptomLocation, setSymptomLocation] = useState<string>('head');
  const [triageState, setTriageState] = useState<TriageState | null>(null);
  const [isSubmittingTurn, setIsSubmittingTurn] = useState<boolean>(false);
  const [submittedCaseId, setSubmittedCaseId] = useState<number | null>(null);

  const [apiError, setApiError] = useState<string | null>(null);

  // Reset helper
  const resetKiosk = () => {
    setSessionId('sess-' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36));
    setVitals(DEFAULT_VITALS);
    setChiefComplaint('');
    setSymptomLocation('head');
    setTriageState(null);
    setSubmittedCaseId(null);
    setIsSubmittingTurn(false);
    setApiError(null);
    setKioskScreen('welcome');
  };

  // Step 1: Start from Welcome
  const handleStart = () => {
    setApiError(null);
    setKioskScreen('vitals');
  };

  // Step 2: Confirm Vitals -> Go to Location (Requirement 4)
  const handleConfirmVitals = (newVitals: Vitals) => {
    setVitals(newVitals);
    setApiError(null);
    setKioskScreen('body_map');
  };

  // Step 3: Confirm Location -> Go to Chief Complaint (Requirement 4)
  const handleConfirmBodyMap = (location: string) => {
    setSymptomLocation(location);
    setApiError(null);
    setKioskScreen('complaint');
  };

  // Step 4: Submit Chief Complaint -> Invoke Backend LangGraph (POST /triage/start)
  const handleSubmitComplaint = async (complaint: string) => {
    setChiefComplaint(complaint);
    setApiError(null);
    setKioskScreen('processing');

    const { state, error } = await ApiService.startTriage(
      vitals,
      symptomLocation,
      complaint,
      sessionId
    );

    if (state) {
      setTriageState(state);
      if (state.status === 'awaiting_answer' && state.next_question) {
        setKioskScreen('conversation');
      } else {
        // Ready to diagnose / red flag / complete -> advance to optional photo
        setKioskScreen('photo');
      }
    } else {
      setApiError(error || 'Could not communicate with the triage agent. Please ensure the backend is running.');
      setKioskScreen('complaint');
    }
  };

  // Step 5: Answer AI follow-up questions -> Invoke Backend LangGraph (POST /triage/step)
  const handleConversationAnswer = async (answer: string) => {
    if (!triageState) return;

    setIsSubmittingTurn(true);
    setApiError(null);
    const { state: updated, error } = await ApiService.stepTriage(triageState, answer);
    setIsSubmittingTurn(false);

    if (updated) {
      setTriageState(updated);
      if (updated.status === 'awaiting_answer' && updated.next_question) {
        // Continue dialogue
        setKioskScreen('conversation');
      } else {
        // LangGraph finished (ready to diagnose or max turns or red flag)
        setKioskScreen('photo');
      }
    } else {
      setApiError(error || 'Could not send answer to agent.');
    }
  };

  // Step 6: Photo screen complete -> finalize and file case (POST /cases)
  const handlePhotoComplete = async () => {
    setKioskScreen('processing');
    setApiError(null);

    if (triageState) {
      const stateToSave: TriageState = {
        ...triageState,
        session_id: sessionId,
      };
      const { id, error } = await ApiService.saveCase(stateToSave);
      if (id) {
        setSubmittedCaseId(id);

        // Trigger celebratory confetti if normal non-urgent check-in
        if (!triageState.escalate && triageState.escalation_reason !== 'red_flag') {
          try {
            confetti({
              particleCount: 55,
              spread: 60,
              origin: { y: 0.65 },
              colors: ['#D67AB1', '#A8DCD9', '#E2A3C7', '#60435F'],
            });
          } catch {}
        }

        setKioskScreen('completion');
      } else {
        setApiError(error || 'Failed to file case to hospital backend.');
        setKioskScreen('photo');
      }
    } else {
      setKioskScreen('welcome');
    }
  };


  // Clinician Mode Render
  if (mode === 'clinician') {
    if (isLoading) {
      return (
        <div className="min-h-screen w-full bg-[#FDF7FA] flex items-center justify-center text-[#60435F]">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-[#D67AB1] border-t-transparent animate-spin" />
            <p className="text-xs font-bold text-[#60435F]/70">Verifying clinician session...</p>
          </div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return <DoctorLoginScreen onBackToKiosk={() => setMode('kiosk')} />;
    }

    return <ClinicianShell onSwitchToKiosk={() => setMode('kiosk')} />;
  }

  // Kiosk Mode Render
  return (
    <KioskShell
      currentScreen={kioskScreen}
      onReset={resetKiosk}
      onSwitchToClinician={() => setMode('clinician')}
    >
      {kioskScreen === 'welcome' && <WelcomeScreen onStart={handleStart} />}

      {kioskScreen === 'vitals' && (
        <VitalsScreen initialVitals={vitals} onConfirm={handleConfirmVitals} />
      )}

      {kioskScreen === 'body_map' && (
        <BodyMapScreen initialLocation={symptomLocation} onConfirm={handleConfirmBodyMap} />
      )}

      {kioskScreen === 'complaint' && (
        <ComplaintScreen
          symptomLocation={symptomLocation}
          initialComplaint={chiefComplaint}
          errorMessage={apiError}
          onSubmit={handleSubmitComplaint}
        />
      )}

      {kioskScreen === 'conversation' && (
        <ConversationScreen
          currentQuestion={
            triageState?.next_question || 'How would you describe your symptoms right now?'
          }
          questionOptions={triageState?.question_options}
          questionType={triageState?.question_type}
          transcript={triageState?.transcript || []}
          isSubmitting={isSubmittingTurn}
          onAnswer={handleConversationAnswer}
        />
      )}

      {kioskScreen === 'photo' && (
        <PhotoUploadScreen sessionId={sessionId} onComplete={handlePhotoComplete} />
      )}

      {kioskScreen === 'processing' && <ProcessingScreen />}

      {kioskScreen === 'completion' && triageState && submittedCaseId && (
        <CompletionScreen
          caseId={submittedCaseId}
          finalState={triageState}
          onStartNew={resetKiosk}
        />
      )}
    </KioskShell>
  );
}

export function App() {
  return (
    <AuthProvider>
      <HealthDeckContent />
    </AuthProvider>
  );
}

export default App;
