import { describe, expect, it } from "vitest";
import { daysActiveThisWeek, fraction, streakMessage, weekdayInitial } from "./stats";

const day = (d: number, reviews: number) => ({ day: `2026-10-${String(d).padStart(2, "0")}`, reviews });

describe("estatísticas", () => {
  it("conta só os últimos 7 dias com estudo", () => {
    const history = [day(6, 9), day(7, 9), ...[13, 14, 15, 16, 17, 18, 19].map((d, i) => day(d, i % 2 ? 0 : 5))];
    expect(daysActiveThisWeek(history)).toBe(4);
    expect(daysActiveThisWeek([])).toBe(0);
  });

  it("fração limitada entre 0 e 1", () => {
    expect(fraction(10, 20)).toBe(0.5);
    expect(fraction(30, 20)).toBe(1);
    expect(fraction(0, 0)).toBe(0);
    expect(fraction(3, 0)).toBe(1);
  });

  it("inicial do dia da semana", () => {
    expect(weekdayInitial("2026-10-19")).toBe("S"); // segunda
    expect(weekdayInitial("2026-10-18")).toBe("D"); // domingo
    expect(weekdayInitial("2026-10-21")).toBe("Q"); // quarta
  });

  it("mensagem conforme a sequência", () => {
    expect(streakMessage(0)).toContain("começar");
    expect(streakMessage(5)).toContain("locked in");
    expect(streakMessage(40)).toContain("GOAT");
  });
});
