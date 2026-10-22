// Tipos que espelham as respostas da API Python (app/main.py).

import type { DailyMinutes, Goal, Level } from "../lib/studyProfile";

export type Grade = 0 | 1 | 2 | 3;

export interface Card {
  id: number;
  front: string;
  back: string;
  note: string;
  category: string;
  source: string;
  created_at: string;
  ease: number;
  interval_days: number;
  reps: number;
  lapses: number;
  due: string | null;
  introduced_on: string | null;
  /** Só na sessão de estudo: traduções erradas pra opções (vazia se a pessoa tem poucos cards). */
  choices?: string[];
}

export interface NewCard {
  front: string;
  back: string;
  note?: string;
  category?: string;
  source?: string;
}

export interface Session {
  due: Card[];
  new: Card[];
  /** Todas as revisões vencidas (due traz no máximo o teto do dia). */
  due_total: number;
  new_per_day: number;
  /** Revisões acumuladas seguraram as frases novas de hoje. */
  held_back: boolean;
}

export interface ReviewResult {
  due: string;
  interval_days: number;
}

export interface Mistake {
  original: string;
  correction: string;
  explanation: string;
}

export interface Correction {
  corrected: string;
  natural: string;
  mistakes: Mistake[];
  encouragement: string;
}

export interface JournalEntry {
  id: number;
  text: string;
  created_at: string;
  correction: Correction | null;
}

export interface CorrectResult {
  correction: Correction;
  cards_created: number;
}

export interface Stats {
  streak: number;
  reviews_today: number;
  speech_checks_today: number;
  total_cards: number;
  learned: number;
  mature: number;
  due_today: number;
  due_tomorrow: number;
  history: { day: string; reviews: number }[];
  skills: SkillLevel[];
}

export type SkillId = "vocabulary" | "listening" | "speaking" | "writing";
export type Band = "A1" | "A2" | "B1" | "B2";

/** Estimativa do nível numa habilidade (app/skills.py). */
export interface SkillLevel {
  id: SkillId;
  value: number;
  band: Band;
  /** Quanto já andou dentro da faixa, de 0 a 1. */
  progress: number;
  next_band: Band | null;
  /** Quantos acertos/erros recentes entraram na conta (0 = só o ponto de partida e o volume). */
  samples: number;
  accuracy: number | null;
  start_band: Band;
}

/** Quem está logado (GET /api/me). */
export interface Me {
  id: number;
  email: string;
  name: string;
  timezone: string;
  /** Como a IA deve tratar essa pessoa na correção ("" = descrição padrão). */
  learner: string;
  /** Perfil de estudo, respondido no primeiro acesso. */
  goals: Goal[];
  level: Level | null;
  daily_minutes: DailyMinutes;
  /** false = ainda não passou pelo primeiro acesso. */
  onboarded: boolean;
}

export interface StudyProfile {
  goals: Goal[];
  level: Level;
  daily_minutes: DailyMinutes;
}

export interface TutorStatus {
  enabled: boolean;
  model: string;
}
