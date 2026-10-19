import { useSyncExternalStore } from "react";
import { getSpeakingKey, speak, speechKey, stopSpeaking, subscribeSpeaking } from "../lib/tts";
import { PlayIcon, SlowIcon, StopIcon } from "./icons";

interface SpeakButtonProps {
  text: string;
  label: string; // ex.: "Ouvir", "Devagar"
  rate?: number;
  slow?: boolean; // ícone de "devagar" em vez de ▶
  iconOnly?: boolean; // só o ícone (o label vira o nome acessível)
  className?: string;
  iconSize?: number;
}

/** Botão de ouvir: mostra ■ "Parar" enquanto o áudio toca e, ao tocar de novo, para. */
export function SpeakButton({ text, label, rate = 1, slow = false, iconOnly = false, className = "", iconSize = 15 }: SpeakButtonProps) {
  const speakingKey = useSyncExternalStore(subscribeSpeaking, getSpeakingKey, () => null);
  const speaking = speakingKey === speechKey(text, rate);
  const Icon = speaking ? StopIcon : slow ? SlowIcon : PlayIcon;
  // Com texto visível: "Parar". Só ícone: o nome acessível diz o que vai parar (ex.: Parar "No cap").
  const name = speaking ? (iconOnly ? label.replace(/^(Ouvir|Devagar)/, "Parar") : "Parar") : label;

  return (
    <button
      type="button"
      className={`${className}${speaking ? " speaking" : ""}`}
      aria-label={iconOnly ? name : undefined}
      title={iconOnly ? name : undefined}
      disabled={!text.trim()}
      onClick={() => (speaking ? stopSpeaking() : speak(text, rate))}
    >
      <Icon width={iconSize} height={iconSize} />
      {!iconOnly && name}
    </button>
  );
}
