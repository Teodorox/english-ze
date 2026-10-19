import type { Card } from "../api/types";

const DAY_MS = 24 * 60 * 60 * 1000;

/** Datas da API vêm como "AAAA-MM-DD"; comparamos em dias inteiros, sem fuso. */
function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((Date.parse(`${toIso}T00:00:00Z`) - Date.parse(`${fromIso}T00:00:00Z`)) / DAY_MS);
}

export function todayIso(now = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** "Ainda não estudado", "Revisão hoje", "amanhã", "em 5 dias" ou "em 3 meses". */
export function dueLabel(card: Pick<Card, "introduced_on" | "due">, today = todayIso()): string {
  if (!card.introduced_on || !card.due) return "Ainda não estudado";
  const days = daysBetween(today, card.due);
  if (days <= 0) return "Revisão hoje";
  if (days === 1) return "Revisão amanhã";
  if (days < 45) return `Revisão em ${days} dias`;
  const months = Math.round(days / 30);
  return `Revisão em ${months} ${months === 1 ? "mês" : "meses"}`;
}
