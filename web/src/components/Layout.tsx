import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { TABS } from "../tabs";
import { GearIcon } from "./icons";
import { SettingsSheet } from "./SettingsSheet";

interface LayoutProps {
  showLogout: boolean;
  onLogout: () => void;
}

export function Layout({ showLogout, onLogout }: LayoutProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <main className="page">
        <div className="toolbar-top">
          <button className="icon glass" aria-label="Ajustes" title="Ajustes" onClick={() => setSettingsOpen(true)}>
            <GearIcon />
          </button>
        </div>
        <Outlet />
      </main>
      <nav className="tabbar glass" aria-label="Abas">
        {TABS.map(({ path, Icon, short, pt }) => (
          <NavLink key={path} to={path} aria-label={pt} title={pt}>
            <Icon />
            {short}
          </NavLink>
        ))}
      </nav>
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
