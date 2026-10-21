import { describe, expect, it } from "vitest";
import { firstName, greeting } from "./greeting";

describe("saudação", () => {
  it("usa só o primeiro nome", () => {
    expect(firstName("José Teodoro")).toBe("José");
    expect(firstName("  Ana   Clara ")).toBe("Ana");
    expect(firstName("")).toBe("");
  });

  it("muda com a hora do dia", () => {
    expect(greeting("José", 5)).toBe("Bom dia, José!");
    expect(greeting("José", 11)).toBe("Bom dia, José!");
    expect(greeting("José", 12)).toBe("Boa tarde, José!");
    expect(greeting("José", 17)).toBe("Boa tarde, José!");
    expect(greeting("José", 18)).toBe("Boa noite, José!");
    expect(greeting("José", 2)).toBe("Boa noite, José!");
  });

  it("sem nome, só cumprimenta", () => {
    expect(greeting("   ", 9)).toBe("Bom dia!");
  });
});
