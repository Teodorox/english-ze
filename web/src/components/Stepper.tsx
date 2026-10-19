interface StepperProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}

/** Ajuste de número com − e +, como o "stepper" do iOS. */
export function Stepper({ label, value, min, max, step = 1, onChange }: StepperProps) {
  return (
    <div className="stepper">
      <span>{label}</span>
      <div className="stepper-controls">
        <button
          type="button"
          aria-label={`Diminuir ${label.toLowerCase()}`}
          disabled={value <= min}
          onClick={() => onChange(Math.max(min, value - step))}
        >
          −
        </button>
        <output aria-live="polite">{value}</output>
        <button
          type="button"
          aria-label={`Aumentar ${label.toLowerCase()}`}
          disabled={value >= max}
          onClick={() => onChange(Math.min(max, value + step))}
        >
          +
        </button>
      </div>
    </div>
  );
}
