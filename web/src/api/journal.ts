import { api } from "./client";
import { PROGRESS_EVENT } from "./study";
import type { CorrectResult, JournalEntry, TutorStatus } from "./types";

export const listJournal = () => api<JournalEntry[]>("/api/journal");

export async function createJournal(text: string) {
  const entry = await api<JournalEntry>("/api/journal", { method: "POST", body: { text } });
  window.dispatchEvent(new Event(PROGRESS_EVENT));
  return entry;
}

export const correctJournal = (id: number) => api<CorrectResult>(`/api/journal/${id}/correct`, { method: "POST" });

export const getTutorStatus = () => api<TutorStatus>("/api/tutor/status");
