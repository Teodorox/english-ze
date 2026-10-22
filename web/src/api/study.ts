import { api } from "./client";
import type { StudyMode } from "../components/Flashcard";
import type { Grade, ReviewResult, Session } from "./types";

/** Disparado quando o progresso do dia muda (avaliação salva, meta alterada), pra barra lateral se atualizar. */
export const PROGRESS_EVENT = "ez:progress";

/** O tamanho do dia vem do tempo escolhido no primeiro acesso (ou em Ajustes > Meu estudo). */
export const getSession = () => api<Session>("/api/session");

export async function reviewCard(cardId: number, grade: Grade, mode: StudyMode): Promise<ReviewResult> {
  const result = await api<ReviewResult>(`/api/cards/${cardId}/review`, { method: "POST", body: { grade, mode } });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return result;
}
