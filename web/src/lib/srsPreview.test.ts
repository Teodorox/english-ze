import { describe, expect, it } from "vitest";
import type { Grade } from "../api/types";
import { intervalLabel, nextIntervalDays } from "./srsPreview";

// Valores tirados do app/srs.py (o servidor), pra prévia nunca divergir do que é salvo.
const CASES: [ease: number, interval: number, reps: number, expected: number[]][] = [
  [2.5, 0, 0, [0, 1, 1, 4]],
  [2.5, 1, 1, [0, 2, 3, 3]],
  [2.5, 3, 2, [0, 4, 8, 10]],
  [2.3, 10, 4, [0, 12, 23, 30]],
  [1.3, 40, 7, [0, 48, 52, 68]],
  [2.5, 1, 2, [0, 2, 2, 3]], // 1 × 2.5 = 2.5 arredonda pra 2, como no Python
];

describe("prévia da repetição espaçada", () => {
  it.each(CASES)("ease %s, intervalo %s, reps %s", (ease, interval_days, reps, expected) => {
    const got = ([0, 1, 2, 3] as Grade[]).map((g) => nextIntervalDays({ ease, interval_days, reps }, g));
    expect(got).toEqual(expected);
  });

  it("rótulos curtos", () => {
    expect(intervalLabel(0)).toBe("hoje");
    expect(intervalLabel(1)).toBe("amanhã");
    expect(intervalLabel(8)).toBe("8 dias");
    expect(intervalLabel(40)).toBe("1 mês");
    expect(intervalLabel(95)).toBe("3 meses");
  });
});
