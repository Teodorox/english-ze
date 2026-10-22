// Estudo ativo: qual exercício cada card pede e como conferir o que a pessoa respondeu.
import type { Card, Grade } from "../api/types";
import { normalizeWords, type WordResult } from "./pronunciation";

export type StudyMode = "read" | "listen";
export type Stage = "intro" | "choice" | "type" | "dictation";
export type Verdict = "right" | "close" | "wrong";

/** Quantas vezes a frase aparece com opções antes de pedir a tradução digitada. */
export const CHOICE_ROUNDS = 2;

/**
 * Frase nova: só conhecer. Depois, no Ler, opções nas primeiras vezes e tradução digitada
 * quando já acertou; um erro zera os acertos (reps) e a frase volta pras opções.
 * No Ouvir, ditado: escrever em inglês o que ouviu.
 */
export function stageFor(card: Card, mode: StudyMode): Stage {
  if (!card.introduced_on) return "intro";
  if (mode === "listen") return "dictation";
  if (card.reps <= CHOICE_ROUNDS && card.choices?.length === 3) return "choice";
  return "type";
}

export function gradeFor(verdict: Verdict): Grade {
  return verdict === "right" ? 2 : verdict === "close" ? 1 : 0;
}

/** A certa no meio das erradas, sempre na mesma ordem pro mesmo card (não pula ao redesenhar). */
export function shuffledOptions(card: Card): string[] {
  const options = [card.back, ...(card.choices ?? [])];
  const rank = (text: string) => {
    let h = card.id * 2654435761;
    for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
    return h >>> 0;
  };
  return options.sort((a, b) => rank(a) - rank(b));
}

// ---------- Tradução digitada (português) ----------

// Jeitos de falar que valem igual ao escrito: "tô" = "estou", "pra" = "para"...
const SPOKEN: Record<string, string[]> = {
  to: ["estou"],
  ta: ["esta"],
  tava: ["estava"],
  tao: ["estao"],
  pra: ["para"],
  pro: ["para", "o"],
  pros: ["para", "os"],
  pras: ["para", "as"],
  ce: ["voce"],
  vc: ["voce"],
  num: ["em", "um"],
  numa: ["em", "uma"],
};

function plain(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Palavras sem acento, maiúscula nem pontuação, com o jeito falado trocado pelo escrito. */
export function ptWords(text: string): string[] {
  return plain(text)
    .replace(/[^a-z0-9/ ]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .flatMap((w) => SPOKEN[w] ?? [w]);
}

/** Cada posição aceita uma ou mais palavras ("tinha/havia" vira as duas). */
type Slot = string[];

function slots(text: string): Slot[] {
  return ptWords(text)
    .map((w) => w.split("/").filter(Boolean))
    .filter((options) => options.length);
}

/**
 * As respostas aceitas a partir do verso do card:
 * "Foi mal. / Desculpa por isso." vale as duas; "O mano tá viajando / pirando." vale
 * "viajando" e "pirando"; o que está entre parênteses pode vir ou não.
 */
export function acceptedAnswers(back: string): Slot[][] {
  const texts = new Set<string>();
  for (const version of [back.replace(/\(([^)]*)\)/g, "$1"), back.replace(/\([^)]*\)/g, " ")]) {
    const parts = version.split(/\s+\/\s+/);
    const first = parts[0];
    texts.add(first);
    for (const part of parts.slice(1)) {
      texts.add(part);
      const firstWords = first.trim().split(/\s+/);
      const partWords = part.trim().split(/\s+/);
      if (partWords.length < firstWords.length) {
        texts.add([...firstWords.slice(0, firstWords.length - partWords.length), ...partWords].join(" "));
      }
    }
  }
  return [...texts].map(slots).filter((s) => s.length);
}

function editDistance(a: string, b: string): number {
  const row = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = row[0];
    row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const tmp = row[j];
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = tmp;
    }
  }
  return row[b.length];
}

/** Erro de digitação pequeno não conta: 1 letra em palavras médias, 2 nas longas. */
function sameWord(typed: string, expected: string): boolean {
  if (typed === expected) return true;
  const allowed = expected.length >= 8 ? 2 : expected.length >= 4 ? 1 : 0;
  return allowed > 0 && editDistance(typed, expected) <= allowed;
}

/** Quanto a resposta bate com uma versão aceita (0 a 1): palavras em comum, nos dois sentidos. */
function similarity(answer: string[], expected: Slot[]): number {
  const left = [...answer];
  let matched = 0;
  for (const slot of expected) {
    const i = left.findIndex((w) => slot.some((option) => sameWord(w, option)));
    if (i >= 0) {
      matched += 1;
      left.splice(i, 1);
    }
  }
  return (2 * matched) / (answer.length + expected.length);
}

export function checkTranslation(answer: string, back: string): { verdict: Verdict; score: number } {
  const typed = ptWords(answer).filter((w) => w !== "/");
  if (!typed.length) return { verdict: "wrong", score: 0 };
  const score = Math.max(0, ...acceptedAnswers(back).map((expected) => similarity(typed, expected)));
  return { verdict: score >= 0.8 ? "right" : score >= 0.5 ? "close" : "wrong", score };
}

// ---------- Ditado (inglês) ----------

/** No ditado a frase em inglês é uma só: compara palavra por palavra ("I'm" e "Im" valem igual). */
export function checkDictation(answer: string, front: string): { verdict: Verdict; words: WordResult[] } {
  const strip = (text: string) => normalizeWords(text).map((w) => w.replace(/'/g, ""));
  const typed = strip(answer);
  const left = [...typed];
  const words = strip(front).map((word) => {
    const i = left.indexOf(word);
    if (i >= 0) left.splice(i, 1);
    return { word, ok: i >= 0 };
  });
  // Palavras em comum, nos dois sentidos: faltar palavra e sobrar palavra contam igual.
  const hits = words.filter((w) => w.ok).length;
  const score = words.length ? (2 * hits) / (words.length + typed.length) : 0;
  return { verdict: score === 1 ? "right" : score >= 0.7 ? "close" : "wrong", words };
}
