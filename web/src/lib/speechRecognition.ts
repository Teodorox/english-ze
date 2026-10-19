// Reconhecimento de voz do navegador (Chrome, Edge e Safari). O TypeScript não traz
// os tipos dessa API, então declaramos só o que usamos.

interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
}

type RecognitionConstructor = new () => Recognition;

function getConstructor(): RecognitionConstructor | undefined {
  if (typeof window === "undefined") return undefined;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

export const recognitionSupported = () => Boolean(getConstructor());

export function isIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  // iPad recente se apresenta como Mac, mas tem tela de toque.
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

/** Aberto pelo ícone da Tela de Início (modo app), e não pelo navegador. */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const nav = navigator as Navigator & { standalone?: boolean };
  return nav.standalone === true || window.matchMedia?.("(display-mode: standalone)").matches;
}

const IOS_BLOCKED =
  "O iPhone bloqueou o reconhecimento de voz. Confira: Ditado ligado (Ajustes › Geral › Teclado › Ativar Ditado), " +
  "microfone liberado pro site (Ajustes › Apps › Safari › Microfone) e o app aberto pelo Safari, não pelo ícone da Tela de Início.";

const ERRORS: Record<string, string> = {
  "no-speech": "Não ouvi nada. Fale logo depois de tocar no botão.",
  "not-allowed": "Permissão do microfone negada. Libere o microfone nos ajustes do navegador.",
  "service-not-allowed": "O navegador bloqueou o reconhecimento de voz. Libere o microfone nas permissões do site.",
  "audio-capture": "Nenhum microfone encontrado.",
  network: "O reconhecimento de voz precisa de internet.",
};

function errorMessage(code: string): string {
  if (isIOS() && (code === "service-not-allowed" || code === "not-allowed")) return IOS_BLOCKED;
  return ERRORS[code] ?? `Não deu pra ouvir (${code}). Tenta de novo.`;
}

/** Escuta uma frase em inglês e devolve o que foi entendido. */
export function listenOnce(lang = "en-US"): Promise<string> {
  const Ctor = getConstructor();
  if (!Ctor) return Promise.reject(new Error("Seu navegador não tem reconhecimento de voz. Use o Chrome ou o Safari."));

  return new Promise((resolve, reject) => {
    const recognition = new Ctor();
    let settled = false;
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      settled = true;
      resolve(event.results[0][0].transcript);
    };
    recognition.onerror = (event) => {
      settled = true;
      reject(new Error(errorMessage(event.error)));
    };
    recognition.onend = () => {
      if (!settled) reject(new Error(ERRORS["no-speech"]));
    };
    recognition.start();
  });
}
