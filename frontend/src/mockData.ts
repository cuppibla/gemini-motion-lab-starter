import type { AvatarStyle, LocationTheme } from './types';

export const AVATAR_STYLES: AvatarStyle[] = [
  {
    id: 'pixel-hero',
    name: 'Pixel Hero',
    description: 'Retro pixel data scientist',
    emoji: '🎮',
    color: '#EA4335',
    previewImage: '/previews/pixel-hero.png',
  },
  {
    id: 'cyber-nova',
    name: 'Cyber Nova',
    description: 'Chrome Google android',
    emoji: '🤖',
    color: '#4285F4',
    previewImage: '/previews/cyber-nova.png',
  },
  {
    id: 'watercolor-dream',
    name: 'Watercolor Dream',
    description: 'Abstract color-field silhouette',
    emoji: '🎨',
    color: '#34A853',
    previewImage: '/previews/watercolor-dream.png',
  },
  {
    id: '3d-figurine',
    name: '3D Figurine',
    description: 'Google panda collectible',
    emoji: '🧸',
    color: '#FBBC05',
    previewImage: '/previews/3d-figurine.png',
  },
  {
    id: 'manga-ink',
    name: 'Manga Ink',
    description: 'B&W manga thumbs-up',
    emoji: '✒️',
    color: '#9C27B0',
    previewImage: '/previews/manga-ink.png',
  },
  {
    id: 'brick-build',
    name: 'Brick Build',
    description: 'Brick-built Google G',
    emoji: '🧱',
    color: '#FF6D00',
    previewImage: '/previews/brick-build.png',
  },
];

export const LOCATION_THEMES: LocationTheme[] = [
  {
    id: 'lunar-surface',
    name: 'Lunar Surface',
    description: 'Moonscape with Earth rising',
    emoji: '🌙',
    color: '#B8C4E8',
    previewImage: '/previews/lunar-surface.png',
  },
  {
    id: 'golden-desert',
    name: 'Golden Desert',
    description: 'Ancient ruins in epic dunes',
    emoji: '🏜️',
    color: '#E8A94A',
    previewImage: '/previews/golden-desert.png',
  },
  {
    id: 'neon-city',
    name: 'Neon City',
    description: 'Cyberpunk metropolis at night',
    emoji: '🌃',
    color: '#E8487A',
    previewImage: '/previews/neon-city.png',
  },
  {
    id: 'space-station',
    name: 'Space Station',
    description: 'Orbital command center',
    emoji: '🚀',
    color: '#4285F4',
    previewImage: '/previews/space-station.png',
  },
  {
    id: 'enchanted-forest',
    name: 'Enchanted Forest',
    description: 'Bioluminescent mystical woods',
    emoji: '🌲',
    color: '#34A853',
    previewImage: '/previews/enchanted-forest.png',
  },
  {
    id: 'underwater-palace',
    name: 'Underwater Palace',
    description: 'Ancient temple beneath the sea',
    emoji: '🌊',
    color: '#00BCD4',
    previewImage: '/previews/underwater-palace.png',
  },
];

export const PROCESSING_TIPS = [
  'Powered by Veo 3.1 on Vertex AI',
  'Analyzing 150 frames of motion data',
  'Your personalized avatar is coming to life',
  'Using Gemini 3.1 Pro for motion understanding',
];

export const ANALYSIS_LINES = [
  'Detecting body movement...',
  'Arms: raised overhead, sweeping motion',
  'Legs: weight shifting left to right',
  'Tempo: medium | Energy: high',
  'Style: fluid, dance-like',
];

export const mockDelay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

// Returns a placeholder avatar image URL (colored data URL)
export function getMockAvatarImageUrl(styleColor: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
    <rect width="400" height="400" fill="${styleColor}" opacity="0.2" rx="20"/>
    <circle cx="200" cy="150" r="80" fill="${styleColor}" opacity="0.6"/>
    <rect x="120" y="250" width="160" height="120" rx="20" fill="${styleColor}" opacity="0.6"/>
    <text x="200" y="380" text-anchor="middle" font-size="24" fill="white" opacity="0.8">Avatar Preview</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export const SHARE_URL = 'https://cloud.google.com/next';
