import { api } from "./client";
import type { StudyMode } from "../components/Flashcard";
import type { Grade, ReviewResult, Session } from "./types";

/**
 * Disparado quando o progresso do dia muda (avaliação, fala, diário, frase minerada, meta alterada),
 * pra barra lateral e o plano de hoje se atualizarem.
 */
export const PROGRESS_EVENT = "ez:progress";

/**
 * O tamanho do dia vem do tempo escolhido no primeiro acesso (ou em Ajustes > Meu estudo).
 * rounds > 1: "Mais uma rodada", o dia cresce mais uma vez esse tamanho.
 */
export const getSession = (rounds = 1) => api<Session>(rounds > 1 ? `/api/session?rounds=${rounds}` : "/api/session");

export async function reviewCard(cardId: number, grade: Grade, mode: StudyMode): Promise<ReviewResult> {
  const result = await api<ReviewResult>(`/api/cards/${cardId}/review`, { method: "POST", body: { grade, mode } });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return result;
}
