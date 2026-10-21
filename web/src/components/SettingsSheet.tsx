import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { changePassword, deleteAccount, logoutOtherDevices, updateMe } from "../api/auth";
import { ApiError } from "../api/client";
import type { Me } from "../api/types";
import { goalsSummary, levelLabel, type DailyMinutes, type Goal, type Level } from "../lib/studyProfile";
import { loadThemePref, setThemePref, type ThemePref } from "../lib/theme";
import { SegmentedControl } from "./SegmentedControl";
import { GoalPicker, LevelPicker, MinutesPicker } from "./StudyPickers";

const PASSWORD_MIN = 8;

interface SettingsSheetProps {
  open: boolean;
  onClose: () => void;
  me: Me;
  onMeChange: (me: Me) => void;
  onLogout: () => void;
}

/** Telas dentro da folha, como a navegação dos Ajustes do iPhone. */
type View = "main" | "name" | "password" | "delete" | "goals" | "level" | "minutes";

const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Sem conexão com o servidor.");

/** Folha de ajustes que sobe de baixo, no estilo iOS. Usa <dialog>: fecha com Esc e prende o foco. */
export function SettingsSheet({ open, onClose, me, onMeChange, onLogout }: SettingsSheetProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [theme, setTheme] = useState<ThemePref>(loadThemePref);
  const [view, setView] = useState<View>("main");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    if (!open) {
      setView("main"); // reabre sempre no começo
      setNotice("");
    }
  }, [open]);

  function changeTheme(value: ThemePref) {
    setTheme(value);
    setThemePref(value);
  }

  function back(message = "") {
    setView("main");
    setNotice(message);
  }

  return (
    <dialog
      ref={dialogRef}
      className="sheet glass"
      aria-labelledby="settings-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose(); // toque fora da folha fecha
      }}
    >
      <div className="sheet-handle" aria-hidden="true" />

      {view === "main" && (
        <>
          <div className="sheet-head">
            <h2 id="settings-title">Ajustes</h2>
            <button type="button" className="small" onClick={onClose}>
              OK
            </button>
          </div>
          {notice && (
            <p className="login-success settings-notice" role="status">
              {notice}
            </p>
          )}

          <h3 className="section-header">Conta</h3>
          <div className="settings-group">
            <div className="account-row">
              <span className="avatar" aria-hidden="true">
                {me.name.trim().charAt(0).toUpperCase() || "?"}
              </span>
              <span className="account-text">
                <strong>{me.name}</strong>
                <span>{me.email}</span>
              </span>
            </div>
            <GroupButton onClick={() => setView("name")}>Mudar nome</GroupButton>
            <GroupButton onClick={() => setView("password")}>Trocar senha</GroupButton>
            <OtherDevicesButton onDone={setNotice} />
          </div>

          <h3 className="section-header">Meu estudo</h3>
          <div className="settings-group">
            <GroupButton onClick={() => setView("goals")} detail={goalsSummary(me.goals) || "Escolher"}>
              Objetivos
            </GroupButton>
            <GroupButton onClick={() => setView("level")} detail={levelLabel(me.level)}>
              Nível
            </GroupButton>
            <GroupButton onClick={() => setView("minutes")} detail={`${me.daily_minutes} min`}>
              Tempo por dia
            </GroupButton>
          </div>

          <h3 className="section-header">Aparência</h3>
          <SegmentedControl
            label="Aparência"
            value={theme}
            onChange={changeTheme}
            options={[
              { value: "system", label: "Automático" },
              { value: "light", label: "Claro" },
              { value: "dark", label: "Escuro" },
            ]}
          />
          <p className="footnote sheet-hint">Automático segue o tema do seu celular ou computador.</p>

          <button type="button" className="destructive-text" onClick={onLogout}>
            Sair
          </button>
          <button type="button" className="link-button settings-delete" onClick={() => setView("delete")}>
            Apagar minha conta
          </button>
        </>
      )}

      {view === "name" && <NameForm me={me} onBack={back} onSaved={onMeChange} />}
      {view === "password" && <PasswordForm onBack={back} />}
      {view === "delete" && <DeleteForm onBack={back} onDeleted={onLogout} />}
      {(view === "goals" || view === "level" || view === "minutes") && (
        <StudyForm field={view} me={me} onBack={back} onSaved={onMeChange} />
      )}
    </dialog>
  );
}

function GroupButton({
  onClick,
  children,
  detail,
}: {
  onClick: () => void;
  children: ReactNode;
  detail?: string;
}) {
  return (
    <button type="button" className="group-button" onClick={onClick}>
      {children}
      <span className="group-detail">
        {detail && <span className="group-value">{detail}</span>}
        <span className="chevron" aria-hidden="true">
          ›
        </span>
      </span>
    </button>
  );
}

const STUDY_TITLES = { goals: "Objetivos", level: "Nível", minutes: "Tempo por dia" } as const;

/** Muda uma resposta do primeiro acesso (objetivos, nível ou tempo por dia). */
function StudyForm({
  field,
  me,
  onBack,
  onSaved,
}: {
  field: keyof typeof STUDY_TITLES;
  me: Me;
  onBack: (msg?: string) => void;
  onSaved: (me: Me) => void;
}) {
  const [goals, setGoals] = useState<Goal[]>(me.goals);
  const [level, setLevel] = useState<Level | null>(me.level);
  const [minutes, setMinutes] = useState<DailyMinutes>(me.daily_minutes);
  const form = useFormState();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    form.run(async () => {
      const changes =
        field === "goals" ? { goals } : field === "level" ? { level: level ?? undefined } : { daily_minutes: minutes };
      onSaved(await updateMe(changes));
      onBack(`${STUDY_TITLES[field]} atualizado.`);
    });
  }

  const ready = field === "goals" ? goals.length > 0 : field === "level" ? level !== null : true;
  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <SubHead title={STUDY_TITLES[field]} onBack={() => onBack()} />
      {field === "goals" && <GoalPicker value={goals} onChange={setGoals} />}
      {field === "level" && <LevelPicker value={level} onChange={setLevel} />}
      {field === "minutes" && <MinutesPicker value={minutes} onChange={setMinutes} />}
      <button type="submit" className="primary" disabled={form.sending || !ready}>
        {form.sending ? "Salvando..." : "Salvar"}
      </button>
      <p className="login-error" role="alert">
        {form.error}
      </p>
    </form>
  );
}

function OtherDevicesButton({ onDone }: { onDone: (message: string) => void }) {
  const [sending, setSending] = useState(false);

  async function handleClick() {
    setSending(true);
    try {
      const { ended } = await logoutOtherDevices();
      onDone(
        ended === 0
          ? "Nenhum outro aparelho estava conectado."
          : `${ended} ${ended === 1 ? "aparelho desconectado" : "aparelhos desconectados"}. Este continua conectado.`,
      );
    } catch (err) {
      onDone(errorMessage(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <button type="button" className="group-button" disabled={sending} onClick={handleClick}>
      {sending ? "Desconectando..." : "Sair dos outros aparelhos"}
    </button>
  );
}

/** Cabeçalho das telas internas: "‹ Ajustes" volta. */
function SubHead({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="sheet-head sheet-subhead">
      <button type="button" className="link-button back-button" onClick={onBack}>
        ‹ Ajustes
      </button>
      <h2 id="settings-title">{title}</h2>
      <span className="sheet-head-spacer" aria-hidden="true" />
    </div>
  );
}

interface FormState {
  sending: boolean;
  error: string;
}

function useFormState() {
  const [state, setState] = useState<FormState>({ sending: false, error: "" });
  async function run(action: () => Promise<void>) {
    setState({ sending: true, error: "" });
    try {
      await action();
      setState({ sending: false, error: "" });
    } catch (err) {
      setState({ sending: false, error: errorMessage(err) });
    }
  }
  return { ...state, run, setError: (error: string) => setState({ sending: false, error }) };
}

function NameForm({ me, onBack, onSaved }: { me: Me; onBack: (msg?: string) => void; onSaved: (me: Me) => void }) {
  const [name, setName] = useState(me.name);
  const form = useFormState();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    form.run(async () => {
      onSaved(await updateMe({ name }));
      onBack("Nome atualizado.");
    });
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <SubHead title="Nome" onBack={() => onBack()} />
      <label className="field">
        Como quer ser chamado
        <input required autoFocus maxLength={60} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <button type="submit" className="primary" disabled={form.sending || !name.trim()}>
        {form.sending ? "Salvando..." : "Salvar"}
      </button>
      <p className="login-error" role="alert">
        {form.error}
      </p>
    </form>
  );
}

function PasswordForm({ onBack }: { onBack: (msg?: string) => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const form = useFormState();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (next !== repeat) {
      form.setError("A nova senha e a repetição não conferem.");
      return;
    }
    form.run(async () => {
      await changePassword(current, next);
      onBack("Senha trocada. Os outros aparelhos foram desconectados; este continua.");
    });
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <SubHead title="Trocar senha" onBack={() => onBack()} />
      <label className="field">
        Senha atual
        <input type="password" required autoFocus maxLength={200} autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </label>
      <label className="field">
        Nova senha
        <input type="password" required minLength={PASSWORD_MIN} maxLength={200} autoComplete="new-password" placeholder={`Pelo menos ${PASSWORD_MIN} caracteres`} value={next} onChange={(e) => setNext(e.target.value)} />
      </label>
      <label className="field">
        Repita a nova senha
        <input type="password" required minLength={PASSWORD_MIN} maxLength={200} autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} />
      </label>
      <button type="submit" className="primary" disabled={form.sending}>
        {form.sending ? "Trocando..." : "Trocar senha"}
      </button>
      <p className="login-error" role="alert">
        {form.error}
      </p>
    </form>
  );
}

function DeleteForm({ onBack, onDeleted }: { onBack: (msg?: string) => void; onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const form = useFormState();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    form.run(async () => {
      await deleteAccount(password);
      onDeleted();
    });
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <SubHead title="Apagar conta" onBack={() => onBack()} />
      <div className="delete-warning" role="note">
        <strong>Isso não tem volta.</strong>
        <p>
          Apaga de vez a sua conta e tudo dela: cards, progresso, revisões, sequência de dias e diário. Ninguém consegue
          recuperar depois, nem quem cuida do app.
        </p>
      </div>
      <label className="field">
        Digite sua senha pra confirmar
        <input type="password" required autoFocus maxLength={200} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      <button type="submit" className="destructive-fill" disabled={form.sending || !password}>
        {form.sending ? "Apagando..." : "Apagar minha conta"}
      </button>
      <button type="button" onClick={() => onBack()}>
        Cancelar
      </button>
      <p className="login-error" role="alert">
        {form.error}
      </p>
    </form>
  );
}
