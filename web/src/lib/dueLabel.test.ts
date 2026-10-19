import { describe, expect, it } from "vitest";
import { dueLabel, todayIso } from "./dueLabel";

const TODAY = "2026-10-19";

describe("texto da próxima revisão", () => {
  it("card novo", () => {
    expect(dueLabel({ introduced_on: null, due: null }, TODAY)).toBe("Ainda não estudado");
  });

  it("hoje, atrasado, amanhã e em dias", () => {
    expect(dueLabel({ introduced_on: "x", due: "2026-10-19" }, TODAY)).toBe("Revisão hoje");
    expect(dueLabel({ introduced_on: "x", due: "2026-10-10" }, TODAY)).toBe("Revisão hoje");
    expect(dueLabel({ introduced_on: "x", due: "2026-10-20" }, TODAY)).toBe("Revisão amanhã");
    expect(dueLabel({ introduced_on: "x", due: "2026-10-26" }, TODAY)).toBe("Revisão em 7 dias");
  });

  it("intervalos longos em meses, atravessando o ano", () => {
    expect(dueLabel({ introduced_on: "x", due: "2026-12-19" }, TODAY)).toBe("Revisão em 2 meses");
    expect(dueLabel({ introduced_on: "x", due: "2027-01-01" }, "2026-11-20")).toBe("Revisão em 42 dias");
    expect(dueLabel({ introduced_on: "x", due: "2026-12-05" }, "2026-11-05")).toBe("Revisão em 30 dias");
    expect(dueLabel({ introduced_on: "x", due: "2027-01-20" }, "2026-12-01")).toBe("Revisão em 2 meses");
  });

  it("todayIso usa a data local", () => {
    expect(todayIso(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
  });
});
