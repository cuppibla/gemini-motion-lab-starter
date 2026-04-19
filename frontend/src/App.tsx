import { useReducer, useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, type Variants } from 'framer-motion';
import { WelcomeScreen } from './screens/WelcomeScreen';
import { RecordScreen } from './screens/RecordScreen';
import { AvatarStyleScreen } from './screens/AvatarStyleScreen';
import { LocationThemeScreen } from './screens/LocationThemeScreen';
import { ProcessingScreen } from './screens/ProcessingScreen';
import { ResultScreen } from './screens/ResultScreen';
import { ShareScreen } from './screens/ShareScreen';
import { DemoScreen } from './screens/DemoScreen';
import { QueueFullScreen } from './screens/QueueFullScreen';
import { API_BASE, getLastApiError } from './hooks/useApi';
import type { AppState, Screen, AvatarStyle, LocationTheme } from './types';

// ─── State ────────────────────────────────────────────────────────────────────

const initialState: AppState = {
  currentScreen: 'welcome',
  recordedBlob: null,
  recordedVideoUrl: null,
  selectedStyle: null,
  selectedTheme: null,
  avatarImageUrl: null,
  generatedVideoUrl: null,
  videoId: null,
  shareUrl: null,
};

type Action =
  | { type: 'GO_TO'; screen: Screen }
  | { type: 'SET_RECORDING'; blob: Blob; url: string }
  | { type: 'SET_STYLE'; style: AvatarStyle }
  | { type: 'SET_THEME'; theme: LocationTheme }
  | { type: 'SET_RESULTS'; avatarImageUrl: string; videoUrl: string | null; videoId: string; shareUrl: string }
  | { type: 'RESET' };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'GO_TO':
      return { ...state, currentScreen: action.screen };
    case 'SET_RECORDING':
      return { ...state, currentScreen: 'avatarStyle', recordedBlob: action.blob, recordedVideoUrl: action.url };
    case 'SET_STYLE':
      return { ...state, currentScreen: 'locationTheme', selectedStyle: action.style };
    case 'SET_THEME':
      return { ...state, currentScreen: 'processing', selectedTheme: action.theme };
    case 'SET_RESULTS':
      return { ...state, currentScreen: 'result', avatarImageUrl: action.avatarImageUrl, generatedVideoUrl: action.videoUrl, videoId: action.videoId, shareUrl: action.shareUrl };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

// ─── Transition variants ──────────────────────────────────────────────────────

type TransitionType = 'slideUp' | 'slideLeft' | 'fadeScale' | 'dramaticFade' | 'fadeOut';

const TRANSITION_VARIANTS: Record<TransitionType, Variants> = {
  slideUp: {
    initial: { opacity: 0, y: '30%' },
    animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' } },
    exit: { opacity: 0, y: '-15%', transition: { duration: 0.3, ease: 'easeIn' } },
  },
  slideLeft: {
    initial: { opacity: 0, x: '40%' },
    animate: { opacity: 1, x: 0, transition: { duration: 0.4, ease: 'easeOut' } },
    exit: { opacity: 0, x: '-25%', transition: { duration: 0.3, ease: 'easeIn' } },
  },
  fadeScale: {
    initial: { opacity: 0, scale: 0.94 },
    animate: { opacity: 1, scale: 1, transition: { duration: 0.45, ease: 'easeOut' } },
    exit: { opacity: 0, scale: 1.04, transition: { duration: 0.3, ease: 'easeIn' } },
  },
  dramaticFade: {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { duration: 0.9, delay: 0.4, ease: 'easeOut' } },
    exit: { opacity: 0, transition: { duration: 0.4 } },
  },
  fadeOut: {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { duration: 0.5, ease: 'easeOut' } },
    exit: { opacity: 0, transition: { duration: 0.35 } },
  },
};

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [bootState, setBootState] = useState<'booting' | 'ready'>('booting');
  const [transitionType, setTransitionType] = useState<TransitionType>('fadeOut');
  const [isNetworkError, setIsNetworkError] = useState(false);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [debugError, setDebugError] = useState<string | null>(null);

  const debugTapCountRef = useRef(0);
  const debugTapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hardResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const networkRetryRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // stable ref so callbacks can access latest handleReset without re-creating timers
  const handleResetRef = useRef<() => void>(() => {});

  // ── Boot sequence ────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const tryConnect = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (!cancelled && res.ok) {
          setBootState('ready');
          return;
        }
      } catch {
        /* network error — retry below */
      }
      if (!cancelled) setTimeout(tryConnect, 2000);
    };
    tryConnect();
    return () => { cancelled = true; };
  }, []);

  // ── Network error monitoring ─────────────────────────────────────────────────
  useEffect(() => {
    const handleOffline = () => {
      setIsNetworkError(true);
      if (networkRetryRef.current) clearInterval(networkRetryRef.current);
      networkRetryRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/health`);
          if (res.ok) {
            setIsNetworkError(false);
            if (networkRetryRef.current) clearInterval(networkRetryRef.current);
          }
        } catch { /* keep retrying */ }
      }, 3000);
    };

    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('offline', handleOffline);
      if (networkRetryRef.current) clearInterval(networkRetryRef.current);
    };
  }, []);

  // ── Context menu prevention ──────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: Event) => e.preventDefault();
    document.addEventListener('contextmenu', handler);
    return () => document.removeEventListener('contextmenu', handler);
  }, []);

  // ── Hard reset (3-minute idle) ───────────────────────────────────────────────
  const resetHardTimer = useCallback(() => {
    if (hardResetTimerRef.current) clearTimeout(hardResetTimerRef.current);
    hardResetTimerRef.current = setTimeout(() => handleResetRef.current(), 30 * 60 * 1000);
  }, []);

  useEffect(() => {
    const events = ['pointerdown', 'keydown', 'touchstart'];
    const handler = () => resetHardTimer();
    events.forEach((e) => window.addEventListener(e, handler, { passive: true }));
    resetHardTimer();
    return () => {
      events.forEach((e) => window.removeEventListener(e, handler));
      if (hardResetTimerRef.current) clearTimeout(hardResetTimerRef.current);
    };
  }, [resetHardTimer]);

  // ── Debug panel (5 taps) ─────────────────────────────────────────────────────
  const handleDebugTap = useCallback(() => {
    debugTapCountRef.current += 1;
    if (debugTapTimerRef.current) clearTimeout(debugTapTimerRef.current);
    debugTapTimerRef.current = setTimeout(() => {
      debugTapCountRef.current = 0;
    }, 2000);
    if (debugTapCountRef.current >= 5) {
      debugTapCountRef.current = 0;
      setDebugError(getLastApiError());
      setShowDebugPanel((v) => !v);
    }
  }, []);

  // ── Reset with blob cleanup ──────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    if (state.recordedVideoUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(state.recordedVideoUrl);
    }
    if (state.generatedVideoUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(state.generatedVideoUrl);
    }
    setTransitionType('fadeOut');
    dispatch({ type: 'RESET' });
  }, [state.recordedVideoUrl, state.generatedVideoUrl]);

  // Keep ref in sync
  handleResetRef.current = handleReset;

  // ── Navigation helpers ───────────────────────────────────────────────────────
  const handleStart = useCallback(() => {
    setTransitionType('slideUp');
    dispatch({ type: 'GO_TO', screen: 'record' });
  }, []);

  const handleRecordComplete = useCallback((blob: Blob, url: string) => {
    setTransitionType('slideLeft');
    dispatch({ type: 'SET_RECORDING', blob, url });
  }, []);

  const handleStyleSelect = useCallback((style: AvatarStyle) => {
    setTransitionType('slideLeft');
    dispatch({ type: 'SET_STYLE', style });
  }, []);

  const handleThemeSelect = useCallback((theme: LocationTheme) => {
    setTransitionType('fadeScale');
    dispatch({ type: 'SET_THEME', theme });
  }, []);

  const handleProcessingComplete = useCallback(
    (avatarImageUrl: string, videoUrl: string | null, videoId: string, shareUrl: string) => {
      setTransitionType('dramaticFade');
      dispatch({ type: 'SET_RESULTS', avatarImageUrl, videoUrl, videoId, shareUrl });
    },
    [],
  );

  const handleShare = useCallback(() => {
    setTransitionType('slideLeft');
    dispatch({ type: 'GO_TO', screen: 'share' });
  }, []);

  const handleGoToDemo = useCallback(() => {
    setTransitionType('fadeScale');
    dispatch({ type: 'GO_TO', screen: 'demo' });
  }, []);

  const handleNextPerson = useCallback(async () => {
    // Clean up blobs
    if (state.recordedVideoUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(state.recordedVideoUrl);
    }
    if (state.generatedVideoUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(state.generatedVideoUrl);
    }
    setTransitionType('fadeOut');
    // Always RESET first to clear stale state, then check queue
    dispatch({ type: 'RESET' });
    try {
      const res = await fetch(`${API_BASE}/api/queue/status`);
      if (res.ok) {
        const data = await res.json();
        if (!data.available) {
          dispatch({ type: 'GO_TO', screen: 'queueFull' });
          return;
        }
      }
    } catch {
      // Network error — stay on welcome
    }
  }, [state.recordedVideoUrl, state.generatedVideoUrl]);

  const variants = TRANSITION_VARIANTS[transitionType];

  // ── Boot screen ──────────────────────────────────────────────────────────────
  if (bootState === 'booting') {
    return (
      <div
        className="h-screen w-screen flex flex-col items-center justify-center gap-8"
        style={{ background: '#0A0A1A' }}
      >
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          className="flex flex-col items-center gap-6"
        >
          {/* Spinner */}
          <div
            className="w-16 h-16 rounded-full border-4 border-white/10"
            style={{
              borderTopColor: '#4285F4',
              animation: 'spin 1s linear infinite',
            }}
          />
          <p className="text-white/80 text-2xl font-semibold">
            Connecting to Gemini Motion Lab...
          </p>
        </motion.div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen overflow-hidden" style={{ background: '#0A0A1A' }}>
      {/* ── Main screen ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={state.currentScreen}
          variants={variants}
          initial="initial"
          animate="animate"
          exit="exit"
          className="h-full w-full"
        >
          {state.currentScreen === 'welcome' && (
            <WelcomeScreen onStart={handleStart} onDebugTap={handleDebugTap} />
          )}

          {state.currentScreen === 'record' && (
            <RecordScreen
              onComplete={handleRecordComplete}
              onBack={() => {
                setTransitionType('slideUp');
                dispatch({ type: 'GO_TO', screen: 'welcome' });
              }}
            />
          )}

          {state.currentScreen === 'avatarStyle' && (
            <AvatarStyleScreen
              onSelect={handleStyleSelect}
              onBack={() => {
                setTransitionType('slideLeft');
                dispatch({ type: 'GO_TO', screen: 'record' });
              }}
              onTimeout={handleReset}
            />
          )}

          {state.currentScreen === 'locationTheme' && (
            <LocationThemeScreen
              onSelect={handleThemeSelect}
              onBack={() => {
                setTransitionType('slideLeft');
                dispatch({ type: 'GO_TO', screen: 'avatarStyle' });
              }}
              onTimeout={handleReset}
            />
          )}

          {state.currentScreen === 'processing' && state.selectedStyle && state.selectedTheme && state.recordedVideoUrl && (
            <ProcessingScreen
              style={state.selectedStyle}
              theme={state.selectedTheme}
              recordedVideoUrl={state.recordedVideoUrl}
              recordedBlob={state.recordedBlob}
              onComplete={handleProcessingComplete}
              onError={handleReset}
              onDemo={handleGoToDemo}
              onNextPerson={handleNextPerson}
            />
          )}

          {state.currentScreen === 'result' && state.recordedVideoUrl && state.avatarImageUrl && (
            <ResultScreen
              recordedVideoUrl={state.recordedVideoUrl}
              avatarImageUrl={state.avatarImageUrl}
              generatedVideoUrl={state.generatedVideoUrl}
              onShare={handleShare}
              onTryAgain={handleReset}
              onTimeout={handleReset}
            />
          )}

          {state.currentScreen === 'share' && (
            <ShareScreen onDone={handleReset} videoId={state.videoId ?? ''} shareUrl={state.shareUrl ?? ''} />
          )}

          {state.currentScreen === 'demo' && (
            <DemoScreen onTryAgain={handleReset} />
          )}

          {state.currentScreen === 'queueFull' && (
            <QueueFullScreen onReady={() => {
              setTransitionType('fadeOut');
              dispatch({ type: 'RESET' });
            }} />
          )}
        </motion.div>
      </AnimatePresence>

      {/* ── Network error overlay ── */}
      <AnimatePresence>
        {isNetworkError && (
          <motion.div
            key="network-error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-6 z-50"
            style={{ background: 'rgba(10,10,26,0.92)', backdropFilter: 'blur(8px)' }}
          >
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex flex-col items-center gap-5"
            >
              <div
                className="w-14 h-14 rounded-full border-4 border-white/10"
                style={{ borderTopColor: '#4285F4', animation: 'spin 1s linear infinite' }}
              />
              <h2 className="text-3xl font-bold text-white">Connection lost</h2>
              <p className="text-white/60 text-xl">Reconnecting...</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Debug panel ── */}
      <AnimatePresence>
        {showDebugPanel && (
          <motion.div
            key="debug-panel"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            className="absolute bottom-0 left-0 right-0 z-50 p-6 rounded-t-3xl"
            style={{ background: 'rgba(20,20,40,0.97)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-white font-bold text-xl">Debug Panel</h3>
              <button
                onClick={() => setShowDebugPanel(false)}
                className="text-white/60 text-2xl px-3"
                style={{ touchAction: 'manipulation' }}
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 font-mono text-sm">
              <div className="text-white/50">Screen: <span className="text-google-blue">{state.currentScreen}</span></div>
              <div className="text-white/50">Boot: <span className="text-google-green">{bootState}</span></div>
              <div className="text-white/50">Network error: <span className={isNetworkError ? 'text-google-red' : 'text-google-green'}>{String(isNetworkError)}</span></div>
              <div className="text-white/50 mt-3">Last API error:</div>
              <div
                className="text-google-red text-xs p-3 rounded-xl break-all"
                style={{ background: 'rgba(234,67,53,0.1)', minHeight: '48px' }}
              >
                {debugError ?? '(none)'}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
