import { api } from "./client";
import type { Me, StudyProfile } from "./types";

export interface SignupData {
  name: string;
  email: string;
  password: string;
  invite: string;
}

/** Quem está logado. Sem login, a API responde 401 (e o App mostra a tela de entrada). */
export const getMe = () => api<Me>("/api/me");

export const login = (email: string, password: string) =>
  api<{ ok: true }>("/api/login", { method: "POST", body: { email, password } });

/** O fuso do aparelho vai junto: é ele que decide quando vira o dia das revisões. */
export const signup = (data: SignupData) =>
  api<{ ok: true }>("/api/signup", {
    method: "POST",
    body: { ...data, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
  });

export const logout = () => api<{ ok: true }>("/api/logout", { method: "POST" });

export const updateMe = (
  changes: Partial<Pick<Me, "name" | "timezone" | "goals" | "daily_minutes">> & { level?: StudyProfile["level"] },
) => api<Me>("/api/me", { method: "PATCH", body: changes });

/** Respostas do primeiro acesso: objetivos, nível e tempo por dia. */
export const completeOnboarding = (profile: StudyProfile) =>
  api<Me>("/api/me/onboarding", { method: "POST", body: profile });

export const changePassword = (current: string, next: string) =>
  api<{ ok: true }>("/api/me/password", { method: "POST", body: { current, new: next } });

export const logoutOtherDevices = () => api<{ ended: number }>("/api/me/logout-others", { method: "POST" });

/** Apaga a conta e tudo dela. Não tem volta. */
export const deleteAccount = (password: string) =>
  api<{ ok: true }>("/api/me", { method: "DELETE", body: { password } });
