import { motion, AnimatePresence } from 'framer-motion';

interface CountdownTimerProps {
  count: number;
}

export function CountdownTimer({ count }: CountdownTimerProps) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black/70 z-10">
      <AnimatePresence mode="wait">
        <motion.div
          key={count}
          initial={{ scale: 1.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.5, opacity: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="text-[200px] font-bold leading-none"
          style={{
            background: 'linear-gradient(135deg, #4285F4, #EA4335)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {count}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
