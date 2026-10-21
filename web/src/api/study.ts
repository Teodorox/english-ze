import { api } from "./client";
import type { StudyMode } from "../components/Flashcard";
import type { Grade, ReviewResult, Session } from "./types";

/** Disparado quando o progresso do dia muda (avaliação salva, meta alterada), pra barra lateral se atualizar. */
export const PROGRESS_EVENT = "ez:progress";

export const getSession = (newLimit: number) => api<Session>(`/api/session?new_limit=${newLimit}`);

export async function reviewCard(cardId: number, grade: Grade, mode: StudyMode): Promise<ReviewResult> {
  const result = await api<ReviewResult>(`/api/cards/${cardId}/review`, { method: "POST", body: { grade, mode } });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return result;
}
