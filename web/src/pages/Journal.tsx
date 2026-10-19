import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { correctJournal, createJournal, getTutorStatus, listJournal } from "../api/journal";
import type { JournalEntry } from "../api/types";
import { CorrectionView } from "../components/CorrectionView";
import { CopyIcon, SparklesIcon } from "../components/icons";
import { LargeTitle } from "../components/LargeTitle";
import { LivePill } from "../components/LivePill";
import { copyText, correctionPrompt } from "../lib/correctionPrompt";
import type { Tab } from "../tabs";

interface Status {
  kind: "info" | "success" | "error";
  text: string;
}

const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Sem conexão com o servidor.");

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function Journal({ tab }: { tab: Tab }) {
  const [entries, setEntries] = useState<JournalEntry[] | null>(null);
  const [tutorEnabled, setTutorEnabled] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [composeStatus, setComposeStatus] = useState<Status | null>(null);
  const [entryStatus, setEntryStatus] = useState<Record<number, Status>>({});
  const [correcting, setCorrecting] = useState<number | null>(null);

  useEffect(() => {
    listJournal()
      .then(setEntries)
      .catch((err) => setComposeStatus({ kind: "error", text: errorMessage(err) }));
    getTutorStatus()
      .then((s) => setTutorEnabled(s.enabled))
      .catch(() => setTutorEnabled(false));
  }, []);

  const setStatus = (id: number, status: Status) => setEntryStatus((all) => ({ ...all, [id]: status }));

  async function correct(id: number) {
    setCorrecting(id);
    setStatus(id, { kind: "info", text: "Corrigindo..." });
    try {
      const { correction, cards_created } = await correctJournal(id);
      setEntries((list) => list?.map((e) => (e.id === id ? { ...e, correction } : e)) ?? null);
      setStatus(id, {
        kind: "success",
        text: cards_created
          ? `Corrigido! ${cards_created} ${cards_created === 1 ? "card novo" : "cards novos"} em "meus-erros".`
          : "Corrigido!",
      });
    } catch (err) {
      setStatus(id, { kind: "error", text: errorMessage(err) });
    } finally {
      setCorrecting(null);
    }
  }

  async function handleSave() {
    const content = text.trim();
    if (!content) return;
    setSaving(true);
    setComposeStatus(null);
    try {
      const entry = await createJournal(content);
      setEntries((list) => [entry, ...(list ?? [])]);
      setText("");
      if (tutorEnabled) await correct(entry.id);
      else setComposeStatus({ kind: "success", text: "Salvo! Use o botão de copiar pra pedir correção numa IA." });
    } catch (err) {
      setComposeStatus({ kind: "error", text: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  async function copyPrompt(content: string, onDone: (status: Status) => void) {
    const ok = await copyText(correctionPrompt(content));
    onDone(
      ok
        ? { kind: "success", text: "Prompt copiado! Cole no Claude ou no ChatGPT." }
        : { kind: "error", text: "Não consegui copiar automaticamente." },
    );
  }

  return (
    <section>
      <LargeTitle tab={tab} accessory={<LivePill />} />
      <p className="footnote intro">
        Escreva 2 ou 3 frases sobre o seu dia, sem medo de errar.{" "}
        {tutorEnabled
          ? 'A IA corrige e cada erro vira um card em "meus-erros".'
          : "Depois copie o prompt e cole numa IA gratuita pra receber correção."}
      </p>

      <div className="glass card compose">
        <textarea
          rows={4}
          lang="en"
          spellCheck={false}
          aria-label="Escreva em inglês"
          placeholder="Today I worked a lot and..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="button-row">
          <button type="button" className="primary" onClick={handleSave} disabled={saving || !text.trim()}>
            {tutorEnabled && <SparklesIcon width={18} height={18} />}
            {saving ? "Salvando..." : tutorEnabled ? "Salvar e corrigir" : "Salvar"}
          </button>
          <button
            type="button"
            className="tinted"
            onClick={() => copyPrompt(text, setComposeStatus)}
            disabled={!text.trim()}
          >
            <CopyIcon width={18} height={18} />
            Copiar prompt
          </button>
        </div>
        {composeStatus && (
          <p className={`status ${composeStatus.kind}`} role="status">
            {composeStatus.text}
          </p>
        )}
      </div>

      {entries && entries.length > 0 && <h2 className="section-header">Suas entradas</h2>}
      {entries?.map((entry) => {
        const status = entryStatus[entry.id];
        return (
          <article key={entry.id} className="glass card journal-entry">
            <header className="journal-entry-head">
              <time className="footnote" dateTime={entry.created_at}>
                {formatDate(entry.created_at)}
              </time>
              <div className="journal-entry-actions">
                {tutorEnabled && !entry.correction && (
                  <button
                    type="button"
                    className="icon"
                    aria-label="Corrigir com IA"
                    title="Corrigir com IA"
                    disabled={correcting !== null}
                    onClick={() => correct(entry.id)}
                  >
                    <SparklesIcon width={18} height={18} />
                  </button>
                )}
                <button
                  type="button"
                  className="icon"
                  aria-label="Copiar prompt de correção"
                  title="Copiar prompt de correção"
                  onClick={() => copyPrompt(entry.text, (s) => setStatus(entry.id, s))}
                >
                  <CopyIcon width={18} height={18} />
                </button>
              </div>
            </header>
            <p className="journal-text" lang="en">
              {entry.text}
            </p>
            {status && (
              <p className={`status ${status.kind}`} role="status">
                {status.text}
              </p>
            )}
            {entry.correction && <CorrectionView correction={entry.correction} />}
          </article>
        );
      })}
    </section>
  );
}
