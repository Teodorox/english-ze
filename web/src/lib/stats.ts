// Cálculos da tela de progresso.

export interface DayCount {
  day: string; // "AAAA-MM-DD"
  reviews: number;
}

/** Em quantos dos últimos 7 dias (incluindo hoje) houve estudo. */
export function daysActiveThisWeek(history: DayCount[]): number {
  return history.slice(-7).filter((d) => d.reviews > 0).length;
}

/** Fração 0–1 pra preencher um anel. */
export function fraction(value: number, goal: number): number {
  if (goal <= 0) return value > 0 ? 1 : 0;
  return Math.max(0, Math.min(1, value / goal));
}

const WEEKDAYS = ["D", "S", "T", "Q", "Q", "S", "S"];

/** Inicial do dia da semana em português (D, S, T, Q, Q, S, S). */
export function weekdayInitial(isoDay: string): string {
  return WEEKDAYS[new Date(`${isoDay}T12:00:00Z`).getUTCDay()];
}

/** Frase de incentivo conforme a sequência de dias. */
export function streakMessage(streak: number): string {
  if (streak === 0) return "Bora começar a sequência hoje.";
  if (streak < 3) return "Começou bem. Não quebra a corrente!";
  if (streak < 7) return "Bro is locked in 🔒";
  if (streak < 30) return "Aura +1000. Você tá voando.";
  return "GOAT 🐐 Sequência lendária.";
}
