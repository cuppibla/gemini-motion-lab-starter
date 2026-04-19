import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { AvatarStyleCard } from '../components/AvatarStyleCard';
import { LOCATION_THEMES } from '../mockData';
import type { LocationTheme } from '../types';

interface LocationThemeScreenProps {
  onSelect: (theme: LocationTheme) => void;
  onBack: () => void;
  onTimeout: () => void;
}

const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

export function LocationThemeScreen({ onSelect, onBack, onTimeout }: LocationThemeScreenProps) {
  const [selected, setSelected] = useState<LocationTheme | null>(null);
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
        <h1 className="text-3xl font-extrabold text-white">Choose your world</h1>
        <p className="text-white/50 text-sm mt-1">Your avatar will perform here</p>
      </motion.div>

      <div className="grid grid-cols-3 grid-rows-2 gap-3 flex-1 min-h-0">
        {LOCATION_THEMES.map((theme, i) => (
          <motion.div
            key={theme.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <AvatarStyleCard
              style={theme}
              isSelected={selected?.id === theme.id}
              onSelect={() => setSelected(theme)}
            />
          </motion.div>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
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
              ? `linear-gradient(135deg, ${selected.color}, ${selected.color}cc)`
              : 'rgba(255,255,255,0.1)',
            opacity: selected ? 1 : 0.5,
            cursor: selected ? 'pointer' : 'not-allowed',
          }}
        >
          {selected ? `Generate in ${selected.name}` : 'Select a World'}
        </button>
      </motion.div>
    </div>
  );
}
