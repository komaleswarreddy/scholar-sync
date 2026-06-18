'use client';

type MasteryRingProps = {
  percent: number;
  strokeColor: string;
  size?: number;
  showCenterLabel?: boolean;
};

export function MasteryRing({
  percent,
  strokeColor,
  size = 40,
  showCenterLabel = false,
}: MasteryRingProps) {
  const r = (size - 6) / 2;
  const cx = size / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg className="-rotate-90" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="#E8EBE9"
          strokeWidth="4"
        />
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      {showCenterLabel && (
        <span
          className="absolute inset-0 flex items-center justify-center text-[10px] font-bold"
          style={{ color: strokeColor }}
        >
          {percent}%
        </span>
      )}
    </div>
  );
}
