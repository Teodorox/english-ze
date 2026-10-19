import { api } from "./client";
import type { Stats } from "./types";

export const getStats = () => api<Stats>("/api/stats");
