import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { AvatarStyleCard } from '../components/AvatarStyleCard';
import { AVATAR_STYLES } from '../mockData';
import type { AvatarStyle } from '../types';

interface AvatarStyleScreenProps {
  onSelect: (style: AvatarStyle) => void;
  onBack: () => void;
  onTimeout: () => void;
}

const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export function AvatarStyleScreen({ onSelect, onBack, onTimeout }: AvatarStyleScreenProps) {
  const [selected, setSelected] = useState<AvatarStyle | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(onTimeout, IDLE_TIMEOUT);
  };

  useEffect(() => {
    resetTimer();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="flex flex-col h-full w-full px-8 py-4"
      onPointerDown={resetTimer}
    >
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-3 flex-shrink-0"
      >
        <button
          onClick={onBack}
          className="text-white/50 text-base mb-1"
          style={{ touchAction: 'manipulation' }}
        >
          ← Back
        </button>
        <h1 className="text-3xl font-extrabold text-white">Choose your style</h1>
      </motion.div>

      <div className="grid grid-cols-3 grid-rows-2 gap-3 flex-1 min-h-0">
        {AVATAR_STYLES.map((style, i) => (
          <motion.div
            key={style.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <AvatarStyleCard
              style={style}
              isSelected={selected?.id === style.id}
              onSelect={() => setSelected(style)}
            />
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-3 flex-shrink-0"
      >
        <button
          onClick={() => selected && onSelect(selected)}
          disabled={!selected}
          className="w-full py-4 rounded-full text-white text-xl font-bold transition-opacity"
          style={{
            minHeight: '56px',
            touchAction: 'manipulation',
            background: selected
              ? 'linear-gradient(135deg, #4285F4, #1a73e8)'
              : 'rgba(255,255,255,0.1)',
            opacity: selected ? 1 : 0.5,
            cursor: selected ? 'pointer' : 'not-allowed',
          }}
        >
          {selected ? `Generate ${selected.name}` : 'Select a Style'}
        </button>
      </motion.div>
    </div>
  );
}
