import { api } from "./client";

/** Limite de palavras que o servidor aceita numa checagem (frases maiores não são guardadas). */
export const MAX_SPEECH_WORDS = 500;

export interface SpeechCheck {
  words_total: number;
  words_ok: number;
  card_id?: number;
}

/** Guarda o resultado de um "Checar pronúncia". Vão só os números: nem o áudio nem o texto entendido. */
export const saveSpeechCheck = (check: SpeechCheck) =>
  api<{ id: number; score: number }>("/api/speech-checks", { method: "POST", body: check });
