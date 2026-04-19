import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { API_BASE } from '../hooks/useApi';

interface QueueFullScreenProps {
  onReady: () => void;
}

export function QueueFullScreen({ onReady }: QueueFullScreenProps) {
  const [activeJobs, setActiveJobs] = useState(0);
  const [maxJobs, setMaxJobs] = useState(3);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;

    const poll = async () => {
      while (!cancelledRef.current) {
        try {
          const res = await fetch(`${API_BASE}/api/queue/status`);
          if (res.ok) {
            const data = await res.json();
            setActiveJobs(data.active_jobs);
            setMaxJobs(data.max_jobs);
            if (data.available) {
              onReady();
              return;
            }
          }
        } catch {
          // Network error — keep polling
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
    };

    poll();
    return () => {
      cancelledRef.current = true;
    };
  }, [onReady]);

  return (
    <div className="flex flex-col items-center justify-center h-full w-full px-8 text-center gap-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="flex flex-col items-center gap-6"
      >
        {/* Pulsing capacity indicator */}
        <motion.div
          animate={{
            boxShadow: [
              '0 0 30px rgba(66,133,244,0.2)',
              '0 0 60px rgba(66,133,244,0.5)',
              '0 0 30px rgba(66,133,244,0.2)',
            ],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="w-32 h-32 rounded-full flex items-center justify-center"
          style={{
            background: 'rgba(66,133,244,0.1)',
            border: '3px solid rgba(66,133,244,0.4)',
          }}
        >
          <span className="text-5xl">⏳</span>
        </motion.div>

        <h2 className="text-5xl font-extrabold text-white">
          We're at capacity!
        </h2>

        <p className="text-white/60 text-xl max-w-md">
          All {maxJobs} video slots are currently in use. Your turn is coming up — hang tight!
        </p>

        {/* Capacity indicator */}
        <div className="flex items-center gap-3 mt-2">
          {Array.from({ length: maxJobs }).map((_, i) => (
            <motion.div
              key={i}
              animate={
                i < activeJobs
                  ? { opacity: [0.5, 1, 0.5] }
                  : { opacity: 0.15 }
              }
              transition={
                i < activeJobs
                  ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: i * 0.3 }
                  : {}
              }
              className="w-6 h-6 rounded-full"
              style={{
                background: i < activeJobs ? '#4285F4' : 'rgba(255,255,255,0.15)',
              }}
            />
          ))}
        </div>
        <p className="text-white/40 text-base">
          {activeJobs}/{maxJobs} videos processing
        </p>

        <motion.p
          animate={{ opacity: [0.3, 0.7, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="text-white/40 text-sm mt-4"
        >
          Checking for available slots...
        </motion.p>
      </motion.div>
    </div>
  );
}
