import { createContext, useContext } from "react";
import type { Me } from "../api/types";

/** Quem está logado, disponível pras telas sem passar de mão em mão. */
export const MeContext = createContext<Me | null>(null);

export function useMe(): Me | null {
  return useContext(MeContext);
}
