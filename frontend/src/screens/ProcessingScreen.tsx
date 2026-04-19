import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { QRCodeSVG } from 'qrcode.react';
import { ProgressRing } from '../components/ProgressRing';
import { ShowcaseGallery } from '../components/ShowcaseGallery';
import { PROCESSING_TIPS, getMockAvatarImageUrl } from '../mockData';
import { useApi, API_BASE } from '../hooks/useApi';
import type { AnalysisResult } from '../hooks/useApi';
import type { AvatarStyle, LocationTheme } from '../types';

interface ProcessingScreenProps {
  style: AvatarStyle;
  theme: LocationTheme;
  onComplete: (avatarImageUrl: string, videoUrl: string | null, videoId: string, shareUrl: string) => void;
  onError: () => void;
  onDemo: () => void;
  onNextPerson: () => void;
  recordedVideoUrl: string;
  recordedBlob: Blob | null;
}

type Phase = 'analyzing' | 'creating' | 'generating';

const TOTAL_POLL_ESTIMATE = 18;
const POLL_INTERVAL_MS = 5000;

export function ProcessingScreen({
  style,
  theme,
  onComplete,
  onError,
  onDemo,
  onNextPerson,
  recordedVideoUrl,
  recordedBlob,
}: ProcessingScreenProps) {
  const [phase, setPhase] = useState<Phase>('analyzing');
  const [analysisLines, setAnalysisLines] = useState<string[]>([]);
  const [avatarImageUrl, setAvatarImageUrl] = useState<string | null>(null);
  const [showAvatar, setShowAvatar] = useState(false);
  const [videoProgress, setVideoProgress] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);
  const [fatalError, setFatalError] = useState(false);
  const [fatalErrorMessage, setFatalErrorMessage] = useState<string | null>(null);
  const [allApiFailed, setAllApiFailed] = useState(false);
  const [currentShareUrl, setCurrentShareUrl] = useState<string | null>(null);
  const { uploadVideo, analyzeVideo, generateAvatar, generateVideo, pollStatus } = useApi();

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      let analysis: AnalysisResult | null = null;
      let videoId: string | null = null;
      let shareUrl: string | null = null;
      let apiSucceeded = false;

      // Phase 1: Analyzing
      setPhase('analyzing');

      if (recordedBlob) {
        try {
          const uploadResult = await uploadVideo(recordedBlob);
          if (cancelled) return;
          videoId = uploadResult.video_id;
          shareUrl = uploadResult.share_url;
          setCurrentShareUrl(uploadResult.share_url);

          analysis = await analyzeVideo(videoId, (phaseText) => {
            if (!cancelled) {
              setAnalysisLines((prev) => [...prev, phaseText]);
            }
          });
          apiSucceeded = true;
        } catch (err) {
          // Upload or analysis failed — surface the error
          if (!cancelled) {
            setFatalErrorMessage(err instanceof Error ? err.message : null);
            setFatalError(true);
          }
          return;
        }
      } else {
        const { ANALYSIS_LINES, mockDelay } = await import('../mockData');
        for (let i = 0; i <= ANALYSIS_LINES.length; i++) {
          if (cancelled) return;
          setAnalysisLines(ANALYSIS_LINES.slice(0, i));
          await mockDelay(800);
        }
        await mockDelay(1000);
      }

      if (cancelled) return;

      // Phase 2: Creating avatar
      setPhase('creating');
      let imgUrl = getMockAvatarImageUrl(style.color);

      if (videoId) {
        try {
          const { avatar_image_url } = await generateAvatar({
            video_id: videoId,
            avatar_style: style.id,
          });
          imgUrl = avatar_image_url;
          apiSucceeded = true;
        } catch {
          // Keep mock image on error
        }
      }

      if (cancelled) return;
      setAvatarImageUrl(imgUrl);
      setShowAvatar(true);
      await new Promise((r) => setTimeout(r, 1500));

      // Phase 3: Generating video
      if (cancelled) return;
      setPhase('generating');

      const resolvedVideoId = videoId ?? 'unknown';
      const resolvedShareUrl = shareUrl ?? `${API_BASE}/share/${resolvedVideoId}`;

      const tipInterval = setInterval(() => {
        if (!cancelled) {
          setTipIndex((i) => (i + 1) % PROCESSING_TIPS.length);
        }
      }, 3000);

      const MAX_POLL_RETRIES = 3;
      let resultUrl: string | null = null;

      try {
        const { operation_id } = await generateVideo({
          video_id: resolvedVideoId,
          avatar_image_url: imgUrl,
          motion_analysis: (analysis ?? {}) as Record<string, unknown>,
          avatar_style: style.id,
          location_theme: theme.id,
        });
        apiSucceeded = true;

        // Poll with retries — same operation_id, never re-generate
        let pollRetry = 0;
        while (pollRetry < MAX_POLL_RETRIES && !cancelled) {
          pollRetry++;
          if (pollRetry > 1) {
            setVideoProgress(0);
            // Wait a bit before retrying poll
            await new Promise((r) => setTimeout(r, 3000));
          }

          let attempts = 0;
          let pollFailed = false;
          while (!cancelled) {
            await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
            if (cancelled) break;

            const statusRes = await pollStatus(operation_id);
            attempts++;
            setVideoProgress(Math.min(attempts / TOTAL_POLL_ESTIMATE, 0.95));

            if (statusRes.status === 'complete') {
              if (statusRes.result_url) resultUrl = statusRes.result_url;
              pollFailed = false;
              break;
            }
            if (statusRes.status === 'failed') {
              pollFailed = true;
              break;
            }
          }

          if (!pollFailed) break; // Success — exit retry loop
          // pollFailed && more retries → loop back and re-poll
        }

        if (!cancelled) {
          setVideoProgress(1);
          await new Promise((r) => setTimeout(r, 500));
        }
      } catch (err) {
        // generateVideo() itself failed
        clearInterval(tipInterval);
        if (!cancelled) {
          setFatalErrorMessage(err instanceof Error ? err.message : null);
          setAllApiFailed(!apiSucceeded);
          setFatalError(true);
        }
        return;
      }

      clearInterval(tipInterval);

      if (!cancelled) {
        onComplete(imgUrl, resultUrl, resolvedVideoId, resolvedShareUrl);
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [style, recordedVideoUrl, recordedBlob, onComplete]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fatal error screen
  if (fatalError) {
    return (
      <div className="flex flex-col items-center justify-center h-full w-full px-8 text-center gap-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center gap-6"
        >
          <div
            className="w-24 h-24 rounded-full flex items-center justify-center text-5xl"
            style={{ background: 'rgba(234,67,53,0.15)', border: '2px solid rgba(234,67,53,0.4)' }}
          >
            ✦
          </div>
          <h2 className="text-5xl font-extrabold text-white">Something went wrong</h2>
          <p className="text-white/60 text-xl max-w-sm">
            We couldn't connect to the AI services right now.
          </p>
          {fatalErrorMessage && (
            <p className="text-red-400/80 text-xs font-mono max-w-sm break-all text-center px-2 py-2 rounded-lg bg-red-900/20">
              {fatalErrorMessage}
            </p>
          )}
          <div className="flex flex-col gap-3 w-full max-w-xs mt-2">
            <button
              onClick={onError}
              className="w-full py-5 rounded-full text-white text-xl font-bold"
              style={{
                minHeight: '72px',
                touchAction: 'manipulation',
                background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
              }}
            >
              Try Again
            </button>
            {allApiFailed && (
              <button
                onClick={onDemo}
                className="w-full py-5 rounded-full text-white text-xl font-semibold"
                style={{
                  minHeight: '72px',
                  touchAction: 'manipulation',
                  background: 'rgba(255,255,255,0.1)',
                  border: '2px solid rgba(255,255,255,0.2)',
                }}
              >
                Watch a Demo
              </button>
            )}
          </div>
        </motion.div>
      </div>
    );
  }


  // All phases use the same split-screen layout:
  // Left 60%: ShowcaseGallery (always visible)
  // Right 40%: Phase-specific content + QR + Next Person
  return (
    <div className="flex h-full w-full">
      {/* Left: Showcase Gallery (60%) */}
      <motion.div
        initial={{ opacity: 0, x: -40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6 }}
        className="h-full"
        style={{ width: '60%' }}
      >
        <ShowcaseGallery />
      </motion.div>

      {/* Right: Status Panel (40%) */}
      <motion.div
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6 }}
        className="flex flex-col items-center justify-center gap-5 px-8 overflow-hidden"
        style={{ width: '40%' }}
      >
        {/* ---- Phase-specific content ---- */}
        <AnimatePresence mode="wait">

          {phase === 'analyzing' && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="w-full"
            >
              <h2 className="text-3xl font-bold text-white mb-5 text-center">
                Analyzing your movement
              </h2>
              <div className="space-y-2 font-mono">
                {analysisLines.map((line, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4 }}
                    className="flex items-center gap-3 text-base"
                  >
                    <span className="text-google-green">▶</span>
                    <span className={i === analysisLines.length - 1 ? 'text-white' : 'text-white/60'}>
                      {line}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {phase === 'creating' && (
            <motion.div
              key="creating"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex flex-col items-center gap-6"
            >
              <h2 className="text-3xl font-bold text-white text-center">
                Creating your avatar
              </h2>
              <div className="relative w-52 h-52 rounded-2xl overflow-hidden">
                {!showAvatar ? (
                  <motion.div
                    className="absolute inset-0 rounded-2xl overflow-hidden"
                    style={{ background: `${style.color}20` }}
                  >
                    <motion.div
                      animate={{ x: ['-100%', '200%'] }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                      className="absolute inset-0"
                      style={{
                        background: `linear-gradient(90deg, transparent 0%, ${style.color}60 50%, transparent 100%)`,
                        width: '50%',
                      }}
                    />
                  </motion.div>
                ) : (
                  <AnimatePresence>
                    {avatarImageUrl && (
                      <>
                        <motion.div
                          className="absolute inset-0 rounded-2xl z-10"
                          initial={{ opacity: 0.8 }}
                          animate={{ opacity: 0 }}
                          transition={{ duration: 0.4, delay: 0.1 }}
                          style={{ background: 'white', pointerEvents: 'none' }}
                        />
                        <motion.img
                          src={avatarImageUrl}
                          alt="Your avatar"
                          className="w-full h-full object-contain rounded-2xl"
                          initial={{ scale: 0.5, opacity: 0, filter: 'blur(20px)' }}
                          animate={{ scale: 1, opacity: 1, filter: 'blur(0px)' }}
                          transition={{
                            scale: { type: 'spring', stiffness: 180, damping: 18, duration: 1.5 },
                            opacity: { duration: 1.0, ease: 'easeOut' },
                            filter: { duration: 1.0, ease: 'easeOut' },
                          }}
                        />
                      </>
                    )}
                  </AnimatePresence>
                )}
              </div>
            </motion.div>
          )}

          {phase === 'generating' && (
            <motion.div
              key="generating"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex flex-col items-center gap-5"
            >
              <h2 className="text-2xl font-bold text-white text-center">
                Placing you in {theme.name} {theme.emoji}
              </h2>

              {avatarImageUrl && (
                <motion.div
                  animate={{
                    boxShadow: [
                      `0 0 20px ${style.color}40`,
                      `0 0 60px ${style.color}80`,
                      `0 0 20px ${style.color}40`,
                    ],
                  }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  className="w-32 h-40 rounded-2xl overflow-hidden"
                >
                  <img src={avatarImageUrl} alt="Your avatar" className="w-full h-full object-contain" />
                </motion.div>
              )}

              <ProgressRing progress={videoProgress} size={90} strokeWidth={7} brandCycle>
                <span className="text-white font-bold text-base">
                  {Math.round(videoProgress * 100)}%
                </span>
              </ProgressRing>

              <AnimatePresence mode="wait">
                <motion.p
                  key={tipIndex}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.4 }}
                  className="text-white/50 text-center text-sm max-w-xs"
                >
                  {PROCESSING_TIPS[tipIndex]}
                </motion.p>
              </AnimatePresence>
            </motion.div>
          )}

        </AnimatePresence>

        {/* ---- QR Code + Next Person (shown as soon as video upload completes) ---- */}
        {currentShareUrl && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col items-center gap-3 w-full"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white rounded-xl">
                <QRCodeSVG
                  value={currentShareUrl}
                  size={90}
                  bgColor="#ffffff"
                  fgColor="#0A0A1A"
                  level="M"
                />
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-white/70 text-sm font-semibold">
                  Scan with your phone
                </p>
                <p className="text-white/40 text-xs max-w-[150px]">
                  Your video appears automatically when ready 📱
                </p>
              </div>
            </div>

            <motion.button
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              onClick={onNextPerson}
              className="w-full py-3 rounded-full text-white text-lg font-bold"
              style={{
                minHeight: '52px',
                touchAction: 'manipulation',
                background: 'linear-gradient(135deg, #34A853, #1e8e3e)',
              }}
            >
              ✋ Next Person
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
