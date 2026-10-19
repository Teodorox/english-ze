import { api } from "./client";
import type { Card, NewCard } from "./types";

export function listCards(filters: { q?: string; category?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return api<Card[]>(`/api/cards${query ? `?${query}` : ""}`);
}

export const listCategories = () => api<string[]>("/api/categories");

export const createCard = (card: NewCard) => api<Card>("/api/cards", { method: "POST", body: card });

export const deleteCard = (id: number) => api<void>(`/api/cards/${id}`, { method: "DELETE" });
