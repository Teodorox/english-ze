/** Primeiro nome, pra falar com a pessoa ("José Teodoro" -> "José"). */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? "";
}

/** "Bom dia, José!" de acordo com a hora do aparelho; sem nome, só o cumprimento. */
export function greeting(name: string, hour: number = new Date().getHours()): string {
  const hello = hour >= 5 && hour < 12 ? "Bom dia" : hour >= 12 && hour < 18 ? "Boa tarde" : "Boa noite";
  const first = firstName(name);
  return first ? `${hello}, ${first}!` : `${hello}!`;
}
