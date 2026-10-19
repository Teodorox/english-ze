import { useCallback, useEffect, useRef, useState } from "react";

function micError(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError") return "Permissão do microfone negada. Libere nos ajustes do navegador.";
  if (name === "NotFoundError") return "Nenhum microfone encontrado.";
  return "Não consegui acessar o microfone.";
}

/** Grava áudio do microfone e devolve um link pra ouvir a gravação. */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [error, setError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);

  // Ao sair da tela: libera o microfone.
  useEffect(() => () => recorderRef.current?.stream.getTracks().forEach((track) => track.stop()), []);

  // Cada gravação nova libera a anterior da memória.
  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  const start = useCallback(async () => {
    setError("");
    if (!window.isSecureContext) {
      setError("O microfone só funciona em conexão segura (https).");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Seu navegador não permite gravar áudio.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const recorded = new Blob(chunks, { type: recorder.mimeType });
        setBlob(recorded);
        setAudioUrl(URL.createObjectURL(recorded));
        setRecording(false);
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch (err) {
      setError(micError(err));
    }
  }, []);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  return { recording, audioUrl, blob, error, start, stop };
}
