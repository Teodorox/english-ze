import { useSyncExternalStore } from "react";

/** Largura a partir da qual o app usa o layout de computador (barra lateral, colunas). */
export const DESKTOP_QUERY = "(min-width: 1024px)";

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
  );
}
