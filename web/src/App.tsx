import { useCallback, useEffect, useState, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { getAuthStatus, logout } from "./api/auth";
import { ApiError, AUTH_REQUIRED_EVENT } from "./api/client";
import { Backdrop } from "./components/Backdrop";
import { Layout } from "./components/Layout";
import { ComingSoon } from "./pages/ComingSoon";
import { Login } from "./pages/Login";
import { Study } from "./pages/Study";
import { TABS, type Tab } from "./tabs";

// Telas já migradas; as outras mostram "Em migração".
const PAGES: Record<string, ComponentType<{ tab: Tab }>> = {
  "/estudar": Study,
};

type AuthState =
  | { status: "checking" }
  | { status: "login" }
  | { status: "offline" }
  | { status: "ready"; loginEnabled: boolean };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "checking" });

  const checkAuth = useCallback(async () => {
    try {
      const { enabled } = await getAuthStatus();
      setAuth({ status: "ready", loginEnabled: enabled });
    } catch (err) {
      setAuth(err instanceof ApiError && err.status === 401 ? { status: "login" } : { status: "offline" });
    }
  }, []);

  useEffect(() => {
    checkAuth();
    const onAuthRequired = () => setAuth({ status: "login" });
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired);
  }, [checkAuth]);

  async function handleLogout() {
    await logout().catch(() => {});
    setAuth({ status: "login" });
  }

  return (
    <>
      <Backdrop />
      <Screen auth={auth} onLogin={checkAuth} onLogout={handleLogout} />
    </>
  );
}

interface ScreenProps {
  auth: AuthState;
  onLogin: () => void;
  onLogout: () => void;
}

function Screen({ auth, onLogin, onLogout }: ScreenProps) {
  switch (auth.status) {
    case "checking":
      return null;
    case "login":
      return <Login onSuccess={onLogin} />;
    case "offline":
      return (
        <main className="login-wrap">
          <div className="glass card" style={{ width: "100%" }}>
            <p style={{ marginTop: 0 }}>Não consegui falar com o servidor.</p>
            <button className="primary" onClick={onLogin}>
              Tentar de novo
            </button>
          </div>
        </main>
      );
    case "ready":
      return (
        <BrowserRouter>
          <Routes>
            <Route element={<Layout showLogout={auth.loginEnabled} onLogout={onLogout} />}>
              <Route index element={<Navigate to={TABS[0].path} replace />} />
              {TABS.map((tab) => {
                const Page = PAGES[tab.path] ?? ComingSoon;
                return <Route key={tab.path} path={tab.path} element={<Page tab={tab} />} />;
              })}
              <Route path="*" element={<Navigate to={TABS[0].path} replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      );
  }
}
