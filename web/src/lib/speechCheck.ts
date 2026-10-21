import { MAX_SPEECH_WORDS, type SpeechCheck } from "../api/speech";
import type { WordResult } from "./pronunciation";

/**
 * O que vai pro servidor depois de uma checagem: palavras certas e total, e o card quando a frase
 * praticada é exatamente um card da pessoa. Sem palavras (ou frase grande demais), não guarda nada.
 */
export function toSpeechCheck(
  target: string,
  words: WordResult[],
  cards: { id: number; front: string }[] | null,
): SpeechCheck | null {
  if (!words.length || words.length > MAX_SPEECH_WORDS) return null;
  const check: SpeechCheck = { words_total: words.length, words_ok: words.filter((w) => w.ok).length };
  const card = cards?.find((c) => c.front.trim() === target.trim());
  if (card) check.card_id = card.id;
  return check;
}
