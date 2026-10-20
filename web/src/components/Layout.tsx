import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { DESKTOP_QUERY, useMediaQuery } from "../lib/useMediaQuery";
import { TABS } from "../tabs";
import { GearIcon } from "./icons";
import { SettingsSheet } from "./SettingsSheet";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  showLogout: boolean;
  onLogout: () => void;
}

export function Layout({ showLogout, onLogout }: LayoutProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Computador: barra lateral. Celular e tablet: engrenagem no topo e barra de abas flutuante.
  const desktop = useMediaQuery(DESKTOP_QUERY);

  return (
    <>
      <div className="status-bar-blur" aria-hidden="true" />
      <div className="app-shell">
        {desktop && <Sidebar onOpenSettings={() => setSettingsOpen(true)} />}
        <main className="page">
          {!desktop && (
            <div className="toolbar-top">
              <button className="icon glass" aria-label="Ajustes" title="Ajustes" onClick={() => setSettingsOpen(true)}>
                <GearIcon />
              </button>
            </div>
          )}
          <Outlet />
        </main>
      </div>
      {!desktop && (
        <nav className="tabbar glass" aria-label="Abas">
          {TABS.map(({ path, Icon, short, pt }) => (
            <NavLink key={path} to={path} aria-label={pt} title={pt}>
              <Icon />
              {short}
            </NavLink>
          ))}
        </nav>
      )}
      <SettingsSheet
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        showLogout={showLogout}
        onLogout={() => {
          setSettingsOpen(false);
          onLogout();
        }}
      />
    </>
  );
}
