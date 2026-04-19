import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useCamera } from '../hooks/useCamera';
import { CountdownTimer } from '../components/CountdownTimer';
import { ProgressRing } from '../components/ProgressRing';

interface RecordScreenProps {
  onComplete: (blob: Blob, url: string) => void;
  onBack: () => void;
}

type RecordState = 'preview' | 'countdown' | 'recording' | 'playback' | 'interrupted';

const RECORD_DURATION = 3000;
const COUNTDOWN_START = 3;

export function RecordScreen({ onComplete, onBack }: RecordScreenProps) {
  const { videoRef, isReady, error, streamDropped, startCamera, stopCamera, startRecording, stopRecording } =
    useCamera();
  const playbackRef = useRef<HTMLVideoElement>(null);
  const [recordState, setRecordState] = useState<RecordState>('preview');
  const [countdown, setCountdown] = useState(COUNTDOWN_START);
  const [recordProgress, setRecordProgress] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, [startCamera, stopCamera]);

  // Handle stream drop during recording
  useEffect(() => {
    if (streamDropped && (recordState === 'recording' || recordState === 'countdown')) {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      setRecordState('interrupted');
    }
  }, [streamDropped, recordState]);

  const handleRecord = useCallback(() => {
    if (recordState !== 'preview') return;
    setRecordState('countdown');
    setCountdown(COUNTDOWN_START);

    let c = COUNTDOWN_START;
    const interval = setInterval(() => {
      c--;
      if (c <= 0) {
        clearInterval(interval);
        setRecordState('recording');
        startRecording();

        const start = Date.now();
        progressIntervalRef.current = setInterval(() => {
          const elapsed = Date.now() - start;
          const progress = Math.min(elapsed / RECORD_DURATION, 1);
          setRecordProgress(progress);
          if (progress >= 1) {
            clearInterval(progressIntervalRef.current!);
          }
        }, 50);

        setTimeout(async () => {
          const blob = await stopRecording();
          if (blob) {
            const url = URL.createObjectURL(blob);
            setRecordedBlob(blob);
            setRecordedUrl(url);
            setRecordState('playback');
            setTimeout(() => {
              if (playbackRef.current) {
                playbackRef.current.src = url;
                playbackRef.current.play();
              }
            }, 100);
          }
        }, RECORD_DURATION);
      } else {
        setCountdown(c);
      }
    }, 1000);
  }, [recordState, startRecording, stopRecording]);

  const handleRetake = useCallback(() => {
    setRecordState('preview');
    setRecordProgress(0);
    setRecordedBlob(null);
    if (recordedUrl) {
      URL.revokeObjectURL(recordedUrl);
      setRecordedUrl(null);
    }
  }, [recordedUrl]);

  const handleRetakeAfterInterrupt = useCallback(() => {
    setRecordState('preview');
    setRecordProgress(0);
    startCamera();
  }, [startCamera]);

  const handleNext = useCallback(() => {
    if (recordedBlob && recordedUrl) {
      stopCamera();
      onComplete(recordedBlob, recordedUrl);
    }
  }, [recordedBlob, recordedUrl, stopCamera, onComplete]);

  // Camera permission error — full-screen friendly UI
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full w-full gap-8 px-8 text-center"
        style={{ background: '#0A0A1A' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-6"
        >
          <div className="w-28 h-28 rounded-full flex items-center justify-center text-6xl"
            style={{ background: 'rgba(234,67,53,0.15)', border: '2px solid rgba(234,67,53,0.4)' }}>
            📷
          </div>
          <h2 className="text-5xl font-extrabold text-white">Camera access needed</h2>
          <p className="text-white/60 text-xl max-w-sm">
            Please allow camera access to record your move. Check your browser settings and try again.
          </p>
          <div className="flex gap-4 mt-4">
            <button
              onClick={onBack}
              className="px-10 py-5 rounded-full text-white text-xl font-semibold"
              style={{
                minHeight: '72px',
                touchAction: 'manipulation',
                background: 'rgba(255,255,255,0.1)',
                border: '2px solid rgba(255,255,255,0.2)',
              }}
            >
              Go Back
            </button>
            <button
              onClick={() => startCamera()}
              className="px-10 py-5 rounded-full text-white text-xl font-bold"
              style={{
                minHeight: '72px',
                touchAction: 'manipulation',
                background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
              }}
            >
              Retry
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-black overflow-hidden">
      {/* Camera preview */}
      <AnimatePresence>
        {recordState !== 'playback' && recordState !== 'interrupted' && (
          <motion.video
            key="camera"
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
            style={{ transform: 'scaleX(-1)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
        )}
      </AnimatePresence>

      {/* Playback video */}
      <AnimatePresence>
        {recordState === 'playback' && (
          <motion.video
            key="playback"
            ref={playbackRef}
            autoPlay
            loop
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
        )}
      </AnimatePresence>

      {/* Recording interrupted overlay */}
      <AnimatePresence>
        {recordState === 'interrupted' && (
          <motion.div
            key="interrupted"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex flex-col items-center justify-center gap-6 px-8 text-center"
            style={{ background: 'rgba(10,10,26,0.92)' }}
          >
            <div className="text-5xl">⚠️</div>
            <h2 className="text-4xl font-bold text-white">Recording interrupted</h2>
            <p className="text-white/60 text-xl">The camera stream was lost. Please retake your video.</p>
            <button
              onClick={handleRetakeAfterInterrupt}
              className="px-12 py-5 rounded-full text-white text-xl font-bold mt-4"
              style={{
                minHeight: '72px',
                touchAction: 'manipulation',
                background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
              }}
            >
              Retake
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Dark overlay gradient at bottom */}
      {recordState !== 'interrupted' && (
        <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
      )}

      {/* Countdown overlay */}
      {recordState === 'countdown' && <CountdownTimer count={countdown} />}

      {/* Recording indicator */}
      {recordState === 'recording' && (
        <div className="absolute top-6 left-6 flex items-center gap-2 bg-black/50 rounded-full px-4 py-2">
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="w-3 h-3 rounded-full bg-google-red"
          />
          <span className="text-white font-semibold text-sm">REC</span>
        </div>
      )}

      {/* Playback label */}
      {recordState === 'playback' && (
        <div className="absolute top-6 left-0 right-0 flex justify-center">
          <div className="bg-black/60 rounded-full px-6 py-2">
            <span className="text-white/80 font-medium text-lg">Preview</span>
          </div>
        </div>
      )}

      {/* Bottom controls */}
      {recordState !== 'interrupted' && (
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-center pb-12 gap-8">
          {recordState === 'preview' && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center gap-4"
            >
              <p className="text-white/60 text-lg">Tap to record your 3-second move</p>
              <button
                onClick={handleRecord}
                disabled={!isReady}
                className="w-24 h-24 rounded-full border-4 border-white flex items-center justify-center"
                style={{ touchAction: 'manipulation', background: 'rgba(255,255,255,0.15)' }}
              >
                <div className="w-16 h-16 rounded-full bg-google-red" />
              </button>
            </motion.div>
          )}

          {recordState === 'countdown' && (
            <div
              className="w-24 h-24 rounded-full border-4 border-white/40 flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            >
              <div className="w-16 h-16 rounded-full bg-google-red/40" />
            </div>
          )}

          {recordState === 'recording' && (
            <ProgressRing progress={recordProgress} size={100} strokeWidth={5} color="#EA4335">
              <div className="w-12 h-12 rounded-lg bg-google-red" />
            </ProgressRing>
          )}

          {recordState === 'playback' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-6"
            >
              <button
                onClick={handleRetake}
                className="px-10 py-5 rounded-full text-white text-xl font-semibold"
                style={{
                  minHeight: '80px',
                  touchAction: 'manipulation',
                  background: 'rgba(255,255,255,0.15)',
                  border: '2px solid rgba(255,255,255,0.3)',
                }}
              >
                Retake
              </button>
              <button
                onClick={handleNext}
                className="px-10 py-5 rounded-full text-white text-xl font-bold"
                style={{
                  minHeight: '80px',
                  touchAction: 'manipulation',
                  background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
                }}
              >
                Next →
              </button>
            </motion.div>
          )}
        </div>
      )}

      {/* Back button */}
      {recordState === 'preview' && (
        <button
          onClick={onBack}
          className="absolute top-6 right-6 p-4 rounded-full bg-black/40"
          style={{ touchAction: 'manipulation' }}
        >
          <span className="text-white/70 text-xl">✕</span>
        </button>
      )}
    </div>
  );
}
