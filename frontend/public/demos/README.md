# Demo Videos

Place pre-recorded demo videos in this directory for offline/fallback playback.

## Required files

| Filename | Avatar Style |
|---|---|
| `pixel-hero.mp4` | Pixel Hero (retro 8-bit) |
| `cyber-nova.mp4` | Cyber Nova (sci-fi android) |
| `watercolor-dream.mp4` | Watercolor Dream (painterly) |

## When demos are shown

If all API calls fail during the Processing screen, a **"Watch a Demo"** button appears.
Tapping it launches `DemoScreen`, which plays these videos in a loop and lets the user
switch between styles.

## Format recommendations

- Duration: 5–10 seconds, loopable
- Resolution: 720p (1280×720) or 1080p
- Codec: H.264 MP4 for broadest browser compatibility
- File size: keep under 20 MB each for fast load
