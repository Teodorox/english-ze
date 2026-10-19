/** Prompt pra colar numa IA gratuita quando a correção automática não está configurada. */
export function correctionPrompt(text: string): string {
  return [
    "Sou brasileiro e estou no nível iniciante de inglês. Corrija o texto abaixo:",
    "1) Mostre a versão corrigida.",
    "2) Liste cada erro com uma explicação curta em português.",
    "3) Mostre como um americano diria isso de um jeito natural e informal.",
    "",
    "Texto:",
    text.trim(),
  ].join("\n");
}

/** Copia texto pra área de transferência. Devolve false se o navegador não deixar. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
