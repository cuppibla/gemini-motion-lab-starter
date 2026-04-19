import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface ResultScreenProps {
  recordedVideoUrl: string;
  avatarImageUrl: string;
  generatedVideoUrl: string | null;
  onShare: () => void;
  onTryAgain: () => void;
  onTimeout: () => void;
}

const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export function ResultScreen({
  recordedVideoUrl,
  avatarImageUrl,
  generatedVideoUrl,
  onShare,
  onTryAgain,
  onTimeout,
}: ResultScreenProps) {
  const originalRef = useRef<HTMLVideoElement>(null);
  const avatarRef = useRef<HTMLVideoElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(onTimeout, IDLE_TIMEOUT);
  };

  useEffect(() => {
    if (originalRef.current) originalRef.current.play();
    if (avatarRef.current) avatarRef.current.play();
    resetTimer();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="flex flex-col h-full w-full px-8 py-10"
      onPointerDown={resetTimer}
    >
      <motion.h1
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-4xl font-extrabold text-white text-center mb-8"
      >
        Your Avatar is Ready! ✨
      </motion.h1>

      {/* Side-by-side videos */}
      <div className="flex gap-4 flex-1 max-h-[55vh]">
        {/* Original video */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="flex-1 flex flex-col gap-2"
        >
          <div className="text-center text-white text-lg font-semibold">You</div>
          <div className="flex-1 rounded-2xl overflow-hidden bg-black border border-white/10">
            <video
              ref={originalRef}
              src={recordedVideoUrl}
              loop
              playsInline
              muted
              className="w-full h-full object-cover"
            />
          </div>
        </motion.div>

        {/* Avatar video — shimmer/glow border */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="flex-1 flex flex-col gap-2"
        >
          <div className="text-center font-semibold text-lg" style={{ color: '#4285F4' }}>
            Your Avatar
          </div>
          <div className="flex-1 relative rounded-2xl overflow-visible">
            {/* Animated shimmer border */}
            <motion.div
              className="absolute inset-0 rounded-2xl pointer-events-none"
              style={{ zIndex: 1 }}
              animate={{
                boxShadow: [
                  '0 0 12px 2px #4285F460, 0 0 32px 4px #4285F430',
                  '0 0 20px 4px #EA433560, 0 0 48px 8px #EA433530',
                  '0 0 16px 3px #FBBC0560, 0 0 40px 6px #FBBC0530',
                  '0 0 20px 4px #34A85360, 0 0 48px 8px #34A85330',
                  '0 0 12px 2px #4285F460, 0 0 32px 4px #4285F430',
                ],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            />
            <div
              className="w-full h-full rounded-2xl overflow-hidden border-2 flex items-center justify-center"
              style={{ borderColor: '#4285F4', background: 'black' }}
            >
              {generatedVideoUrl ? (
                <video
                  ref={avatarRef}
                  src={generatedVideoUrl}
                  loop
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center gap-4 p-6">
                  <img
                    src={avatarImageUrl}
                    alt="Generated avatar"
                    className="w-32 h-32 rounded-xl object-cover"
                  />
                  <p className="text-white/60 text-center text-sm">
                    Video generation failed — tap Try Again
                  </p>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Avatar image */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="flex justify-center mt-4"
      >
        <img
          src={avatarImageUrl}
          alt="Generated avatar"
          className="w-24 h-24 rounded-xl object-cover border-2 border-white/20"
        />
      </motion.div>

      {/* Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="flex gap-4 mt-4"
      >
        <button
          onClick={onTryAgain}
          className="flex-1 py-5 rounded-full text-white text-xl font-semibold"
          style={{
            minHeight: '80px',
            touchAction: 'manipulation',
            background: 'rgba(255,255,255,0.1)',
            border: '2px solid rgba(255,255,255,0.2)',
          }}
        >
          Try Again
        </button>
        <button
          onClick={onShare}
          className="flex-1 py-5 rounded-full text-white text-xl font-bold"
          style={{
            minHeight: '80px',
            touchAction: 'manipulation',
            background: 'linear-gradient(135deg, #34A853, #0f9d58)',
          }}
        >
          Share ↗
        </button>
      </motion.div>
    </div>
  );
}
