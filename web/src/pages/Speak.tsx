import { useCallback, useEffect, useState } from "react";
import { listCards } from "../api/cards";
import type { Card } from "../api/types";
import { MicIcon, ShuffleIcon } from "../components/icons";
import { SpeakButton } from "../components/SpeakButton";
import { LargeTitle } from "../components/LargeTitle";
import { LivePill } from "../components/LivePill";
import { ScoreRing } from "../components/ScoreRing";
import { scorePronunciation, verdict, type WordResult } from "../lib/pronunciation";
import { isIOS, isStandalone, listenOnce, recognitionSupported } from "../lib/speechRecognition";
import { useRecorder } from "../lib/useRecorder";
import type { Tab } from "../tabs";

interface CheckResult {
  heard: string;
  score: number;
  words: WordResult[];
}

export function Speak({ tab }: { tab: Tab }) {
  const [phrase, setPhrase] = useState("");
  const [cards, setCards] = useState<Card[] | null>(null);
  const [listening, setListening] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [checkError, setCheckError] = useState("");
  const recorder = useRecorder();
  const canRecognize = recognitionSupported();
  const iosHomeScreen = isIOS() && isStandalone();

  const shuffle = useCallback(async () => {
    try {
      const list = cards ?? (await listCards());
      setCards(list);
      if (!list.length) return;
      const others = list.length > 1 ? list.filter((c) => c.front !== phrase) : list;
      setPhrase(others[Math.floor(Math.random() * others.length)].front);
      setResult(null);
      setCheckError("");
    } catch {
      // sem cards: o usuário digita a própria frase
    }
  }, [cards, phrase]);

  // Ao abrir a tela, já sorteia uma frase (só na primeira vez, por isso a lista vazia).
  useEffect(() => {
    if (!phrase) shuffle();
  }, []);

  async function checkPronunciation() {
    const target = phrase.trim();
    if (!target || listening) return;
    setListening(true);
    setCheckError("");
    setResult(null);
    try {
      const heard = await listenOnce();
      setResult({ heard, ...scorePronunciation(target, heard) });
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Não deu pra ouvir. Tenta de novo.");
    } finally {
      setListening(false);
    }
  }

  return (
    <section>
      <LargeTitle tab={tab} accessory={<LivePill />} />

      <div className="glass card speak-phrase">
        <label className="field">
          Frase pra praticar
          <textarea
            rows={2}
            lang="en"
            spellCheck={false}
            autoCapitalize="sentences"
            value={phrase}
            placeholder="Digite ou sorteie uma frase"
            onChange={(e) => {
              setPhrase(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <div className="button-row">
          <SpeakButton text={phrase} label="Ouvir" className="tinted small" />
          <SpeakButton text={phrase} label="Devagar" rate={0.7} slow className="small" />
          <button type="button" className="small" onClick={shuffle}>
            <ShuffleIcon width={15} height={15} />
            Sortear
          </button>
        </div>
      </div>

      <h2 className="section-header">1 · Grave e compare</h2>
      <div className="glass card speak-record">
        <div className="record-row">
          <button
            type="button"
            className={`record-button${recorder.recording ? " recording" : ""}`}
            aria-label={recorder.recording ? "Parar gravação" : "Gravar"}
            onClick={recorder.recording ? recorder.stop : recorder.start}
          >
            <span className="record-shape" />
          </button>
          <div>
            <strong>{recorder.recording ? "Gravando... toque pra parar" : "Toque pra gravar"}</strong>
            <p className="footnote" style={{ margin: "2px 0 0" }}>
              Ouça a frase, repita imitando o ritmo e a entonação, e compare com o original.
            </p>
          </div>
        </div>
        {recorder.audioUrl && !recorder.recording && (
          <audio key={recorder.audioUrl} className="recording-player" src={recorder.audioUrl} controls autoPlay />
        )}
        {recorder.error && (
          <p className="banner-error" role="alert">
            {recorder.error}
          </p>
        )}
      </div>

      <h2 className="section-header">2 · Cheque a pronúncia</h2>
      <div className="glass card speak-check">
        <button
          type="button"
          className="primary"
          onClick={checkPronunciation}
          disabled={!canRecognize || listening || !phrase.trim()}
        >
          <MicIcon width={18} height={18} />
          {listening ? "Ouvindo... fale agora" : "Checar pronúncia"}
        </button>
        {!canRecognize && (
          <p className="footnote">Seu navegador não tem reconhecimento de voz. Use o Chrome, o Edge ou o Safari.</p>
        )}
        {canRecognize && iosHomeScreen && (
          <p className="footnote">
            Aberto pelo ícone da Tela de Início, o iPhone pode bloquear a checagem de pronúncia. Se der erro, abra o app
            pelo Safari.
          </p>
        )}
        {checkError && (
          <p className="banner-error" role="alert">
            {checkError}
          </p>
        )}
        {result && (
          <div className="speak-result" aria-live="polite">
            <div className="speak-score">
              <ScoreRing score={result.score} />
              <div>
                <strong className="speak-verdict">{verdict(result.score)}</strong>
                <p className="footnote" style={{ margin: "2px 0 0" }}>
                  Entendi: “{result.heard}”
                </p>
              </div>
            </div>
            <div className="word-chips" lang="en">
              {result.words.map((w, i) => (
                <span key={`${w.word}-${i}`} className={`word-chip ${w.ok ? "ok" : "miss"}`}>
                  {w.word}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
