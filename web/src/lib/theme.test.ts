import { describe, expect, it } from "vitest";
import { resolveTheme } from "./theme";

describe("tema", () => {
  it("Automático segue o aparelho", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("Claro e Escuro ignoram o aparelho", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});
