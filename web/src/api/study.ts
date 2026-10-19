import { api } from "./client";
import type { Grade, ReviewResult, Session } from "./types";

export const getSession = (newLimit: number) => api<Session>(`/api/session?new_limit=${newLimit}`);

export const reviewCard = (cardId: number, grade: Grade) =>
  api<ReviewResult>(`/api/cards/${cardId}/review`, { method: "POST", body: { grade } });
