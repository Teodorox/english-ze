import { api } from "./client";
import type { Me } from "./types";

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

export const updateMe = (changes: Partial<Pick<Me, "name" | "timezone" | "learner">>) =>
  api<Me>("/api/me", { method: "PATCH", body: changes });

export const changePassword = (current: string, next: string) =>
  api<{ ok: true }>("/api/me/password", { method: "POST", body: { current, new: next } });

export const logoutOtherDevices = () => api<{ ended: number }>("/api/me/logout-others", { method: "POST" });

/** Apaga a conta e tudo dela. Não tem volta. */
export const deleteAccount = (password: string) =>
  api<{ ok: true }>("/api/me", { method: "DELETE", body: { password } });
