import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

interface WelcomeScreenProps {
  onStart: () => void;
  onDebugTap?: () => void;
}

const BRAND_COLORS = ['#4285F4', '#EA4335', '#FBBC05', '#34A853'];
const TITLE = 'Gemini Motion Lab';

export function WelcomeScreen({ onStart, onDebugTap }: WelcomeScreenProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [consented, setConsented] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 3 + 1,
      color: BRAND_COLORS[Math.floor(Math.random() * BRAND_COLORS.length)],
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      opacity: Math.random() * 0.6 + 0.2,
    }));

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      animId = requestAnimationFrame(animate);
    };
    animate();

    return () => cancelAnimationFrame(animId);
  }, []);

  return (
    <div className="relative flex flex-col items-center justify-center h-full w-full overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-radial from-transparent via-transparent to-kiosk-bg/80 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="relative z-10 flex flex-col items-center gap-6 text-center px-8"
      >
        {/* Logo/Title — tapping 5x activates debug panel */}
        <motion.div
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          onClick={onDebugTap}
          style={{ cursor: 'default' }}
        >
          <div className="flex items-center gap-3 mb-2 justify-center">
            <div className="w-3 h-3 rounded-full bg-google-blue" />
            <div className="w-3 h-3 rounded-full bg-google-red" />
            <div className="w-3 h-3 rounded-full bg-google-yellow" />
            <div className="w-3 h-3 rounded-full bg-google-green" />
          </div>
          <h1 className="text-7xl font-extrabold tracking-tight">
            {TITLE.split('').map((letter, i) => (
              <motion.span
                key={i}
                animate={{
                  color: [
                    BRAND_COLORS[i % 4],
                    BRAND_COLORS[(i + 1) % 4],
                    BRAND_COLORS[(i + 2) % 4],
                    BRAND_COLORS[(i + 3) % 4],
                    BRAND_COLORS[i % 4],
                  ],
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: 'linear',
                  delay: i * 0.15,
                }}
                style={{ display: letter === ' ' ? 'inline' : 'inline-block' }}
              >
                {letter}
              </motion.span>
            ))}
          </h1>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="text-2xl text-white/70 font-light max-w-lg"
        >
          Record your move. See yourself as AI.
        </motion.p>

        {/* Privacy consent checkbox */}
        <motion.label
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45, duration: 0.6 }}
          htmlFor="privacy-consent"
          className="flex items-start gap-4 mt-8 px-6 py-4 rounded-2xl cursor-pointer select-none"
          style={{
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.1)',
            maxWidth: '540px',
            minHeight: '56px',
            touchAction: 'manipulation',
          }}
        >
          {/* Custom checkbox */}
          <span
            className="flex-shrink-0 flex items-center justify-center rounded-md mt-0.5 transition-colors duration-200"
            style={{
              width: '28px',
              height: '28px',
              background: consented ? '#4285F4' : 'rgba(255,255,255,0.12)',
              border: `2px solid ${consented ? '#4285F4' : 'rgba(255,255,255,0.3)'}`,
            }}
          >
            {consented && (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3.5 8.5L6.5 11.5L12.5 4.5" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </span>
          <span className="text-white/70 text-base leading-relaxed">
            I understand this demo temporarily records my face, and that all video is automatically deleted within 24 hours.
          </span>
          {/* Hidden native checkbox for accessibility */}
          <input
            id="privacy-consent"
            type="checkbox"
            checked={consented}
            onChange={(e) => setConsented(e.target.checked)}
            className="sr-only"
            aria-label="Privacy consent"
          />
        </motion.label>

        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.6 }}
          whileTap={consented ? { scale: 0.97 } : undefined}
          onClick={consented ? onStart : undefined}
          className="mt-5 relative px-16 py-6 rounded-full text-2xl font-bold text-white overflow-hidden"
          style={{
            background: consented
              ? 'linear-gradient(135deg, #4285F4, #1a73e8)'
              : 'linear-gradient(135deg, #3a3a4a, #2a2a3a)',
            minHeight: '80px',
            touchAction: 'manipulation',
            boxShadow: consented ? '0 0 40px #4285F440' : 'none',
            opacity: consented ? 1 : 0.45,
            pointerEvents: consented ? 'auto' : 'none',
            transition: 'opacity 0.3s ease, background 0.3s ease, box-shadow 0.3s ease',
          }}
        >
          {consented && (
            <motion.div
              animate={{
                boxShadow: [
                  '0 0 20px #4285F440',
                  '0 0 60px #4285F470',
                  '0 0 20px #4285F440',
                ],
              }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute inset-0 rounded-full"
            />
          )}
          <span className="relative z-10">Tap to Start</span>
        </motion.button>
      </motion.div>
    </div>
  );
}
