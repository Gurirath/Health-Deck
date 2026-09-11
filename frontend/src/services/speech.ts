// Real Speech-to-Text service connecting to faster-whisper backend
import { ApiService } from './api';

export type SpeechRecordingState = 'idle' | 'recording' | 'transcribing' | 'error';

export interface AudioRecorderSession {
  stop: () => void;
  cancel: () => void;
}

export class SpeechService {
  private static activeRecorderSession: AudioRecorderSession | null = null;

  static isSupported(): boolean {
    return (
      typeof window !== 'undefined' &&
      typeof navigator !== 'undefined' &&
      Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    );
  }

  static async startRecording(
    onStateChange: (state: SpeechRecordingState) => void,
    onResult: (transcriptText: string) => void,
    onError: (errorMessage: string) => void
  ): Promise<AudioRecorderSession> {
    if (!this.isSupported()) {
      const msg = 'Microphone access is not supported in this browser. Please type below.';
      onError(msg);
      onStateChange('error');
      return { stop: () => {}, cancel: () => {} };
    }

    // If an existing session is running, cleanly stop/cancel it first
    if (this.activeRecorderSession) {
      try {
        this.activeRecorderSession.cancel();
      } catch {}
      this.activeRecorderSession = null;
    }

    let stream: MediaStream | null = null;
    let recorder: MediaRecorder | null = null;
    const audioChunks: Blob[] = [];
    let isCancelled = false;
    let isStopped = false;

    const cleanupStream = () => {
      if (stream) {
        stream.getTracks().forEach((track) => {
          try {
            track.stop();
          } catch {}
        });
        stream = null;
      }
    };

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Determine best supported mime type
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/wav',
      ].find((type) => MediaRecorder.isTypeSupported(type)) || '';

      const options = mimeType ? { mimeType } : undefined;
      recorder = new MediaRecorder(stream, options);

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        cleanupStream();

        if (isCancelled) {
          audioChunks.length = 0;
          onStateChange('idle');
          return;
        }

        if (audioChunks.length === 0) {
          onStateChange('idle');
          onError('No audio recorded. Please speak clearly or type below.');
          return;
        }

        const resolvedMime = recorder?.mimeType || mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunks, { type: resolvedMime });
        audioChunks.length = 0;

        if (audioBlob.size === 0) {
          onStateChange('idle');
          onError('Empty audio recording. Please try speaking again or type below.');
          return;
        }

        onStateChange('transcribing');
        const { text, error } = await ApiService.transcribeAudio(audioBlob);

        if (error) {
          onError(error);
          onStateChange('error');
        } else if (text && text.trim()) {
          onResult(text.trim());
          onStateChange('idle');
        } else {
          onError('No speech detected. Please speak clearly or type below.');
          onStateChange('idle');
        }
      };

      recorder.onerror = (e: any) => {
        cleanupStream();
        onError(e.error?.message || 'Recording error occurred.');
        onStateChange('error');
      };

      recorder.start(250); // collect 250ms chunks
      onStateChange('recording');

      const session: AudioRecorderSession = {
        stop: () => {
          if (isStopped || isCancelled) return;
          isStopped = true;
          if (recorder && recorder.state === 'recording') {
            try {
              recorder.stop();
            } catch {
              cleanupStream();
              onStateChange('idle');
            }
          } else {
            cleanupStream();
            onStateChange('idle');
          }
          if (SpeechService.activeRecorderSession === session) {
            SpeechService.activeRecorderSession = null;
          }
        },
        cancel: () => {
          if (isCancelled) return;
          isCancelled = true;
          isStopped = true;
          audioChunks.length = 0;
          if (recorder && recorder.state === 'recording') {
            try {
              recorder.stop();
            } catch {
              cleanupStream();
              onStateChange('idle');
            }
          } else {
            cleanupStream();
            onStateChange('idle');
          }
          if (SpeechService.activeRecorderSession === session) {
            SpeechService.activeRecorderSession = null;
          }
        },
      };

      this.activeRecorderSession = session;
      return session;
    } catch (err: any) {
      cleanupStream();
      const errorMsg =
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Microphone permission denied. Please allow microphone access or type below.'
          : err.message || 'Could not access microphone';
      onError(errorMsg);
      onStateChange('error');
      return { stop: () => {}, cancel: () => {} };
    }
  }
}

