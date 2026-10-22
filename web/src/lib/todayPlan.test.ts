import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlanItem, TodayPlan } from "../api/today";
import { addRound, localDay, nextStep, roundsToday, stepsDone } from "./todayPlan";

const item = (id: PlanItem["id"], path: string, done: boolean): PlanItem => ({
  id,
  title: id,
  detail: "",
  path,
  count: done ? 1 : 0,
  target: 1,
  done,
});

const plan = (...items: PlanItem[]): TodayPlan => ({ minutes: 15, goal: "viagem", items, done: items.every((i) => i.done) });

describe("plano de hoje", () => {
  it("o próximo passo é o primeiro que falta", () => {
    const p = plan(item("study", "/estudar", true), item("speak", "/falar", false), item("journal", "/diario", false));
    expect(nextStep(p)?.id).toBe("speak");
  });

  it("não manda pra tela em que a pessoa já está", () => {
    const p = plan(item("study", "/estudar", false), item("speak", "/falar", false));
    expect(nextStep(p, "/estudar")?.id).toBe("speak");
  });

  it("tudo feito: não há próximo", () => {
    expect(nextStep(plan(item("study", "/estudar", true)))).toBeNull();
  });

  it("conta os passos feitos", () => {
    expect(stepsDone(plan(item("study", "/estudar", true), item("speak", "/falar", false)))).toEqual({ done: 1, total: 2 });
  });
});

describe("mais uma rodada", () => {
  // Os testes rodam fora do navegador: um localStorage de mentira, em memória.
  beforeEach(() => {
    const store = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => store.set(k, v),
    });
  });

  it("começa em 1 e cresce de um em um, até 10", () => {
    expect(roundsToday("2026-10-22")).toBe(1);
    expect(addRound("2026-10-22")).toBe(2);
    expect(roundsToday("2026-10-22")).toBe(2);
    for (let i = 0; i < 20; i++) addRound("2026-10-22");
    expect(roundsToday("2026-10-22")).toBe(10);
  });

  it("recomeça no dia seguinte", () => {
    addRound("2026-10-22");
    expect(roundsToday("2026-10-23")).toBe(1);
  });

  it("dia local no formato AAAA-MM-DD", () => {
    expect(localDay(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
  });
});
