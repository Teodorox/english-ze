import { useState, type FormEvent } from "react";
import { login } from "../api/auth";
import { ApiError } from "../api/client";

const SLANG = ["no cap", "W", "let him cook", "bet"];

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
      <div className="app-icon" aria-hidden="true">
        Ze
      </div>
      <h1 className="large-title">English Ze</h1>
      <p className="subtitle" style={{ marginBottom: 0 }}>
        Inglês de verdade, do jeito que a internet fala.
      </p>
      <div className="login-slang" aria-hidden="true">
        {SLANG.map((word) => (
          <span key={word} className="pill tint">
            {word}
          </span>
        ))}
      </div>
      <form className="login-card glass card" onSubmit={handleSubmit}>
        <label className="field">
          Senha
          <input
            type="password"
            required
            autoFocus
            autoComplete="current-password"
            placeholder="Digite sua senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="primary" disabled={sending}>
          {sending ? "Entrando..." : "Entrar"}
        </button>
        <p className="login-error" role="alert">
          {error}
        </p>
      </form>
    </main>
  );
}
