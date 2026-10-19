import { api } from "./client";

export const getTranscribeStatus = () => api<{ available: boolean; model: string }>("/api/transcribe/status");

/** Envia a gravação pro servidor (Whisper) e devolve o texto entendido. */
export const transcribeAudio = (audio: Blob) =>
  api<{ text: string }>("/api/transcribe", { method: "POST", body: audio });
