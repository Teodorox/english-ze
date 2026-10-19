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

const ERRORS: Record<string, string> = {
  "no-speech": "Não ouvi nada. Fale logo depois de tocar no botão.",
  "not-allowed": "Permissão do microfone negada. Libere nos ajustes do navegador.",
  "audio-capture": "Nenhum microfone encontrado.",
  network: "O reconhecimento de voz precisa de internet.",
};

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
      reject(new Error(ERRORS[event.error] ?? `Não deu pra ouvir (${event.error}). Tenta de novo.`));
    };
    recognition.onend = () => {
      if (!settled) reject(new Error(ERRORS["no-speech"]));
    };
    recognition.start();
  });
}
