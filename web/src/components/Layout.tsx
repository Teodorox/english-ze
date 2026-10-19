import { NavLink, Outlet } from "react-router";
import { TABS } from "../tabs";
import { Brand } from "./Brand";

interface LayoutProps {
  showLogout: boolean;
  onLogout: () => void;
}

export function Layout({ showLogout, onLogout }: LayoutProps) {
  return (
    <>
      <header className="topbar">
        <div className="brand">
          <Brand />
          {showLogout && (
            <button className="logout" title="Sair" onClick={onLogout}>
              Sair
            </button>
          )}
        </div>
        <nav className="tabs">
          {TABS.map((tab) => (
            <NavLink key={tab.path} to={tab.path} title={tab.pt}>
              <span className="icon">{tab.icon}</span>
              <span className="label">{tab.label}</span>
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </>
  );
}
