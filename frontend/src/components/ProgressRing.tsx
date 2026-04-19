import { useEffect, useRef } from 'react';

const BRAND_COLORS = ['#4285F4', '#EA4335', '#FBBC05', '#34A853'];

interface ProgressRingProps {
  progress: number; // 0 to 1
  size?: number;
  strokeWidth?: number;
  color?: string;
  brandCycle?: boolean; // when true, cycles through Google brand colors
  children?: React.ReactNode;
}

export function ProgressRing({
  progress,
  size = 120,
  strokeWidth = 6,
  color = '#4285F4',
  brandCycle = false,
  children,
}: ProgressRingProps) {
  const circleRef = useRef<SVGCircleElement>(null);
  const colorIndexRef = useRef(0);
  const animFrameRef = useRef<number | null>(null);
  const lastColorTimeRef = useRef(Date.now());

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - progress * circumference;

  useEffect(() => {
    if (!brandCycle || !circleRef.current) return;

    const animate = () => {
      const now = Date.now();
      if (now - lastColorTimeRef.current > 600) {
        colorIndexRef.current =
          (colorIndexRef.current + 1) % BRAND_COLORS.length;
        lastColorTimeRef.current = now;
        if (circleRef.current) {
          circleRef.current.style.stroke =
            BRAND_COLORS[colorIndexRef.current];
        }
      }
      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animFrameRef.current !== null) cancelAnimationFrame(animFrameRef.current);
    };
  }, [brandCycle]);

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.15)"
          strokeWidth={strokeWidth}
        />
        <circle
          ref={circleRef}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={brandCycle ? BRAND_COLORS[0] : color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.1s linear, stroke 0.3s ease' }}
        />
      </svg>
      {children}
    </div>
  );
}
