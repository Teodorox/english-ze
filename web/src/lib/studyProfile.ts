// Opções do perfil de estudo (primeiro acesso e Ajustes). As mesmas listas valem na API e no banco.

export type Goal = "streamers" | "conversar" | "trabalho" | "musica" | "viagem" | "series" | "provas";
export type Level = "iniciante" | "basico" | "intermediario";
export type DailyMinutes = 5 | 10 | 15 | 20 | 30;

export const GOALS: { id: Goal; emoji: string; label: string }[] = [
  { id: "streamers", emoji: "🎮", label: "Streamers e games" },
  { id: "conversar", emoji: "💬", label: "Conversar" },
  { id: "trabalho", emoji: "💼", label: "Trabalho" },
  { id: "musica", emoji: "🎵", label: "Música" },
  { id: "viagem", emoji: "✈️", label: "Viagem" },
  { id: "series", emoji: "🎬", label: "Séries e filmes" },
  { id: "provas", emoji: "🎓", label: "Provas e entrevistas" },
];

export const LEVELS: { id: Level; label: string; description: string }[] = [
  { id: "iniciante", label: "Estou começando", description: "Sei poucas palavras e quero o básico do básico." },
  { id: "basico", label: "Me viro", description: "Entendo frases simples, se falarem devagar." },
  { id: "intermediario", label: "Intermediário", description: "Converso, mas travo com fala rápida e gírias." },
];

// As frases novas por dia são as do NEW_PER_DAY em app/main.py (quem decide é o servidor).
export const MINUTES: { value: DailyMinutes; label: string; description: string }[] = [
  { value: 5, label: "5 min", description: "Rapidinho, pra não perder a sequência. 3 frases novas por dia." },
  { value: 10, label: "10 min", description: "Equilibrado. O recomendado. 5 frases novas por dia." },
  { value: 15, label: "15 min", description: "Puxado, pra evoluir mais rápido. 8 frases novas por dia." },
  { value: 20, label: "20 min", description: "Focado, pra quem leva a sério. 10 frases novas por dia." },
  { value: 30, label: "30 min", description: "Intensivo, pra quem tem tempo livre. 15 frases novas por dia." },
];

/** "Streamers e games, Música" (na ordem da lista, não na ordem em que a pessoa tocou). */
export function goalsSummary(goals: Goal[]): string {
  return GOALS.filter((g) => goals.includes(g.id))
    .map((g) => g.label)
    .join(", ");
}

export const levelLabel = (level: Level | null) => LEVELS.find((l) => l.id === level)?.label ?? "Não informado";

/** Marca ou desmarca um objetivo, mantendo a ordem da lista. */
export function toggleGoal(goals: Goal[], goal: Goal): Goal[] {
  const next = goals.includes(goal) ? goals.filter((g) => g !== goal) : [...goals, goal];
  return GOALS.map((g) => g.id).filter((id) => next.includes(id));
}
