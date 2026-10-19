import { api } from "./client";
import type { Card } from "./types";

export function listCards(filters: { q?: string; category?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return api<Card[]>(`/api/cards${query ? `?${query}` : ""}`);
}
