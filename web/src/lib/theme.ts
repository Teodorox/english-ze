// Tema do app: Automático (segue o aparelho), Claro ou Escuro.
// O public/theme-boot.js aplica o tema antes do app carregar, pra não piscar a cor errada.
import { loadPref, savePref } from "./storage";

export type ThemePref = "system" | "light" | "dark";
export type Theme = "light" | "dark";

const KEY = "theme";
const THEME_COLORS: Record<Theme, string> = { light: "#f2f2f7", dark: "#000000" };
const darkQuery = () => window.matchMedia("(prefers-color-scheme: dark)");

export function resolveTheme(pref: ThemePref, systemIsDark: boolean): Theme {
  if (pref === "system") return systemIsDark ? "dark" : "light";
  return pref;
}

export function loadThemePref(): ThemePref {
  const pref = loadPref<string>(KEY, "system");
  return pref === "light" || pref === "dark" ? pref : "system";
}

export function applyTheme(pref: ThemePref): void {
  const theme = resolveTheme(pref, darkQuery().matches);
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", THEME_COLORS[theme]);
}

export function setThemePref(pref: ThemePref): void {
  savePref(KEY, pref);
  applyTheme(pref);
}

/** Aplica o tema salvo e acompanha o aparelho quando estiver em Automático. */
export function initTheme(): void {
  applyTheme(loadThemePref());
  darkQuery().addEventListener("change", () => {
    if (loadThemePref() === "system") applyTheme("system");
  });
}
