import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { getAuthStatus, logout } from "./api/auth";
import { ApiError, AUTH_REQUIRED_EVENT } from "./api/client";
import { Layout } from "./components/Layout";
import { ComingSoon } from "./pages/ComingSoon";
import { Login } from "./pages/Login";
import { TABS } from "./tabs";

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

  switch (auth.status) {
    case "checking":
      return null;
    case "login":
      return <Login onSuccess={checkAuth} />;
    case "offline":
      return (
        <main className="login-wrap">
          <div className="card">
            <p>⚠️ Não consegui falar com o servidor.</p>
            <button className="primary" onClick={checkAuth}>
              Tentar de novo
            </button>
          </div>
        </main>
      );
    case "ready":
      return (
        <BrowserRouter>
          <Routes>
            <Route element={<Layout showLogout={auth.loginEnabled} onLogout={handleLogout} />}>
              <Route index element={<Navigate to={TABS[0].path} replace />} />
              {TABS.map((tab) => (
                <Route key={tab.path} path={tab.path} element={<ComingSoon tab={tab} />} />
              ))}
              <Route path="*" element={<Navigate to={TABS[0].path} replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      );
  }
}
