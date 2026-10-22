import { describe, expect, it } from "vitest";
import type { Card } from "../api/types";
import {
  acceptedAnswers,
  checkDictation,
  checkTranslation,
  gradeFor,
  ptWords,
  shuffledOptions,
  stageFor,
} from "./activeStudy";

const card = (changes: Partial<Card> = {}): Card => ({
  id: 7,
  front: "I'm lost.",
  back: "Estou perdido.",
  note: "",
  category: "viagem",
  source: "deck inicial",
  created_at: "2026-10-21",
  ease: 2.5,
  interval_days: 1,
  reps: 1,
  lapses: 0,
  due: "2026-10-22",
  introduced_on: "2026-10-21",
  choices: ["Siga em frente.", "É longe daqui?", "Dá pra ir a pé?"],
  ...changes,
});

describe("qual exercício", () => {
  it("frase nova é só pra conhecer, nos dois modos", () => {
    expect(stageFor(card({ introduced_on: null, reps: 0 }), "read")).toBe("intro");
    expect(stageFor(card({ introduced_on: null, reps: 0 }), "listen")).toBe("intro");
  });

  it("no Ler: opções nas primeiras vezes, depois digitar", () => {
    expect(stageFor(card({ reps: 1 }), "read")).toBe("choice");
    expect(stageFor(card({ reps: 2 }), "read")).toBe("choice");
    expect(stageFor(card({ reps: 3 }), "read")).toBe("type");
  });

  it("errou: os acertos zeram e volta pras opções", () => {
    expect(stageFor(card({ reps: 0, lapses: 1 }), "read")).toBe("choice");
  });

  it("sem opções suficientes, pede pra digitar", () => {
    expect(stageFor(card({ choices: [] }), "read")).toBe("type");
    expect(stageFor(card({ choices: undefined }), "read")).toBe("type");
  });

  it("no Ouvir é ditado", () => {
    expect(stageFor(card({ reps: 1 }), "listen")).toBe("dictation");
  });

  it("resultado vira a nota da repetição espaçada", () => {
    expect([gradeFor("right"), gradeFor("close"), gradeFor("wrong")]).toEqual([2, 1, 0]);
  });
});

describe("opções", () => {
  it("a certa está entre as quatro, sempre na mesma ordem pro mesmo card", () => {
    const options = shuffledOptions(card());
    expect(options).toHaveLength(4);
    expect(options).toContain("Estou perdido.");
    expect(shuffledOptions(card())).toEqual(options);
  });

  it("a certa não fica sempre no mesmo lugar", () => {
    const places = new Set(Array.from({ length: 30 }, (_, id) => shuffledOptions(card({ id })).indexOf("Estou perdido.")));
    expect(places.size).toBeGreaterThan(2);
  });
});

describe("tradução digitada", () => {
  it("ignora acento, maiúscula e pontuação", () => {
    expect(checkTranslation("estou perdido", "Estou perdido.").verdict).toBe("right");
    expect(checkTranslation("SÉRIO? ", "Sério?").verdict).toBe("right");
    expect(checkTranslation("serio", "Sério?").verdict).toBe("right");
  });

  it("aceita o jeito falado", () => {
    expect(ptWords("Tô indo pro trabalho")).toEqual(["estou", "indo", "para", "o", "trabalho"]);
    expect(checkTranslation("to perdido", "Estou perdido.").verdict).toBe("right");
    expect(checkTranslation("eu tava no mudo", "Desculpa, eu tava no mudo.").verdict).toBe("right");
  });

  it("perdoa erro de digitação pequeno", () => {
    expect(checkTranslation("sem mentira aquilo foi insno", "Sem mentira, aquilo foi insano.").verdict).toBe("right");
  });

  it("aceita qualquer uma das versões separadas por barra", () => {
    expect(checkTranslation("desculpa por isso", "Foi mal. / Desculpa por isso.").verdict).toBe("right");
    expect(checkTranslation("foi mal", "Foi mal. / Desculpa por isso.").verdict).toBe("right");
    expect(checkTranslation("o mano ta pirando", "O mano tá viajando / pirando.").verdict).toBe("right");
    expect(checkTranslation("havia uma vez", "Existia/Havia/Tinha uma vez").verdict).toBe("right");
  });

  it("o que está entre parênteses é opcional", () => {
    expect(checkTranslation("morri mano", "Morri (de rir), mano.").verdict).toBe("right");
    expect(checkTranslation("morri de rir mano", "Morri (de rir), mano.").verdict).toBe("right");
  });

  it("monta as versões aceitas", () => {
    expect(acceptedAnswers("Saquei. / Entendi.")).toEqual([[["saquei"]], [["entendi"]]]);
  });

  it("meio certo é 'quase'", () => {
    expect(checkTranslation("nao estou mentindo", "Sério mesmo, não tô mentindo.").verdict).toBe("close");
  });

  it("errado ou vazio é errado", () => {
    expect(checkTranslation("vire a esquerda", "Estou perdido.").verdict).toBe("wrong");
    expect(checkTranslation("   ", "Estou perdido.").verdict).toBe("wrong");
    expect(checkTranslation("/", "Estou perdido.").verdict).toBe("wrong");
  });

  it("encher de palavras não vira acerto", () => {
    const answer = "estou perdido sem mentira aquilo foi insano siga em frente";
    expect(checkTranslation(answer, "Estou perdido.").verdict).not.toBe("right");
  });
});

describe("ditado", () => {
  it("tudo certo, mesmo sem apóstrofo e pontuação", () => {
    const result = checkDictation("im lost", "I'm lost.");
    expect(result.verdict).toBe("right");
    expect(result.words).toEqual([
      { word: "im", ok: true },
      { word: "lost", ok: true },
    ]);
  });

  it("mostra as palavras que faltaram", () => {
    const result = checkDictation("is this flight late", "Is this flight delayed?");
    expect(result.verdict).toBe("close");
    expect(result.words.filter((w) => !w.ok).map((w) => w.word)).toEqual(["delayed"]);
  });

  it("palavras a mais também contam", () => {
    expect(checkDictation("im so so very lost today", "I'm lost.").verdict).toBe("wrong");
  });

  it("vazio é errado", () => {
    expect(checkDictation("", "I'm lost.").verdict).toBe("wrong");
  });
});
