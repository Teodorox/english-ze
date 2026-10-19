import type { Correction } from "../api/types";
import { speak } from "../lib/tts";
import { PlayIcon } from "./icons";

/** Correção da IA: texto corrigido, versão natural, erros e incentivo. */
export function CorrectionView({ correction }: { correction: Correction }) {
  const { corrected, natural, mistakes, encouragement } = correction;
  return (
    <div className="correction">
      <section>
        <h4>Corrigido</h4>
        <p lang="en">{corrected}</p>
      </section>

      <section>
        <h4>Como um americano diria</h4>
        <div className="correction-natural">
          <p lang="en">{natural}</p>
          <button type="button" className="icon tinted" aria-label="Ouvir a versão natural" onClick={() => speak(natural)}>
            <PlayIcon width={16} height={16} />
          </button>
        </div>
      </section>

      <section>
        <h4>{mistakes.length ? `Erros (${mistakes.length})` : "Erros"}</h4>
        {mistakes.length ? (
          <ul className="mistakes">
            {mistakes.map((m, i) => (
              <li key={i}>
                <span lang="en">
                  <s>{m.original}</s> → <strong>{m.correction}</strong>
                </span>
                <span className="footnote">{m.explanation}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>Zero erros. You ate that 🔥</p>
        )}
      </section>

      <p className="encouragement">{encouragement}</p>
    </div>
  );
}
