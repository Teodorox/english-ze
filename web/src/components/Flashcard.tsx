import type { Card } from "../api/types";
import { speak } from "../lib/tts";
import { HeadphonesIcon, PlayIcon, SlowIcon } from "./icons";

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
        <button type="button" className="tinted small" onClick={() => speak(card.front)}>
          <PlayIcon width={15} height={15} />
          Ouvir
        </button>
        <button type="button" className="small" onClick={() => speak(card.front, 0.7)}>
          <SlowIcon width={15} height={15} />
          Devagar
        </button>
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
