// Compara a frase alvo com o que o reconhecimento de voz entendeu.

export function normalizeWords(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[’‘]/g, "'")
    .replace(/[^a-z0-9' ]+/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export interface WordResult {
  word: string;
  ok: boolean;
}

export function scorePronunciation(target: string, heard: string) {
  const heardWords = new Set(normalizeWords(heard));
  const words: WordResult[] = normalizeWords(target).map((word) => ({ word, ok: heardWords.has(word) }));
  const hits = words.filter((w) => w.ok).length;
  return { score: words.length ? Math.round((hits / words.length) * 100) : 0, words };
}

export function verdict(score: number): string {
  if (score >= 90) return "No cap 🔥";
  if (score >= 60) return "That's a W 👍";
  return "Run it back 💪";
}
