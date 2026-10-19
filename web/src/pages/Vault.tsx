import { useEffect, useRef, useState } from "react";
import { deleteCard, listCards, listCategories } from "../api/cards";
import { ApiError } from "../api/client";
import type { Card } from "../api/types";
import { PlayIcon, SearchIcon, TrashIcon } from "../components/icons";
import { LargeTitle } from "../components/LargeTitle";
import { dueLabel } from "../lib/dueLabel";
import { speak } from "../lib/tts";
import type { Tab } from "../tabs";

const SEARCH_DELAY_MS = 250;
const errorMessage = (err: unknown) => (err instanceof ApiError ? err.message : "Sem conexão com o servidor.");

export function Vault({ tab }: { tab: Tab }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [cards, setCards] = useState<Card[] | null>(null);
  const [error, setError] = useState("");
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {});
  }, []);

  // Busca com espera curta; respostas atrasadas de buscas antigas são descartadas.
  useEffect(() => {
    const id = ++requestId.current;
    const timer = window.setTimeout(async () => {
      try {
        const result = await listCards({ q: query.trim(), category });
        if (id === requestId.current) {
          setCards(result);
          setError("");
        }
      } catch (err) {
        if (id === requestId.current) setError(errorMessage(err));
      }
    }, query ? SEARCH_DELAY_MS : 0);
    return () => window.clearTimeout(timer);
  }, [query, category]);

  async function handleDelete(card: Card) {
    setConfirmingId(null);
    try {
      await deleteCard(card.id);
      setCards((list) => list?.filter((c) => c.id !== card.id) ?? null);
    } catch (err) {
      setError(`Não consegui apagar "${card.front}" (${errorMessage(err).replace(/\.$/, "")}).`);
    }
  }

  return (
    <section>
      <LargeTitle
        tab={tab}
        accessory={cards && <span className="pill gray vault-count">{cards.length} cards</span>}
      />

      <label className="search-field">
        <SearchIcon width={18} height={18} />
        <input
          type="search"
          placeholder="Buscar frase, significado ou nota"
          aria-label="Buscar cards"
          spellCheck={false}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>

      <div className="filter-chips" role="group" aria-label="Filtrar por categoria">
        {["", ...categories].map((c) => (
          <button
            key={c || "todas"}
            type="button"
            className={`chip${c === category ? " selected" : ""}`}
            aria-pressed={c === category}
            onClick={() => setCategory(c)}
          >
            {c || "Todas"}
          </button>
        ))}
      </div>

      {error && (
        <p className="banner-error" role="alert">
          {error}
        </p>
      )}

      {cards && cards.length === 0 && (
        <div className="glass card vault-empty">
          <strong>Nada por aqui</strong>
          <p className="footnote">
            {query || category ? "Nenhum card com esse filtro." : "Você ainda não tem cards. Que tal minerar umas frases?"}
          </p>
        </div>
      )}

      {cards && cards.length > 0 && (
        <ul className="glass vault-list">
          {cards.map((card) => (
            <li key={card.id} className="vault-row">
              <div className="vault-text">
                <span className="vault-front" lang="en">
                  {card.front}
                </span>
                <span className="vault-back">{card.back}</span>
                <span className="footnote">
                  {card.category} · {dueLabel(card)}
                </span>
              </div>
              {confirmingId === card.id ? (
                <div className="vault-confirm">
                  <button type="button" className="small" onClick={() => setConfirmingId(null)}>
                    Cancelar
                  </button>
                  <button type="button" className="small destructive" onClick={() => handleDelete(card)}>
                    Apagar
                  </button>
                </div>
              ) : (
                <div className="vault-actions">
                  <button type="button" className="icon" aria-label={`Ouvir "${card.front}"`} onClick={() => speak(card.front)}>
                    <PlayIcon width={18} height={18} />
                  </button>
                  <button
                    type="button"
                    className="icon trash"
                    aria-label={`Apagar "${card.front}"`}
                    onClick={() => setConfirmingId(card.id)}
                  >
                    <TrashIcon width={18} height={18} />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
