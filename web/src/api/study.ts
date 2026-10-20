import { api } from "./client";
import type { Grade, ReviewResult, Session } from "./types";

/** Disparado quando o progresso do dia muda (avaliação salva, meta alterada), pra barra lateral se atualizar. */
export const PROGRESS_EVENT = "ez:progress";

export const getSession = (newLimit: number) => api<Session>(`/api/session?new_limit=${newLimit}`);

export async function reviewCard(cardId: number, grade: Grade): Promise<ReviewResult> {
  const result = await api<ReviewResult>(`/api/cards/${cardId}/review`, { method: "POST", body: { grade } });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return result;
}
