import { GOALS, LEVELS, MINUTES, toggleGoal, type DailyMinutes, type Goal, type Level } from "../lib/studyProfile";

/** Objetivos: dá pra marcar vários. */
export function GoalPicker({ value, onChange }: { value: Goal[]; onChange: (goals: Goal[]) => void }) {
  return (
    <div className="goal-grid" role="group" aria-label="Objetivos">
      {GOALS.map((goal) => (
        <button
          key={goal.id}
          type="button"
          className="choice goal-choice"
          aria-pressed={value.includes(goal.id)}
          onClick={() => onChange(toggleGoal(value, goal.id))}
        >
          <span className="choice-emoji" aria-hidden="true">
            {goal.emoji}
          </span>
          {goal.label}
        </button>
      ))}
    </div>
  );
}

/** Lista de opções em que só uma vale (nível e tempo por dia). */
function OptionList<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | null;
  options: { value: T; label: string; description: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="choice-list" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          className="choice"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
        >
          <strong>{option.label}</strong>
          <span>{option.description}</span>
        </button>
      ))}
    </div>
  );
}

export function LevelPicker({ value, onChange }: { value: Level | null; onChange: (level: Level) => void }) {
  return (
    <OptionList
      label="Nível"
      value={value}
      options={LEVELS.map((l) => ({ value: l.id, label: l.label, description: l.description }))}
      onChange={onChange}
    />
  );
}

export function MinutesPicker({ value, onChange }: { value: DailyMinutes | null; onChange: (m: DailyMinutes) => void }) {
  return <OptionList label="Tempo por dia" value={value} options={MINUTES} onChange={onChange} />;
}
