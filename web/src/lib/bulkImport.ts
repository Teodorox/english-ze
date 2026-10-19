// Importação em lote: uma frase por linha, no formato "frase | significado | nota".

export interface ParsedCard {
  front: string;
  back: string;
  note: string;
}

export function parseBulkLines(text: string): { cards: ParsedCard[]; invalid: string[] } {
  const cards: ParsedCard[] = [];
  const invalid: string[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const [front = "", back = "", ...rest] = line.split("|").map((part) => part.trim());
    if (front && back) cards.push({ front, back, note: rest.join(" | ") });
    else invalid.push(line);
  }
  return { cards, invalid };
}

export function toBulkLine(card: ParsedCard): string {
  return [card.front, card.back, card.note].filter(Boolean).join(" | ");
}
