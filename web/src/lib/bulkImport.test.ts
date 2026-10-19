import { describe, expect, it } from "vitest";
import { parseBulkLines, toBulkLine } from "./bulkImport";

describe("importação em lote", () => {
  it("lê frase, significado e nota", () => {
    const { cards, invalid } = parseBulkLines("That's tuff | Isso é muito bom | tuff = tough\nBet | Fechou");
    expect(invalid).toEqual([]);
    expect(cards).toEqual([
      { front: "That's tuff", back: "Isso é muito bom", note: "tuff = tough" },
      { front: "Bet", back: "Fechou", note: "" },
    ]);
  });

  it("ignora linhas vazias e separa as que faltam significado", () => {
    const { cards, invalid } = parseBulkLines("\n  só a frase  \n\nOk | Certo\r\n| sem frase");
    expect(cards.map((c) => c.front)).toEqual(["Ok"]);
    expect(invalid).toEqual(["só a frase", "| sem frase"]);
  });

  it("mantém barras extras dentro da nota", () => {
    const { cards } = parseBulkLines("A | B | nota | com barra");
    expect(cards[0].note).toBe("nota | com barra");
  });

  it("toBulkLine volta pro formato de linha", () => {
    expect(toBulkLine({ front: "A", back: "B", note: "" })).toBe("A | B");
    expect(toBulkLine({ front: "A", back: "B", note: "C" })).toBe("A | B | C");
  });
});
