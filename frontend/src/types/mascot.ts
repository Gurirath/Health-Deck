export type MascotPose =
  | 'idle'
  | 'welcome'
  | 'listening'
  | 'thinking'
  | 'guiding'
  | 'success'
  | 'urgent';

export interface MascotConfig {
  pose: MascotPose;
  message?: string;
  subMessage?: string;
  isInteractive?: boolean;
}
