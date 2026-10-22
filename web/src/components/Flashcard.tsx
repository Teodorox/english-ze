import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { Card, Grade } from "../api/types";
import {
  checkDictation,
  checkTranslation,
  gradeFor,
  shuffledOptions,
  stageFor,
  type Stage,
  type StudyMode,
  type Verdict,
} from "../lib/activeStudy";
import type { WordResult } from "../lib/pronunciation";
import { GradeButtons } from "./GradeButtons";
import { HeadphonesIcon } from "./icons";
import { SpeakButton } from "./SpeakButton";

export type { StudyMode };

interface FlashcardProps {
  card: Card;
  mode: StudyMode;
  /** "Só mostrar a resposta": o jeito rápido, com os 4 botões de nota. */
  revealed: boolean;
  onReveal: () => void;
  onGrade: (grade: Grade) => void;
}

const STAGE_LABEL: Record<Stage, string> = {
  intro: "Conhecer",
  choice: "Escolha",
  type: "Traduza",
  dictation: "Ditado",
};

const VERDICT_TEXT: Record<Verdict, string> = {
  right: "Certo! 🔥",
  close: "Quase! 👀",
  wrong: "Não foi dessa vez 💪",
};

interface Result {
  verdict: Verdict;
  typed: string;
  words?: WordResult[];
}

/** Um card da sessão. A tela Estudar troca a key a cada card, então tudo aqui começa do zero. */
export function Flashcard({ card, mode, revealed, onReveal, onGrade }: FlashcardProps) {
  const stage = stageFor(card, mode);
  const isNew = !card.introduced_on;
  const showSource = card.source && card.source !== "deck inicial";
  const options = useMemo(() => shuffledOptions(card), [card]);
  const [picked, setPicked] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  const answered = revealed || picked !== null || result !== null || stage === "intro";
  const hideFront = mode === "listen" && !answered;

  // Opções: teclas 1–4 escolhem (antes de responder).
  useEffect(() => {
    if (stage !== "choice" || answered) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLElement && e.target.closest("input, textarea, select")) return;
      const option = options[Number(e.key) - 1];
      if (option) setPicked(option);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [stage, answered, options]);

  function check(e: FormEvent) {
    e.preventDefault();
    if (!typed.trim()) return;
    if (stage === "dictation") {
      const { verdict, words } = checkDictation(typed, card.front);
      setResult({ verdict, typed, words });
    } else {
      setResult({ verdict: checkTranslation(typed, card.back).verdict, typed });
    }
  }

  const answer = (
    <div className="flashcard-answer">
      <p className="flashcard-back">{card.back}</p>
      {card.note && <p className="flashcard-note">{card.note}</p>}
      {showSource && <p className="footnote">Fonte: {card.source}</p>}
    </div>
  );

  let body;
  if (revealed) {
    body = (
      <>
        {answer}
        <GradeButtons card={card} onGrade={onGrade} />
      </>
    );
  } else if (stage === "intro") {
    body = (
      <>
        {answer}
        <p className="footnote">Frase nova: leia, ouça e entenda. Na próxima vez você responde.</p>
        <button type="button" className="primary" autoFocus onClick={() => onGrade(2)}>
          Entendi
        </button>
      </>
    );
  } else if (stage === "choice") {
    const right = picked === card.back;
    body = (
      <>
        <p className="exercise-prompt" id={`prompt-${card.id}`}>
          Qual é a tradução?
        </p>
        <div className="choices" role="group" aria-labelledby={`prompt-${card.id}`}>
          {options.map((option, i) => {
            const state =
              picked === null ? "" : option === card.back ? " right" : option === picked ? " wrong" : " faded";
            return (
              <button
                key={option}
                type="button"
                className={`choice-option${state}`}
                disabled={picked !== null}
                onClick={() => setPicked(option)}
              >
                <kbd className="desktop-only">{i + 1}</kbd>
                <span>{option}</span>
              </button>
            );
          })}
        </div>
        {picked !== null && (
          <>
            <p className={`verdict ${right ? "right" : "wrong"}`} role="status">
              {right ? VERDICT_TEXT.right : `${VERDICT_TEXT.wrong} A certa está em verde.`}
            </p>
            {card.note && <p className="flashcard-note">{card.note}</p>}
            <button type="button" className="primary" autoFocus onClick={() => onGrade(right ? 2 : 0)}>
              Continuar
            </button>
          </>
        )}
      </>
    );
  } else if (!result) {
    const dictation = stage === "dictation";
    body = (
      <form className="exercise-form" onSubmit={check}>
        <label className="exercise-prompt" htmlFor={`answer-${card.id}`}>
          {dictation ? "Escreva em inglês o que você ouviu" : "Como se diz em português?"}
        </label>
        <input
          id={`answer-${card.id}`}
          lang={dictation ? "en" : "pt-BR"}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          maxLength={500}
          autoFocus
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder={dictation ? "Ouça quantas vezes quiser" : "Escreva do seu jeito"}
        />
        <button type="submit" className="primary" disabled={!typed.trim()}>
          Conferir
        </button>
      </form>
    );
  } else {
    body = (
      <>
        <p className={`verdict ${result.verdict}`} role="status">
          {VERDICT_TEXT[result.verdict]}
        </p>
        {result.words ? (
          <div className="word-chips" lang="en" aria-label="Palavras da frase">
            {result.words.map((w, i) => (
              <span key={`${w.word}-${i}`} className={`word-chip ${w.ok ? "ok" : "miss"}`}>
                {w.word}
              </span>
            ))}
          </div>
        ) : (
          <p className="footnote">Você escreveu: “{result.typed}”</p>
        )}
        {answer}
        <div className="exercise-actions">
          <button type="button" className="primary" autoFocus onClick={() => onGrade(gradeFor(result.verdict))}>
            Continuar
          </button>
          {result.verdict !== "right" && (
            <button type="button" onClick={() => onGrade(2)}>
              Eu estava certo
            </button>
          )}
        </div>
      </>
    );
  }

  return (
    <article className="glass card flashcard" aria-live="polite">
      <div className="flashcard-pills">
        <span className={`pill ${isNew ? "tint" : "gray"}`}>{isNew ? "Novo" : "Revisão"}</span>
        <span className="pill gray">{STAGE_LABEL[stage]}</span>
        <span className="pill gray">{card.category}</span>
      </div>

      {hideFront ? (
        <p className="flashcard-front listening">
          <HeadphonesIcon />
          Ouça e escreva
        </p>
      ) : (
        <p className="flashcard-front" lang="en">
          {card.front}
        </p>
      )}

      <div className="flashcard-audio">
        <SpeakButton text={card.front} label="Ouvir" className="tinted small" />
        <SpeakButton text={card.front} label="Devagar" rate={0.7} slow className="small" />
      </div>

      {body}

      {!answered && (
        <button type="button" className="link-button" onClick={onReveal}>
          Só mostrar a resposta
        </button>
      )}
    </article>
  );
}
