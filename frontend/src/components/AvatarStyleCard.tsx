import { motion } from 'framer-motion';
import type { AvatarStyle } from '../types';

interface AvatarStyleCardProps {
  style: AvatarStyle;
  isSelected: boolean;
  onSelect: () => void;
}

export function AvatarStyleCard({ style, isSelected, onSelect }: AvatarStyleCardProps) {
  return (
    <motion.button
      onClick={onSelect}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className="relative overflow-hidden rounded-2xl border-2 cursor-pointer w-full h-full"
      style={{
        borderColor: isSelected ? style.color : 'rgba(255,255,255,0.08)',
        touchAction: 'manipulation',
      }}
    >
      {/* Animated glow on selection */}
      {isSelected && (
        <motion.div
          layoutId="selected-glow"
          className="absolute inset-0 rounded-2xl z-10 pointer-events-none"
          style={{
            boxShadow: `0 0 40px ${style.color}60, inset 0 0 20px ${style.color}20`,
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
      )}

      {/* Themed background for object-contain */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(ellipse at center bottom, ${style.color}25 0%, #0A0A1A 70%)`,
        }}
      />

      {/* Preview image — fit to contain (full body visible) */}
      <img
        src={style.previewImage}
        alt={style.name}
        className="absolute inset-0 w-full h-full object-contain p-2"
        loading="eager"
      />

      {/* Gradient overlay at bottom for text readability */}
      <div
        className="absolute inset-x-0 bottom-0 h-2/5 pointer-events-none"
        style={{
          background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 60%, transparent 100%)',
        }}
      />

      {/* Glassmorphism label */}
      <div className="absolute inset-x-0 bottom-0 p-3 flex items-center justify-center gap-2 z-20">
        <span className="text-2xl">{style.emoji}</span>
        <div className="font-bold text-white text-base leading-tight uppercase tracking-wide">{style.name}</div>
      </div>

      {/* Selected checkmark */}
      {isSelected && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center z-20"
          style={{ background: style.color }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8.5L6.5 12L13 4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>
      )}
    </motion.button>
  );
}
