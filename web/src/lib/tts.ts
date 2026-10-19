// Voz do navegador (Text-to-Speech) em inglês americano.

const supported = typeof window !== "undefined" && "speechSynthesis" in window;
let voice: SpeechSynthesisVoice | null = null;

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

export const ttsSupported = supported;

export function speak(text: string, rate = 1): void {
  if (!supported || !text) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = rate;
  if (voice) utterance.voice = voice;
  speechSynthesis.speak(utterance);
}
