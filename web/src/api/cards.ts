import { api } from "./client";
import { PROGRESS_EVENT } from "./study";
import type { Card, NewCard } from "./types";

export function listCards(filters: { q?: string; category?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return api<Card[]>(`/api/cards${query ? `?${query}` : ""}`);
}

export const listCategories = () => api<string[]>("/api/categories");

export async function createCard(card: NewCard) {
  const created = await api<Card>("/api/cards", { method: "POST", body: card });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return created;
}

export const deleteCard = (id: number) => api<void>(`/api/cards/${id}`, { method: "DELETE" });
