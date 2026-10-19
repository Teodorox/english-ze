import type { Card } from "../api/types";
import { HeadphonesIcon } from "./icons";
import { SpeakButton } from "./SpeakButton";

export type StudyMode = "read" | "listen";

interface FlashcardProps {
  card: Card;
  mode: StudyMode;
  revealed: boolean;
  onReveal: () => void;
}

export function Flashcard({ card, mode, revealed, onReveal }: FlashcardProps) {
  const isNew = !card.introduced_on;
  const hideFront = mode === "listen" && !revealed;
  const showSource = card.source && card.source !== "deck inicial";

  return (
    <article className="glass card flashcard" aria-live="polite">
      <div className="flashcard-pills">
        <span className={`pill ${isNew ? "tint" : "gray"}`}>{isNew ? "Novo" : "Revisão"}</span>
        <span className="pill gray">{card.category}</span>
      </div>

      {hideFront ? (
        <p className="flashcard-front listening">
          <HeadphonesIcon />
          Ouça e tente entender
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

      {revealed ? (
        <div className="flashcard-answer">
          <p className="flashcard-back">{card.back}</p>
          {card.note && <p className="flashcard-note">{card.note}</p>}
          {showSource && <p className="footnote">Fonte: {card.source}</p>}
        </div>
      ) : (
        <button type="button" className="primary flashcard-reveal" onClick={onReveal}>
          Mostrar resposta
        </button>
      )}
    </article>
  );
}
