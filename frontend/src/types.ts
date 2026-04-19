export type Screen =
  | 'welcome'
  | 'record'
  | 'avatarStyle'
  | 'locationTheme'
  | 'processing'
  | 'result'
  | 'share'
  | 'demo'
  | 'queueFull';

export interface AvatarStyle {
  id: string;
  name: string;
  description: string;
  emoji: string;
  color: string;
  previewImage: string;
}

export interface LocationTheme {
  id: string;
  name: string;
  description: string;
  emoji: string;
  color: string;
  previewImage: string;
}

export interface AppState {
  currentScreen: Screen;
  recordedBlob: Blob | null;
  recordedVideoUrl: string | null;
  selectedStyle: AvatarStyle | null;
  selectedTheme: LocationTheme | null;
  avatarImageUrl: string | null;
  generatedVideoUrl: string | null;
  videoId: string | null;
  shareUrl: string | null;
}
