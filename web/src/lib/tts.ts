// Voz do navegador (Text-to-Speech) em inglês americano.
// Guarda o que está tocando agora, pra os botões mostrarem "Parar" enquanto o áudio toca.

const supported = typeof window !== "undefined" && "speechSynthesis" in window;
let voice: SpeechSynthesisVoice | null = null;
let current: SpeechSynthesisUtterance | null = null;
let speakingKey: string | null = null;
const listeners = new Set<() => void>();

function pickVoice() {
  const voices = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("en-us"));
  // Vozes "Natural" (Edge), "Premium/Enhanced" (iPhone) e Google soam mais humanas.
  voice =
    voices.find((v) => /natural|premium|enhanced/i.test(v.name)) ??
    voices.find((v) => /google/i.test(v.name)) ??
    voices[0] ??
    null;
}

if (supported) {
  pickVoice();
  speechSynthesis.addEventListener("voiceschanged", pickVoice);
}

function setSpeaking(key: string | null) {
  speakingKey = key;
  listeners.forEach((listener) => listener());
}

export const ttsSupported = supported;

/** Identifica um áudio (o mesmo texto em velocidade diferente é outro áudio). */
export const speechKey = (text: string, rate = 1) => `${rate}|${text}`;

export function subscribeSpeaking(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const getSpeakingKey = () => speakingKey;

export function speak(text: string, rate = 1): void {
  if (!supported || !text.trim()) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = rate;
  if (voice) utterance.voice = voice;
  // Ao cancelar um áudio pra tocar outro, o antigo também "termina": só limpa se for o atual.
  const finished = () => {
    if (current === utterance) {
      current = null;
      setSpeaking(null);
    }
  };
  utterance.onend = finished;
  utterance.onerror = finished;
  current = utterance;
  setSpeaking(speechKey(text, rate));
  speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (!supported) return;
  current = null;
  speechSynthesis.cancel();
  setSpeaking(null);
}
