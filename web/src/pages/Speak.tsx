import { useCallback, useEffect, useRef, useState } from "react";
import { listCards } from "../api/cards";
import { ApiError } from "../api/client";
import { saveSpeechCheck } from "../api/speech";
import { getTranscribeStatus, transcribeAudio } from "../api/transcribe";
import type { Card } from "../api/types";
import { MicIcon, ShuffleIcon, StopIcon } from "../components/icons";
import { SpeakButton } from "../components/SpeakButton";
import { LargeTitle } from "../components/LargeTitle";
import { LivePill } from "../components/LivePill";
import { ScoreRing } from "../components/ScoreRing";
import { scorePronunciation, verdict, type WordResult } from "../lib/pronunciation";
import { toSpeechCheck } from "../lib/speechCheck";
import { isIOS, isStandalone, listenOnce, recognitionSupported } from "../lib/speechRecognition";
import { useRecorder } from "../lib/useRecorder";
import type { Tab } from "../tabs";
import { NextStep } from "../components/NextStep";

interface CheckResult {
  heard: string;
  score: number;
  words: WordResult[];
}

export function Speak({ tab }: { tab: Tab }) {
  const [phrase, setPhrase] = useState("");
  const [cards, setCards] = useState<Card[] | null>(null);
  const [listening, setListening] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [checkError, setCheckError] = useState("");
  const [saveFailed, setSaveFailed] = useState(false);
  const [serverTranscribe, setServerTranscribe] = useState(false);
  const recorder = useRecorder(); // "Grave e compare"
  const checker = useRecorder(); // "Cheque a pronúncia" (quando o servidor transcreve)
  const awaitingCheck = useRef(false);
  const canRecognize = recognitionSupported();
  const canCheck = serverTranscribe || canRecognize;
  const iosHomeScreen = isIOS() && isStandalone();
  const cardsRef = useRef(cards);
  cardsRef.current = cards;

  // Mostra o resultado e guarda a nota no progresso (só os números; o áudio e o texto ficam aqui).
  const showResult = useCallback((target: string, heard: string) => {
    const scored = scorePronunciation(target, heard);
    setResult({ heard, ...scored });
    setSaveFailed(false);
    const check = toSpeechCheck(target, scored.words, cardsRef.current);
    if (check) saveSpeechCheck(check).catch(() => setSaveFailed(true));
  }, []);

  // Com o Whisper no servidor, a checagem funciona em qualquer navegador (inclusive no iPhone).
  useEffect(() => {
    getTranscribeStatus()
      .then((s) => setServerTranscribe(s.available))
      .catch(() => setServerTranscribe(false));
  }, []);

  // Terminou a gravação da checagem: manda pro servidor.
  useEffect(() => {
    if (!awaitingCheck.current || !checker.blob) return;
    awaitingCheck.current = false;
    const target = phrase.trim();
    setAnalyzing(true);
    transcribeAudio(checker.blob)
      .then(({ text }) => {
        if (text) showResult(target, text);
        else setCheckError("Não ouvi nada. Fale a frase logo depois de tocar no botão.");
      })
      .catch((err) => setCheckError(err instanceof ApiError ? err.message : "Sem conexão com o servidor."))
      .finally(() => setAnalyzing(false));
  }, [checker.blob, phrase, showResult]);

  useEffect(() => {
    if (checker.error) setCheckError(checker.error);
  }, [checker.error]);

  // onlyIfEmpty: o sorteio automático da abertura não sobrescreve o que a pessoa já digitou
  // (a lista de cards chega um instante depois de a tela abrir).
  const shuffle = useCallback(
    async (onlyIfEmpty = false) => {
      try {
        const list = cards ?? (await listCards());
        setCards(list);
        if (!list.length) return;
        const others = list.length > 1 ? list.filter((c) => c.front !== phrase) : list;
        const picked = others[Math.floor(Math.random() * others.length)].front;
        if (onlyIfEmpty) {
          setPhrase((current) => current || picked);
          return;
        }
        setPhrase(picked);
        setResult(null);
        setCheckError("");
      } catch {
        // sem cards: o usuário digita a própria frase
      }
    },
    [cards, phrase],
  );

  // Ao abrir a tela, já sorteia uma frase (só na primeira vez, por isso a lista vazia).
  useEffect(() => {
    if (!phrase) shuffle(true);
  }, []);

  async function checkPronunciation() {
    const target = phrase.trim();
    if (!target || listening || analyzing) return;

    if (serverTranscribe) {
      if (checker.recording) {
        checker.stop(); // o efeito acima envia a gravação
        return;
      }
      setCheckError("");
      setResult(null);
      awaitingCheck.current = true;
      await checker.start();
      return;
    }

    setListening(true);
    setCheckError("");
    setResult(null);
    try {
      showResult(target, await listenOnce());
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Não deu pra ouvir. Tenta de novo.");
    } finally {
      setListening(false);
    }
  }

  return (
    <section className="speak-page">
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
          <button type="button" className="small" onClick={() => shuffle()}>
            <ShuffleIcon width={15} height={15} />
            Sortear
          </button>
        </div>
      </div>

      {/* No computador, os dois passos ficam lado a lado. */}
      <div className="speak-steps">
        <div className="speak-step">
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
        </div>

        <div className="speak-step">
          <h2 className="section-header">2 · Cheque a pronúncia</h2>
          <div className="glass card speak-check">
            <button
              type="button"
              className={checker.recording ? "primary recording-check" : "primary"}
              onClick={checkPronunciation}
              disabled={!canCheck || listening || analyzing || !phrase.trim()}
            >
              {checker.recording ? <StopIcon width={18} height={18} /> : <MicIcon width={18} height={18} />}
              {checker.recording
                ? "Parar e checar"
                : analyzing
                  ? "Analisando..."
                  : listening
                    ? "Ouvindo... fale agora"
                    : "Checar pronúncia"}
            </button>
            {serverTranscribe && !result && !checkError && (
              <p className="footnote">Toque, fale a frase e toque de novo pra analisar.</p>
            )}
            {!canCheck && (
              <p className="footnote">Seu navegador não tem reconhecimento de voz. Use o Chrome, o Edge ou o Safari.</p>
            )}
            {!serverTranscribe && canRecognize && iosHomeScreen && (
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
                {saveFailed && (
                  <p className="footnote">Não consegui guardar essa nota no seu progresso. A checagem vale do mesmo jeito.</p>
                )}
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
        </div>
      </div>
      <NextStep path="/falar" />
    </section>
  );
}
