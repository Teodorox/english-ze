import { useEffect, useRef, useState, type FormEvent } from "react";
import { createCard, listCategories } from "../api/cards";
import { ApiError } from "../api/client";
import { LargeTitle } from "../components/LargeTitle";
import { LivePill } from "../components/LivePill";
import { SpeakButton } from "../components/SpeakButton";
import { parseBulkLines, toBulkLine } from "../lib/bulkImport";
import type { Tab } from "../tabs";

type Notice = { kind: "success" | "error"; text: string } | null;

const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Sem conexão com o servidor.");

export function Mine({ tab }: { tab: Tab }) {
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [note, setNote] = useState("");
  const [category, setCategory] = useState("geral");
  const [source, setSource] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [bulkText, setBulkText] = useState("");
  const [bulkNotice, setBulkNotice] = useState<Notice>(null);
  const [importing, setImporting] = useState(false);
  const frontRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {});
  }, []);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      await createCard({ front, back, note, category: category || "geral", source });
      setNotice({ kind: "success", text: `Card salvo em "${category || "geral"}". Bora pro próximo!` });
      setFront("");
      setBack("");
      setNote("");
      if (category && !categories.includes(category)) setCategories([...categories, category].sort());
      frontRef.current?.focus(); // fonte e categoria ficam: normalmente você anota várias frases da mesma fonte
    } catch (err) {
      setNotice({ kind: "error", text: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  async function handleImport() {
    const { cards, invalid } = parseBulkLines(bulkText);
    if (!cards.length && !invalid.length) return;
    setImporting(true);
    setBulkNotice(null);
    let saved = 0;
    const failed: string[] = [...invalid];
    for (const card of cards) {
      try {
        await createCard({ ...card, category: category || "geral", source: source || "importado" });
        saved += 1;
      } catch {
        failed.push(toBulkLine(card));
      }
    }
    setBulkText(failed.join("\n")); // o que deu errado fica na caixa pra corrigir
    setBulkNotice(
      failed.length
        ? { kind: "error", text: `${saved} importados. ${failed.length} com problema (ficaram na caixa): falta o significado ou já existe.` }
        : { kind: "success", text: `${saved} cards importados em "${category || "geral"}".` },
    );
    setImporting(false);
  }

  return (
    <section className="mine-page">
      <LargeTitle tab={tab} accessory={<LivePill />} />
      <p className="footnote intro">
        Ouviu ou leu uma frase em inglês que não entendeu? Numa série, música, vídeo, jogo ou conversa: anote aqui e ela
        vira card. Seus cards entram na fila antes das frases das trilhas.
      </p>

      <form className="mine-form" onSubmit={handleSave}>
        <h2 className="section-header">Nova frase</h2>
        <div className="glass form-list">
          <label className="form-row">
            <span>Frase em inglês</span>
            <input
              ref={frontRef}
              required
              maxLength={500}
              lang="en"
              spellCheck={false}
              placeholder="I'm on my way"
              value={front}
              onChange={(e) => setFront(e.target.value)}
            />
          </label>
          <label className="form-row">
            <span>Significado</span>
            <input
              required
              maxLength={500}
              placeholder="Tô a caminho"
              value={back}
              onChange={(e) => setBack(e.target.value)}
            />
          </label>
          <label className="form-row">
            <span>Nota (opcional)</span>
            <input maxLength={1000} placeholder='"on my way" = a caminho' value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
        </div>
        <SpeakButton text={front} label="Ouvir a frase" className="tinted small hear-button" />

        <h2 className="section-header">Detalhes</h2>
        <div className="glass form-list">
          <label className="form-row">
            <span>Categoria</span>
            <input maxLength={40} value={category} onChange={(e) => setCategory(e.target.value)} />
          </label>
          {categories.length > 0 && (
            <div className="form-row category-picks" role="group" aria-label="Categorias usadas">
              {categories.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`chip${c === category ? " selected" : ""}`}
                  aria-pressed={c === category}
                  onClick={() => setCategory(c)}
                >
                  {c}
                </button>
              ))}
            </div>
          )}
          <label className="form-row">
            <span>Fonte (opcional)</span>
            <input maxLength={200} placeholder="Ex.: série, música, podcast, aula" value={source} onChange={(e) => setSource(e.target.value)} />
          </label>
        </div>

        {notice && (
          <p className={notice.kind === "success" ? "banner-success" : "banner-error"} role="status">
            {notice.text}
          </p>
        )}
        <button type="submit" className="primary full" disabled={saving}>
          {saving ? "Salvando..." : "Salvar card"}
        </button>
      </form>

      {/* No computador, a importação em lote fica na coluna da direita. */}
      <div className="mine-bulk">
        <h2 className="section-header">Importar várias de uma vez</h2>
        <div className="glass card bulk-import">
          <p className="footnote" style={{ marginTop: 0 }}>
            Uma por linha, no formato <code>frase | significado | nota</code>. Usam a categoria e a fonte acima.
          </p>
          <textarea
            rows={5}
            lang="en"
            spellCheck={false}
            aria-label="Frases para importar"
            placeholder={"Break a leg | Boa sorte | expressão comum\nI'm on my way | Tô a caminho"}
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
          />
          {bulkNotice && (
            <p className={bulkNotice.kind === "success" ? "banner-success" : "banner-error"} role="status">
              {bulkNotice.text}
            </p>
          )}
          <button type="button" className="tinted full" onClick={handleImport} disabled={importing || !bulkText.trim()}>
            {importing ? "Importando..." : "Importar"}
          </button>
        </div>
      </div>
    </section>
  );
}
