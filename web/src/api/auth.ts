import { api } from "./client";
import type { AuthStatus } from "./types";

export const getAuthStatus = () => api<AuthStatus>("/api/auth/status");

export const login = (password: string) => api<{ ok: true }>("/api/login", { method: "POST", body: { password } });

export const logout = () => api<{ ok: true }>("/api/logout", { method: "POST" });
