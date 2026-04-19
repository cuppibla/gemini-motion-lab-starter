import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { QRCodeSVG } from 'qrcode.react';
import { useApi } from '../hooks/useApi';

interface ShareScreenProps {
  onDone: () => void;
  videoId: string;
  shareUrl: string;
}

const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes
const COUNTDOWN_S = 90;

export function ShareScreen({ onDone, videoId, shareUrl }: ShareScreenProps) {
  const [timeLeft, setTimeLeft] = useState(COUNTDOWN_S);
  const [composedVideoUrl, setComposedVideoUrl] = useState<string | null>(null);
  const [isComposing, setIsComposing] = useState(true);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { getShare } = useApi();

  // shareUrl comes from the upload response (backend's PUBLIC_BASE_URL/share/{videoId}),
  // ensuring both the loading screen QR and this QR always encode the same correct link.

  const startCountdown = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);

    setTimeLeft(COUNTDOWN_S);
    timerRef.current = setTimeout(onDone, IDLE_TIMEOUT);
    countdownRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
  };

  const resetTimer = () => {
    startCountdown();
  };

  useEffect(() => {
    // Start countdown immediately — QR is visible from the start
    startCountdown();

    // Compose video in background (for kiosk preview only)
    if (videoId) {
      getShare(videoId)
        .then((data) => {
          setComposedVideoUrl(data.download_url);
        })
        .catch(() => {
          // Composition failed — QR still works, user can compose on mobile
        })
        .finally(() => {
          setIsComposing(false);
        });
    } else {
      setIsComposing(false);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="flex flex-col items-center h-full w-full px-8 overflow-y-auto py-10"
      onPointerDown={resetTimer}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="flex flex-col items-center gap-6"
      >
        <h1 className="text-5xl font-extrabold text-white text-center">
          Scan to get your video!
        </h1>

        {/* Composed video preview (shows when ready) */}
        <AnimatePresence>
          {composedVideoUrl && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-2xl overflow-hidden"
              style={{ width: 180, aspectRatio: '9/16' }}
            >
              <video
                src={composedVideoUrl}
                autoPlay
                loop
                muted
                playsInline
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* QR Code — shown immediately */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="p-6 bg-white rounded-3xl"
        >
          <QRCodeSVG
            value={shareUrl}
            size={280}
            bgColor="#ffffff"
            fgColor="#0A0A1A"
            level="M"
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="text-center"
        >
          <p className="text-white/70 text-2xl">
            Scan to download &amp; share
          </p>
          {isComposing && (
            <motion.p
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
              className="text-white/40 text-base mt-2"
            >
              Composing video...
            </motion.p>
          )}
        </motion.div>

        <button
          onClick={onDone}
          className="px-16 py-5 rounded-full text-white text-xl font-bold"
          style={{
            minHeight: '80px',
            touchAction: 'manipulation',
            background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
          }}
        >
          Start Over
        </button>

        <p className="text-white/30 text-base">
          Auto-returning to start in {timeLeft}s
        </p>
      </motion.div>
    </div>
  );
}
