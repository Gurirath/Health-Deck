// Real Speech-to-Text service connecting to faster-whisper backend
import { ApiService } from './api';

export type SpeechRecordingState = 'idle' | 'recording' | 'transcribing' | 'error';

export interface AudioRecorderSession {
  stop: () => void;
  cancel: () => void;
}

export class SpeechService {
  private static mediaRecorder: MediaRecorder | null = null;
  private static audioStream: MediaStream | null = null;
  private static audioChunks: Blob[] = [];

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

    try {
      this.audioChunks = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioStream = stream;

      // Determine best supported mime type
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/wav',
      ].find((type) => MediaRecorder.isTypeSupported(type)) || '';

      const options = mimeType ? { mimeType } : undefined;
      const recorder = new MediaRecorder(stream, options);
      this.mediaRecorder = recorder;

      let isCancelled = false;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop all audio tracks
        stream.getTracks().forEach((track) => track.stop());

        if (isCancelled) {
          onStateChange('idle');
          return;
        }

        if (this.audioChunks.length === 0) {
          onStateChange('idle');
          return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: recorder.mimeType || 'audio/webm' });
        this.audioChunks = [];

        onStateChange('transcribing');
        const { text, error } = await ApiService.transcribeAudio(audioBlob);

        if (error) {
          onError(error);
          onStateChange('error');
        } else if (text) {
          onResult(text);
          onStateChange('idle');
        } else {
          onError('No speech detected. Please speak clearly or type below.');
          onStateChange('idle');
        }
      };

      recorder.onerror = (e: any) => {
        stream.getTracks().forEach((track) => track.stop());
        onError(e.error?.message || 'Recording error occurred.');
        onStateChange('error');
      };

      recorder.start(250); // collect 250ms chunks
      onStateChange('recording');

      return {
        stop: () => {
          if (recorder.state === 'recording') {
            recorder.stop();
          }
        },
        cancel: () => {
          isCancelled = true;
          if (recorder.state === 'recording') {
            recorder.stop();
          } else {
            stream.getTracks().forEach((track) => track.stop());
            onStateChange('idle');
          }
        },
      };
    } catch (err: any) {
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

