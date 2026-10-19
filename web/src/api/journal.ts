import { api } from "./client";
import type { CorrectResult, JournalEntry, TutorStatus } from "./types";

export const listJournal = () => api<JournalEntry[]>("/api/journal");

export const createJournal = (text: string) => api<JournalEntry>("/api/journal", { method: "POST", body: { text } });

export const correctJournal = (id: number) => api<CorrectResult>(`/api/journal/${id}/correct`, { method: "POST" });

export const getTutorStatus = () => api<TutorStatus>("/api/tutor/status");
