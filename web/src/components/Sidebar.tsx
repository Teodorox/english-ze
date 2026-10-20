import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router";
import { getStats } from "../api/stats";
import { PROGRESS_EVENT } from "../api/study";
import type { Stats } from "../api/types";
import { fraction } from "../lib/stats";
import { loadPref } from "../lib/storage";
import { TABS } from "../tabs";
import { ActivityRings } from "./ActivityRings";
import { GearIcon } from "./icons";

/** Navegação do computador: barra lateral de vidro, como no Apple Music e nos Ajustes do Mac. */
export function Sidebar({ onOpenSettings }: { onOpenSettings: () => void }) {
  return (
    <nav className="sidebar glass" aria-label="Abas">
      <div className="sidebar-brand">
        <span className="sidebar-logo" aria-hidden="true">
          Ze
        </span>
        English Ze
      </div>
      {TABS.map(({ path, Icon, title, pt }) => (
        <NavLink key={path} to={path} className="sidebar-link">
          <Icon />
          {title}
          <span className="sidebar-pt">{pt}</span>
        </NavLink>
      ))}
      <div className="sidebar-bottom">
        <DailyGoal />
        <button type="button" className="sidebar-link" onClick={onOpenSettings}>
          <GearIcon />
          Ajustes
        </button>
      </div>
    </nav>
  );
}

/** Meta do dia (a mesma da aba Stats) e a sequência, sempre à vista. */
function DailyGoal() {
  const [stats, setStats] = useState<Stats | null>(null);
  const { pathname } = useLocation();

  // Atualiza ao trocar de aba, a cada avaliação salva e quando a meta muda.
  useEffect(() => {
    const refresh = () => getStats().then(setStats).catch(() => {});
    refresh();
    window.addEventListener(PROGRESS_EVENT, refresh);
    return () => window.removeEventListener(PROGRESS_EVENT, refresh);
  }, [pathname]);

  if (!stats) return null;
  const goal = loadPref("dailyGoal", 20);
  const days = stats.streak === 1 ? "dia seguido" : "dias seguidos";
  return (
    <div className="sidebar-goal">
      <ActivityRings
        size={44}
        label={`Meta do dia: ${stats.reviews_today} de ${goal} revisões.`}
        rings={[{ fraction: fraction(stats.reviews_today, goal), color: "var(--pink)" }]}
      />
      <div>
        <strong>Meta de hoje</strong>
        <span>
          {stats.reviews_today} de {goal} revisões
        </span>
        <span>
          {stats.streak} {days}
        </span>
      </div>
    </div>
  );
}
