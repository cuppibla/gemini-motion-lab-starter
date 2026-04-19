import { useRef, useState } from 'react';
import { motion } from 'framer-motion';

interface DemoScreenProps {
  onTryAgain: () => void;
}

const DEMOS = [
  { label: 'Pixel Hero', file: '/demos/pixel-hero.mp4' },
  { label: 'Cyber Nova', file: '/demos/cyber-nova.mp4' },
  { label: 'Watercolor Dream', file: '/demos/watercolor-dream.mp4' },
];

export function DemoScreen({ onTryAgain }: DemoScreenProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleSelect = (i: number) => {
    setActiveIndex(i);
    setTimeout(() => {
      if (videoRef.current) {
        videoRef.current.load();
        videoRef.current.play();
      }
    }, 50);
  };

  return (
    <div className="flex flex-col h-full w-full px-8 py-10">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <h1 className="text-5xl font-extrabold text-white text-center">Demo Mode</h1>
        <p className="text-white/60 text-xl text-center mt-2">
          See what Gemini Motion Lab can create
        </p>
      </motion.div>

      {/* Video player */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2 }}
        className="flex-1 rounded-3xl overflow-hidden bg-black border border-white/10 max-h-[50vh]"
      >
        <video
          ref={videoRef}
          key={DEMOS[activeIndex].file}
          src={DEMOS[activeIndex].file}
          autoPlay
          loop
          playsInline
          muted
          className="w-full h-full object-contain"
        />
      </motion.div>

      {/* Demo selector */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="flex gap-3 mt-5 justify-center"
      >
        {DEMOS.map((demo, i) => (
          <button
            key={demo.file}
            onClick={() => handleSelect(i)}
            className="flex-1 py-4 rounded-2xl text-base font-semibold transition-colors"
            style={{
              touchAction: 'manipulation',
              background: activeIndex === i ? 'rgba(66,133,244,0.3)' : 'rgba(255,255,255,0.06)',
              border: `2px solid ${activeIndex === i ? '#4285F4' : 'rgba(255,255,255,0.1)'}`,
              color: activeIndex === i ? '#fff' : 'rgba(255,255,255,0.6)',
            }}
          >
            {demo.label}
          </button>
        ))}
      </motion.div>

      {/* Try Again */}
      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        onClick={onTryAgain}
        className="mt-5 w-full py-6 rounded-full text-white text-xl font-bold"
        style={{
          minHeight: '80px',
          touchAction: 'manipulation',
          background: 'linear-gradient(135deg, #4285F4, #1a73e8)',
        }}
      >
        Try Again
      </motion.button>
    </div>
  );
}
