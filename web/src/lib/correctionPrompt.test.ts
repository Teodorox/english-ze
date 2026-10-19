import { describe, expect, it } from "vitest";
import { correctionPrompt } from "./correctionPrompt";

describe("prompt de correção", () => {
  it("inclui as instruções e o texto sem espaços sobrando", () => {
    const prompt = correctionPrompt("  Yesterday I go to work.  \n");
    expect(prompt).toContain("Corrija o texto abaixo");
    expect(prompt).toContain("como um americano diria");
    expect(prompt.endsWith("Texto:\nYesterday I go to work.")).toBe(true);
  });
});
