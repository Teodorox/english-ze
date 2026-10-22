import { useCallback, useEffect, useState, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { getMe, logout } from "./api/auth";
import { ApiError, AUTH_REQUIRED_EVENT } from "./api/client";
import type { Me } from "./api/types";
import { Backdrop } from "./components/Backdrop";
import { Layout } from "./components/Layout";
import { Journal } from "./pages/Journal";
import { Login } from "./pages/Login";
import { Mine } from "./pages/Mine";
import { Onboarding } from "./pages/Onboarding";
import { Speak } from "./pages/Speak";
import { StatsPage } from "./pages/StatsPage";
import { Study } from "./pages/Study";
import { Today } from "./pages/Today";
import { Vault } from "./pages/Vault";
import { TABS, type Tab } from "./tabs";

// Uma tela por aba.
const PAGES: Record<string, ComponentType<{ tab: Tab }>> = {
  "/hoje": Today,
  "/estudar": Study,
  "/falar": Speak,
  "/minerar": Mine,
  "/vault": Vault,
  "/diario": Journal,
  "/stats": StatsPage,
};

type AuthState =
  | { status: "checking" }
  | { status: "login" }
  | { status: "offline" }
  | { status: "ready"; me: Me };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "checking" });

  const checkAuth = useCallback(async () => {
    try {
      setAuth({ status: "ready", me: await getMe() });
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
      <Screen
        auth={auth}
        onLogin={checkAuth}
        onLogout={handleLogout}
        onMeChange={(me) => setAuth({ status: "ready", me })}
      />
    </>
  );
}

interface ScreenProps {
  auth: AuthState;
  onLogin: () => void;
  onLogout: () => void;
  onMeChange: (me: Me) => void;
}

function Screen({ auth, onLogin, onLogout, onMeChange }: ScreenProps) {
  switch (auth.status) {
    case "checking":
      return null;
    case "login":
      return (
        <Login
          onSuccess={() => {
            // Entrou agora: começa pelo plano do dia, mesmo que a aba aberta no navegador fosse outra.
            window.history.replaceState(null, "", "/");
            onLogin();
          }}
        />
      );
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
      if (!auth.me.onboarded) return <Onboarding me={auth.me} onDone={onMeChange} />;
      return (
        <BrowserRouter>
          <Routes>
            <Route element={<Layout me={auth.me} onMeChange={onMeChange} onLogout={onLogout} />}>
              <Route index element={<Navigate to={TABS[0].path} replace />} />
              {TABS.map((tab) => {
                const Page = PAGES[tab.path];
                return Page && <Route key={tab.path} path={tab.path} element={<Page tab={tab} />} />;
              })}
              <Route path="*" element={<Navigate to={TABS[0].path} replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      );
  }
}
