import { NavLink, Outlet } from "react-router";
import { TABS } from "../tabs";
import { LogoutIcon } from "./icons";

interface LayoutProps {
  showLogout: boolean;
  onLogout: () => void;
}

export function Layout({ showLogout, onLogout }: LayoutProps) {
  return (
    <>
      <main className="page">
        <div className="toolbar-top">
          {showLogout && (
            <button className="icon glass" aria-label="Sair" title="Sair" onClick={onLogout}>
              <LogoutIcon />
            </button>
          )}
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
    </>
  );
}
