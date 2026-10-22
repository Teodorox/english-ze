// Plano de hoje no app: o próximo passo e as rodadas extras ("Mais uma rodada").
import type { PlanItem, TodayPlan } from "../api/today";
import { loadPref, savePref } from "./storage";

/** O primeiro passo que falta, sem contar a tela em que a pessoa já está. */
export function nextStep(plan: TodayPlan, currentPath?: string): PlanItem | null {
  return plan.items.find((item) => !item.done && item.path !== currentPath) ?? null;
}

/** "2 de 3 passos" */
export function stepsDone(plan: TodayPlan): { done: number; total: number } {
  return { done: plan.items.filter((i) => i.done).length, total: plan.items.length };
}

/** Data local do aparelho (AAAA-MM-DD): as rodadas extras recomeçam a cada dia. */
export function localDay(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

const roundsKey = (day: string) => `rodadas-${day}`;

/** Quantas rodadas o Estudar já pediu hoje (1 = só a do plano). */
export function roundsToday(day = localDay()): number {
  return loadPref(roundsKey(day), 1);
}

/** Mais uma rodada: o dia cresce mais uma vez o tamanho escolhido (o servidor aceita até 10). */
export function addRound(day = localDay()): number {
  const rounds = Math.min(roundsToday(day) + 1, 10);
  savePref(roundsKey(day), rounds);
  return rounds;
}
