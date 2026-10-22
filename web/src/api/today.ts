import { api } from "./client";

/** Um passo do plano de hoje (GET /api/today). */
export interface PlanItem {
  id: "study" | "speak" | "journal" | "mine";
  title: string;
  detail: string;
  path: string;
  count: number;
  target: number;
  done: boolean;
}

export interface TodayPlan {
  minutes: number;
  goal: string;
  items: PlanItem[];
  done: boolean;
}

export const getToday = () => api<TodayPlan>("/api/today");
