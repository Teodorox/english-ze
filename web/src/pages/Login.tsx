import { useState, type FormEvent } from "react";
import { login } from "../api/auth";
import { ApiError } from "../api/client";
import { Brand } from "../components/Brand";

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError("");
    try {
      await login(password);
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão com o servidor.");
      setPassword("");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="login-wrap">
      <div className="login-brand">
        <Brand />
      </div>
      <form className="card form" onSubmit={handleSubmit}>
        <span className="tag">pull up, bro</span>
        <label>
          Senha
          <input
            type="password"
            required
            autoFocus
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="primary" disabled={sending}>
          {sending ? "Entrando..." : "Entrar"}
        </button>
        <p className="login-status muted" role="alert">
          {error && `⚠️ ${error}`}
        </p>
      </form>
    </main>
  );
}
