import { describe, expect, it } from "vitest";
import { scorePronunciation } from "./pronunciation";
import { toSpeechCheck } from "./speechCheck";

const cards = [
  { id: 7, front: "That's tuff" },
  { id: 9, front: "No cap" },
];

describe("toSpeechCheck", () => {
  it("manda só os números da checagem", () => {
    const { words } = scorePronunciation("I want to go home", "I want go home");
    expect(toSpeechCheck("I want to go home", words, cards)).toEqual({ words_total: 5, words_ok: 4 });
  });

  it("liga a prática ao card quando a frase é um card", () => {
    const { words } = scorePronunciation("No cap", "no cap");
    expect(toSpeechCheck(" No cap ", words, cards)).toEqual({ words_total: 2, words_ok: 2, card_id: 9 });
  });

  it("não liga a um card parecido", () => {
    const { words } = scorePronunciation("No cap bro", "no cap bro");
    expect(toSpeechCheck("No cap bro", words, cards)?.card_id).toBeUndefined();
    expect(toSpeechCheck("No cap", words, null)?.card_id).toBeUndefined();
  });

  it("não guarda checagem sem palavras ou grande demais", () => {
    expect(toSpeechCheck("!!!", [], cards)).toBeNull();
    const huge = Array.from({ length: 501 }, () => ({ word: "a", ok: true }));
    expect(toSpeechCheck("a", huge, cards)).toBeNull();
  });
});
