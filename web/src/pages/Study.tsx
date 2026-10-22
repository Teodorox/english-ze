import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { getSession, reviewCard } from "../api/study";
import type { Grade, Session } from "../api/types";
import { ChatFeed, useChatFeed } from "../components/ChatFeed";
import { Flashcard, type StudyMode } from "../components/Flashcard";
import { HeadphonesIcon } from "../components/icons";
import { LargeTitle } from "../components/LargeTitle";
import { LivePill } from "../components/LivePill";
import { useMe } from "../components/MeContext";
import { SegmentedControl } from "../components/SegmentedControl";
import { greeting } from "../lib/greeting";
import { loadPref, savePref } from "../lib/storage";
import { afterGrade, counts, requeue, reveal, startQueue, type QueueState } from "../lib/studyQueue";
import { speak } from "../lib/tts";
import type { Tab } from "../tabs";

const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Sem conexão com o servidor.");

export function Study({ tab }: { tab: Tab }) {
  const [mode, setMode] = useState<StudyMode>(() => loadPref("studyMode", "read"));
  const [state, setState] = useState<QueueState | null>(null);
  const [error, setError] = useState("");
  const chat = useChatFeed();
  const me = useMe();

  const [session, setSession] = useState<Session | null>(null);

  const loadSession = useCallback(async () => {
    setError("");
    try {
      const data = await getSession();
      setSession(data);
      setState(startQueue(data));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  // Mudou objetivos, nível ou tempo em Ajustes: o dia é montado de novo.
  const plan = me ? `${me.goals.join()}|${me.level}|${me.daily_minutes}` : "";
  useEffect(() => {
    loadSession();
  }, [loadSession, plan]);

  const current = state?.current ?? null;
  const revealed = state?.revealed ?? false;

  // No modo Ouvir, cada card novo na tela já toca sozinho.
  const turn = state ? `${current?.id}-${state.done}` : "";
  useEffect(() => {
    if (mode === "listen" && current && !revealed) speak(current.front);
  }, [turn, mode]); // de propósito: só quando muda o card ou o modo, não ao revelar

  const handleReveal = useCallback(() => setState((s) => s && reveal(s)), []);

  // Avança na hora e salva em segundo plano; se falhar, o card volta pra fila.
  const handleGrade = useCallback(
    (grade: Grade) => {
      if (!current) return;
      const card = current;
      setError("");
      setState((s) => s && afterGrade(s, grade));
      chat.pop(grade);
      reviewCard(card.id, grade, mode).catch((err) => {
        setError(`Não consegui salvar "${card.front}" (${errorMessage(err).replace(/\.$/, "")}). O card voltou pra fila.`);
        setState((s) => s && requeue(s, card));
      });
    },
    [current, chat, mode],
  );

  // Atalhos: R repete o áudio, S toca devagar e, depois de "Só mostrar a resposta", 1–4 avaliam.
  // Enter confirma pelo botão em foco; as opções (1–4) ficam no próprio card.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const target = e.target instanceof HTMLElement ? e.target : null;
      if (target?.closest("input, textarea, select")) return;
      if (revealed && ["1", "2", "3", "4"].includes(e.key)) {
        handleGrade((Number(e.key) - 1) as Grade);
      } else if (e.key.toLowerCase() === "r" && current) {
        speak(current.front);
      } else if (e.key.toLowerCase() === "s" && current) {
        speak(current.front, 0.7);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleGrade, current, revealed]);

  function changeMode(value: StudyMode) {
    setMode(value);
    savePref("studyMode", value);
  }

  const { remaining, newCount } = state ? counts(state) : { remaining: 0, newCount: 0 };
  const total = remaining + (state?.done ?? 0);
  const progress = total ? Math.round(((state?.done ?? 0) / total) * 100) : 0;

  // No celular as duas colunas (.study-main e .study-aside) somem e tudo fica numa coluna só.
  return (
    <section className="study-page">
      <LargeTitle tab={tab} accessory={<LivePill />} greeting={me ? greeting(me.name) : undefined} />

      <SegmentedControl
        label="Modo de estudo"
        value={mode}
        onChange={changeMode}
        options={[
          { value: "read", label: "Ler" },
          {
            value: "listen",
            label: (
              <>
                <HeadphonesIcon width={16} height={16} /> Ouvir
              </>
            ),
          },
        ]}
      />

      {state && current && (
        <div className="study-progress">
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Progresso da sessão"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <span className="footnote">
            {remaining} restantes · {newCount} novos
          </span>
        </div>
      )}

      {session?.held_back && (
        <p className="banner-info" role="status">
          {session.new_per_day
            ? `Hoje só ${session.new_per_day} frases novas: tem bastante revisão acumulada.`
            : "Hoje sem frases novas: primeiro vamos pôr as revisões em dia."}
        </p>
      )}

      {error && (
        <p className="banner-error" role="alert">
          {error}
        </p>
      )}

      <div className="study-main">
        {state &&
          (current ? (
            <>
              <Flashcard
                key={turn}
                card={current}
                mode={mode}
                revealed={revealed}
                onReveal={handleReveal}
                onGrade={handleGrade}
              />
            </>
          ) : (
            <div className="glass card study-done">
              <div className="study-done-emoji" aria-hidden="true">
                {state.done ? "🏆" : "😎"}
              </div>
              <h2>{state.done ? "That's a W" : "We're all caught up"}</h2>
              <p>{state.done ? `${state.done} revisões hoje. Bro is locked in.` : "Nada pra revisar agora."}</p>
              {session && session.due_total > session.due.length && (
                <p className="footnote">
                  Meta de hoje feita. As outras {session.due_total - session.due.length} revisões acumuladas ficam pra
                  amanhã.
                </p>
              )}
              <p className="footnote">Que tal minerar umas frases da próxima live ou fazer um shadowing rápido?</p>
            </div>
          ))}
      </div>

      <aside className="study-aside">
        {state && (
          <div className="glass card desktop-only session-summary">
            <h2 className="card-heading">Sessão de hoje</h2>
            <dl>
              <div>
                <dt>revisões</dt>
                <dd>{remaining - newCount}</dd>
              </div>
              <div>
                <dt>novos</dt>
                <dd className="tint">{newCount}</dd>
              </div>
              <div>
                <dt>feitos</dt>
                <dd className="green">{state.done}</dd>
              </div>
            </dl>
          </div>
        )}

        <div className="glass card desktop-only shortcuts">
          <h2 className="card-heading">Atalhos do teclado</h2>
          <dl>
            <div>
              <dt>Escolher opção</dt>
              <dd>
                <kbd>1</kbd>
                <kbd>2</kbd>
                <kbd>3</kbd>
                <kbd>4</kbd>
              </dd>
            </div>
            <div>
              <dt>Conferir e continuar</dt>
              <dd>
                <kbd>Enter</kbd>
              </dd>
            </div>
            <div>
              <dt>Avaliar (resposta rápida)</dt>
              <dd>
                <kbd>1</kbd>
                <kbd>2</kbd>
                <kbd>3</kbd>
                <kbd>4</kbd>
              </dd>
            </div>
            <div>
              <dt>Repetir o áudio</dt>
              <dd>
                <kbd>R</kbd>
              </dd>
            </div>
            <div>
              <dt>Ouvir devagar</dt>
              <dd>
                <kbd>S</kbd>
              </dd>
            </div>
          </dl>
        </div>
      </aside>

      <p className="hint">
        Atalhos: <kbd>1</kbd>–<kbd>4</kbd> escolhem a opção · <kbd>Enter</kbd> confere e continua · <kbd>R</kbd> repete o
        áudio
      </p>

      <ChatFeed messages={chat.messages} />
    </section>
  );
}
