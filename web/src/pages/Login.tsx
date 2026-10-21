import { useState, type FormEvent } from "react";
import { login, signup } from "../api/auth";
import { ApiError } from "../api/client";
import { SegmentedControl } from "../components/SegmentedControl";
import { ZeIcon } from "../components/ZeIcon";

const SLANG = ["no cap", "W", "let him cook", "bet"];
const PASSWORD_MIN = 8;

type Mode = "login" | "signup";

/** Tela de entrada: entrar com e-mail e senha, ou criar conta com um código de convite. */
export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invite, setInvite] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [sending, setSending] = useState(false);

  function changeMode(value: Mode) {
    setMode(value);
    setError("");
    setNotice("");
    setPassword("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError("");
    setNotice("");
    try {
      if (mode === "login") {
        await login(email, password);
        onSuccess();
      } else {
        // Criar a conta não entra nela: volta pro "Entrar" com o e-mail preenchido.
        await signup({ name, email, password, invite });
        setMode("login");
        setPassword("");
        setInvite("");
        setShowPassword(false);
        setNotice("Conta criada! Agora entre com seu e-mail e senha.");
        requestAnimationFrame(() => document.getElementById("login-password")?.focus());
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão com o servidor.");
      if (mode === "login") setPassword("");
    } finally {
      setSending(false);
    }
  }

  const signingUp = mode === "signup";

  return (
    <main className="login-wrap">
      <div className="app-icon" aria-hidden="true">
        <ZeIcon />
      </div>
      <h1 className="large-title">English Zé</h1>
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
        {notice && (
          <p className="login-success" role="status">
            {notice}
          </p>
        )}
        <SegmentedControl
          label="Entrar ou criar conta"
          value={mode}
          onChange={changeMode}
          options={[
            { value: "login", label: "Entrar" },
            { value: "signup", label: "Criar conta" },
          ]}
        />

        {signingUp && (
          <>
            <label className="field">
              Código de convite
              <input
                required
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                maxLength={20}
                placeholder="ABCD-2345"
                value={invite}
                onChange={(e) => setInvite(e.target.value)}
              />
            </label>
            <label className="field">
              Nome
              <input
                required
                autoComplete="name"
                maxLength={60}
                placeholder="Como quer ser chamado"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          </>
        )}

        <label className="field">
          E-mail
          <input
            type="email"
            required
            autoFocus
            autoComplete={signingUp ? "email" : "username"}
            autoCapitalize="none"
            spellCheck={false}
            inputMode="email"
            maxLength={254}
            placeholder="voce@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <div className="field">
          <span className="field-row">
            <label htmlFor="login-password">Senha</label>
            <button
              type="button"
              className="link-button"
              aria-pressed={showPassword}
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          </span>
          <input
            id="login-password"
            type={showPassword ? "text" : "password"}
            required
            minLength={signingUp ? PASSWORD_MIN : undefined}
            maxLength={200}
            autoComplete={signingUp ? "new-password" : "current-password"}
            placeholder={signingUp ? `Pelo menos ${PASSWORD_MIN} caracteres` : "Sua senha"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {signingUp && <p className="footnote login-hint">Evite senhas óbvias, como 12345678 ou o seu nome.</p>}

        <button type="submit" className="primary" disabled={sending}>
          {sending ? (signingUp ? "Criando..." : "Entrando...") : signingUp ? "Criar conta" : "Entrar"}
        </button>
        <p className="login-error" role="alert">
          {error}
        </p>
        {!signingUp && (
          <p className="footnote login-hint">Esqueceu a senha? Fale com quem te convidou pra redefinir.</p>
        )}
      </form>
    </main>
  );
}
