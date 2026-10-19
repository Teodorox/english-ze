import { useCallback, useEffect, useRef, useState } from "react";
import type { Grade } from "../api/types";

// Chat fictício da live que reage às suas avaliações.
const USERS = ["lilbro_22", "chat_goblin", "bronx_kid", "zeboy", "goat_watcher", "nyc_lurker", "yapper99", "lockedin_ana"];
const COLORS = ["var(--pink)", "var(--green-text)", "var(--orange-text)", "var(--tint-text)"];
const REACTIONS: Record<Grade, string[]> = {
  0: ["L 😭", "it's ok bro, run it back", "we been there 💀", "next one fr"],
  1: ["mid but we take those", "almost had it", "lock in 🔒", "keep cooking"],
  2: ["W", "W W W", "LETS GOOO", "bro is locked in 🔒", "no cap that was clean"],
  3: ["GOAT 🐐", "HE'S HIM", "aura +1000", "bro is cooking 🔥", "too easy"],
};
const VISIBLE_MS = 2700;
const MAX_MESSAGES = 3;

interface ChatMessage {
  id: number;
  user: string;
  color: string;
  text: string;
}

const pick = <T,>(list: T[]) => list[Math.floor(Math.random() * list.length)];

export function useChatFeed() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);
  const timers = useRef<number[]>([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const pop = useCallback((grade: Grade) => {
    const count = grade >= 2 ? 3 : 1;
    for (let i = 0; i < count; i++) {
      const id = nextId.current++;
      const message = { id, user: pick(USERS), color: pick(COLORS), text: pick(REACTIONS[grade]) };
      timers.current.push(
        window.setTimeout(() => setMessages((list) => [...list, message].slice(-MAX_MESSAGES)), i * 180),
        window.setTimeout(() => setMessages((list) => list.filter((m) => m.id !== id)), i * 180 + VISIBLE_MS),
      );
    }
  }, []);

  return { messages, pop };
}

export function ChatFeed({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="chat-feed" aria-hidden="true">
      {messages.map((m) => (
        <div key={m.id} className="chat-message glass">
          <strong style={{ color: m.color }}>{m.user}</strong> {m.text}
        </div>
      ))}
    </div>
  );
}
