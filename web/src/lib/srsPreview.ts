// Prévia de quando o card volta para cada nota, mostrada nos botões no computador.
// Espelha app/srs.py (SM-2): se mudar lá, mude aqui (os testes cobrem os mesmos casos).
import type { Card, Grade } from "../api/types";

type CardState = Pick<Card, "ease" | "interval_days" | "reps">;

/** round() do Python: o meio vai pro par (2.5 → 2, 3.5 → 4), diferente do Math.round. */
function pyRound(x: number): number {
  const floor = Math.floor(x);
  const diff = x - floor;
  if (diff < 0.5) return floor;
  if (diff > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}

/** Em quantos dias o card volta com essa nota (0 = hoje mesmo). */
export function nextIntervalDays({ ease, interval_days: interval, reps }: CardState, grade: Grade): number {
  if (grade === 0) return 0;
  if (grade === 1) return reps === 0 ? 1 : Math.max(interval + 1, pyRound(interval * 1.2));
  if (grade === 2) {
    if (reps === 0) return 1;
    if (reps === 1) return Math.max(3, interval + 1);
    return Math.max(interval + 1, pyRound(interval * ease));
  }
  return reps === 0 ? 4 : Math.max(interval + 2, pyRound(interval * ease * 1.3));
}

export function intervalLabel(days: number): string {
  if (days === 0) return "hoje";
  if (days === 1) return "amanhã";
  if (days < 30) return `${days} dias`;
  const months = Math.round(days / 30);
  return months === 1 ? "1 mês" : `${months} meses`;
}
