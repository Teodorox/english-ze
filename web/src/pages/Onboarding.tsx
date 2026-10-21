import { useState } from "react";
import { completeOnboarding } from "../api/auth";
import { ApiError } from "../api/client";
import type { Me } from "../api/types";
import { GoalPicker, LevelPicker, MinutesPicker } from "../components/StudyPickers";
import { ZeIcon } from "../components/ZeIcon";
import { firstName } from "../lib/greeting";
import type { DailyMinutes, Goal, Level } from "../lib/studyProfile";

const QUESTIONS = 3;

/** Primeiro acesso: boas-vindas e 3 perguntas (objetivos, nível e tempo por dia). */
export function Onboarding({ me, onDone }: { me: Me; onDone: (me: Me) => void }) {
  const [step, setStep] = useState(0);
  const [goals, setGoals] = useState<Goal[]>(me.goals);
  const [level, setLevel] = useState<Level | null>(me.level);
  const [minutes, setMinutes] = useState<DailyMinutes | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  async function finish() {
    if (!level || !minutes) return;
    setSending(true);
    setError("");
    try {
      onDone(await completeOnboarding({ goals, level, daily_minutes: minutes }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sem conexão com o servidor.");
      setSending(false);
    }
  }

  if (step === 0) {
    const name = firstName(me.name);
    return (
      <main className="login-wrap onboarding">
        <div className="app-icon" aria-hidden="true">
          <ZeIcon />
        </div>
        <h1 className="large-title">{name ? `Olá, ${name}!` : "Olá!"}</h1>
        <p className="subtitle onboarding-lede">
          Boas-vindas ao English Zé! Eu sou o Zé. Antes de começar, 3 perguntas rápidas pra montar o seu plano de
          estudo.
        </p>
        <button type="button" className="primary onboarding-next" autoFocus onClick={() => setStep(1)}>
          Bora!
        </button>
      </main>
    );
  }

  const ready = step === 1 ? goals.length > 0 : step === 2 ? level !== null : minutes !== null;
  const last = step === QUESTIONS;

  return (
    <main className="login-wrap onboarding">
      <div className="onboarding-top">
        <button type="button" className="link-button back-button" onClick={() => setStep(step - 1)}>
          ‹ Voltar
        </button>
        <span className="onboarding-step" aria-label={`Pergunta ${step} de ${QUESTIONS}`}>
          {Array.from({ length: QUESTIONS }, (_, i) => (
            <i key={i} className={i < step ? "done" : ""} />
          ))}
        </span>
      </div>

      {step === 1 && (
        <>
          <h1 className="onboarding-title">Pra que você quer inglês?</h1>
          <p className="subtitle onboarding-lede">Pode marcar mais de um.</p>
          <GoalPicker value={goals} onChange={setGoals} />
        </>
      )}
      {step === 2 && (
        <>
          <h1 className="onboarding-title">Como está seu inglês hoje?</h1>
          <p className="subtitle onboarding-lede">Sem pressão: o app ajusta conforme você estuda.</p>
          <LevelPicker value={level} onChange={setLevel} />
        </>
      )}
      {step === 3 && (
        <>
          <h1 className="onboarding-title">Quanto tempo por dia?</h1>
          <p className="subtitle onboarding-lede">Dá pra mudar depois nos Ajustes.</p>
          <MinutesPicker value={minutes} onChange={setMinutes} />
        </>
      )}

      <button
        type="button"
        className="primary onboarding-next"
        disabled={!ready || sending}
        onClick={last ? finish : () => setStep(step + 1)}
      >
        {last ? (sending ? "Montando..." : "Montar meu plano") : "Continuar"}
      </button>
      <p className="login-error" role="alert">
        {error}
      </p>
    </main>
  );
}
