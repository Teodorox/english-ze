import type { Card, Grade } from "../api/types";
import { intervalLabel, nextIntervalDays } from "../lib/srsPreview";

const GRADES: { grade: Grade; label: string; sub: string; className: string }[] = [
  { grade: 0, label: "L", sub: "errei", className: "grade-l" },
  { grade: 1, label: "MID", sub: "difícil", className: "grade-mid" },
  { grade: 2, label: "W", sub: "bom", className: "grade-w" },
  { grade: 3, label: "GOAT", sub: "fácil", className: "grade-goat" },
];

/** No computador, cada botão mostra também quando o card volta e a tecla do atalho. */
export function GradeButtons({ card, onGrade }: { card: Card; onGrade: (grade: Grade) => void }) {
  return (
    <div className="grades" role="group" aria-label="Como foi?">
      {GRADES.map(({ grade, label, sub, className }) => (
        <button
          key={grade}
          type="button"
          className={className}
          aria-label={`${label}: ${sub} (tecla ${grade + 1})`}
          onClick={() => onGrade(grade)}
        >
          {label}
          <small>{sub}</small>
          <small className="grade-when">
            {intervalLabel(nextIntervalDays(card, grade))} · <kbd>{grade + 1}</kbd>
          </small>
        </button>
      ))}
    </div>
  );
}
