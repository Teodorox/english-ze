import { describe, expect, it } from "vitest";
import { normalizeWords, scorePronunciation, verdict } from "./pronunciation";

describe("pronúncia", () => {
  it("normaliza pontuação, maiúsculas e apóstrofos curvos", () => {
    expect(normalizeWords("I’m gonna stream, TOMORROW!")).toEqual(["i'm", "gonna", "stream", "tomorrow"]);
  });

  it("pontua as palavras reconhecidas", () => {
    const result = scorePronunciation("No cap, that was crazy.", "no cap that was lazy");
    expect(result.score).toBe(80);
    expect(result.words).toEqual([
      { word: "no", ok: true },
      { word: "cap", ok: true },
      { word: "that", ok: true },
      { word: "was", ok: true },
      { word: "crazy", ok: false },
    ]);
  });

  it("frase vazia dá zero sem quebrar", () => {
    expect(scorePronunciation("", "anything").score).toBe(0);
  });

  it("veredito em gíria", () => {
    expect(verdict(95)).toContain("No cap");
    expect(verdict(70)).toContain("W");
    expect(verdict(20)).toContain("Run it back");
  });
});
