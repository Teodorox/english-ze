// Fila de uma sessão de estudo. Funções puras: recebem um estado e devolvem o próximo.
import type { Card, Grade, Session } from "../api/types";

export interface QueueState {
  queue: Card[]; // próximos cards, em ordem
  current: Card | null; // card na tela (null = sessão acabou)
  revealed: boolean;
  done: number; // avaliações feitas nesta sessão
}

export function startQueue(session: Pick<Session, "due" | "new">): QueueState {
  const [current = null, ...queue] = [...session.due, ...session.new];
  return { queue, current, revealed: false, done: 0 };
}

export function reveal(state: QueueState): QueueState {
  return state.current ? { ...state, revealed: true } : state;
}

/**
 * Depois de avaliar: se errou (L), o card volta pro fim da fila e aparece de novo hoje,
 * com os acertos zerados como no servidor (assim volta no exercício mais fácil).
 */
export function afterGrade(state: QueueState, grade: Grade): QueueState {
  if (!state.current) return state;
  const reviewed: Card = {
    ...state.current,
    introduced_on: state.current.introduced_on ?? "hoje",
    reps: grade === 0 ? 0 : state.current.reps + 1,
  };
  const queue = grade === 0 ? [...state.queue, reviewed] : state.queue;
  const [current = null, ...rest] = queue;
  return { queue: rest, current, revealed: false, done: state.done + 1 };
}

/** Devolve um card à sessão (quando a avaliação não pôde ser salva). */
export function requeue(state: QueueState, card: Card): QueueState {
  if (!state.current) return { ...state, current: card, revealed: false };
  return { ...state, queue: [...state.queue.filter((c) => c.id !== card.id), card] };
}

export function counts(state: QueueState) {
  const all = state.current ? [state.current, ...state.queue] : state.queue;
  return {
    remaining: all.length,
    newCount: all.filter((card) => !card.introduced_on).length,
  };
}
