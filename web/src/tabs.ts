export interface Tab {
  path: string;
  icon: string;
  label: string; // gíria em inglês, mostrada na aba
  pt: string; // nome em português, no tooltip e no título da seção
  tag: string; // adesivo ao lado do título
}

export const TABS: Tab[] = [
  { path: "/estudar", icon: "🔒", label: "Lock In", pt: "Estudar", tag: "bro is locked in" },
  { path: "/falar", icon: "🎤", label: "Mic Check", pt: "Falar", tag: "run it back" },
  { path: "/minerar", icon: "✂️", label: "Clip It", pt: "Minerar", tag: "chat, is this real?" },
  { path: "/vault", icon: "🗂️", label: "The Vault", pt: "Cards", tag: "all the bars" },
  { path: "/diario", icon: "💬", label: "Daily Yap", pt: "Diário", tag: "what are you yapping about?" },
  { path: "/stats", icon: "📊", label: "Stats", pt: "Progresso", tag: "aura check" },
];
