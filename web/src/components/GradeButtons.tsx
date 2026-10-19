import type { Grade } from "../api/types";

const GRADES: { grade: Grade; label: string; sub: string; className: string }[] = [
  { grade: 0, label: "L", sub: "errei", className: "grade-l" },
  { grade: 1, label: "MID", sub: "difícil", className: "grade-mid" },
  { grade: 2, label: "W", sub: "bom", className: "grade-w" },
  { grade: 3, label: "GOAT", sub: "fácil", className: "grade-goat" },
];

export function GradeButtons({ onGrade }: { onGrade: (grade: Grade) => void }) {
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
        </button>
      ))}
    </div>
  );
}
