const RADIUS = 34;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Anel de progresso no estilo do app Fitness, com a nota no meio. */
export function ScoreRing({ score }: { score: number }) {
  const filled = (Math.max(0, Math.min(100, score)) / 100) * CIRCUMFERENCE;
  return (
    <svg className="score-ring" viewBox="0 0 84 84" width="84" height="84" role="img" aria-label={`Pronúncia: ${score}%`}>
      <circle cx="42" cy="42" r={RADIUS} fill="none" stroke="var(--fill)" strokeWidth="10" />
      <circle
        cx="42"
        cy="42"
        r={RADIUS}
        fill="none"
        stroke={score >= 60 ? "var(--green-text)" : "var(--orange-text)"}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
        transform="rotate(-90 42 42)"
      />
      <text x="42" y="47" textAnchor="middle" fontSize="18" fontWeight="700" fill="var(--label)">
        {score}%
      </text>
    </svg>
  );
}
