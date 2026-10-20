interface Ring {
  fraction: number; // 0–1
  color: string;
}

const SIZE = 120;
const STROKE = 14;
const GAP = 3;

/** Anéis concêntricos no estilo do app Fitness. O primeiro é o de fora. */
export function ActivityRings({ rings, label, size = SIZE }: { rings: Ring[]; label: string; size?: number }) {
  return (
    <svg className="activity-rings" viewBox={`0 0 ${SIZE} ${SIZE}`} width={size} height={size} role="img" aria-label={label}>
      {rings.map((ring, i) => {
        const radius = SIZE / 2 - STROKE / 2 - i * (STROKE + GAP);
        const circumference = 2 * Math.PI * radius;
        const filled = Math.max(0, Math.min(1, ring.fraction)) * circumference;
        return (
          <g key={i}>
            <circle cx={SIZE / 2} cy={SIZE / 2} r={radius} fill="none" stroke={ring.color} strokeOpacity="0.2" strokeWidth={STROKE} />
            {filled > 0 && (
              <circle
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={radius}
                fill="none"
                stroke={ring.color}
                strokeWidth={STROKE}
                strokeLinecap="round"
                strokeDasharray={`${filled} ${circumference}`}
                transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}
