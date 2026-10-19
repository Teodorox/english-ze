import type { Correction } from "../api/types";
import { SpeakButton } from "./SpeakButton";

/** Correção da IA em blocos com cores próprias: corrigido (verde), natural (roxo) e erros. */
export function CorrectionView({ correction }: { correction: Correction }) {
  const { corrected, natural, mistakes, encouragement } = correction;
  return (
    <div className="correction">
      <section className="correction-block corrected">
        <h4>✓ Corrigido</h4>
        <p lang="en">{corrected}</p>
      </section>

      <section className="correction-block natural">
        <div className="correction-block-head">
          <h4>Como um americano diria</h4>
          <SpeakButton text={natural} label="Ouvir a versão natural" iconOnly className="icon tinted" iconSize={16} />
        </div>
        <p lang="en">{natural}</p>
      </section>

      <section className="correction-mistakes">
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
