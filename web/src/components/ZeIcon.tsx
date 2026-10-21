import { useId } from "react";

const DARK = "#16141f";
const EYES = [84, 116];

/**
 * Ícone do app: o "Zé" e o Zé (a arara) se revezam. O "Zé" encolhe, o Zé pula pra dentro,
 * pisca, olha em volta e desce (ciclo de 8 s). `calm`: três ciclos e para no "Zé", pra não
 * disputar a atenção com o conteúdo. Com "Reduzir movimento" no aparelho, fica só o "Zé".
 */
export function ZeIcon({ calm = false, className = "" }: { calm?: boolean; className?: string }) {
  // ids únicos por ícone: vários na mesma página não podem dividir gradiente e recorte
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const party = `ze-party-${id}`;
  const body = `ze-body-${id}`;
  const clip = `ze-clip-${id}`;

  return (
    <svg className={`ze-icon${calm ? " calm" : ""} ${className}`.trim()} viewBox="0 0 120 120" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={party} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#9b6bff" />
          <stop offset="0.6" stopColor="#6a3df0" />
          <stop offset="1" stopColor="#ff2d55" />
        </linearGradient>
        <linearGradient id={body} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7d55ff" />
          <stop offset="1" stopColor="#4b23c8" />
        </linearGradient>
        <clipPath id={clip}>
          <rect x="4" y="4" width="112" height="112" rx="27" />
        </clipPath>
      </defs>

      <rect x="4" y="4" width="112" height="112" rx="27" fill={`url(#${party})`} />
      <g className="face-ze">
        <text x="60" y="79" textAnchor="middle" fontSize="52" fill="#ffffff" className="ze-word">
          Zé
        </text>
      </g>

      <g clipPath={`url(#${clip})`}>
        <g className="face-m">
          {/* A cabeça é desenhada num quadro de 200 e encolhida pro centro do ícone */}
          <g transform="translate(-8.18 17) scale(0.682)">
            <g className="tuft">
              <ellipse cx="84" cy="34" rx="8" ry="20" fill="#ff2d55" transform="rotate(-26 84 34)" />
              <ellipse cx="100" cy="27" rx="8" ry="22" fill="#ff9f0a" />
              <ellipse cx="116" cy="34" rx="8" ry="20" fill="#ff2d55" transform="rotate(26 116 34)" />
            </g>
            <circle cx="100" cy="82" r="44" fill={`url(#${body})`} />
            {EYES.map((x) => (
              <g key={x}>
                <ellipse cx={x} cy="80" rx="16" ry="19" fill="#ffffff" />
                <g className="look">
                  <circle cx={x + 1.5} cy="81" r="8" fill={DARK} />
                  <circle cx={x + 4} cy="77.5" r="2.9" fill="#ffffff" />
                </g>
                <rect className="blink" x={x - 17.5} y="59.5" width="35" height="41" rx="17.5" fill="#5d34dc" />
              </g>
            ))}
            <circle cx="70" cy="102" r="6" fill="#ff2d55" opacity="0.45" />
            <circle cx="130" cy="102" r="6" fill="#ff2d55" opacity="0.45" />
            <path d="M100 94 C86 94 84 113 100 122 C116 113 114 94 100 94 Z" fill="#ffc83d" />
            <path d="M91 113 Q100 127 109 113 Q100 118 91 113 Z" fill="#c98a12" />
            {/* fone de streamer */}
            <path d="M54 76 A46 46 0 0 1 146 76" fill="none" stroke="#ffffff" strokeWidth="7" strokeLinecap="round" />
            <rect x="46" y="68" width="15" height="27" rx="7.5" fill="#ffffff" />
            <rect x="139" y="68" width="15" height="27" rx="7.5" fill="#ffffff" />
            <path d="M54 94 Q58 113 78 113" fill="none" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
            <circle cx="80" cy="113" r="4.5" fill="#ffffff" />
          </g>
        </g>
      </g>
    </svg>
  );
}
