import type { ComponentType, SVGProps } from "react";
import { ArchiveIcon, BubbleIcon, ChartIcon, LockIcon, MicIcon, ScissorsIcon } from "./components/icons";

export interface Tab {
  path: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string; // gíria em inglês: título grande da tela
  short: string; // nome curto na barra de abas
  pt: string; // nome em português: subtítulo e nome acessível
}

export const TABS: Tab[] = [
  { path: "/estudar", Icon: LockIcon, title: "Lock In", short: "Lock In", pt: "Estudar" },
  { path: "/falar", Icon: MicIcon, title: "Mic Check", short: "Mic", pt: "Falar" },
  { path: "/minerar", Icon: ScissorsIcon, title: "Clip It", short: "Clip", pt: "Minerar frases" },
  { path: "/vault", Icon: ArchiveIcon, title: "The Vault", short: "Vault", pt: "Seus cards" },
  { path: "/diario", Icon: BubbleIcon, title: "Daily Yap", short: "Yap", pt: "Diário" },
  { path: "/stats", Icon: ChartIcon, title: "Stats", short: "Stats", pt: "Progresso" },
];
