import { describe, expect, it } from "vitest";
import type { Card } from "../api/types";
import { afterGrade, counts, requeue, reveal, startQueue } from "./studyQueue";

function card(id: number, introduced = true): Card {
  return {
    id,
    front: `front ${id}`,
    back: `back ${id}`,
    note: "",
    category: "streamer",
    source: "",
    created_at: "2026-10-19T00:00:00",
    ease: 2.5,
    interval_days: 0,
    reps: 0,
    lapses: 0,
    due: introduced ? "2026-10-19" : null,
    introduced_on: introduced ? "2026-10-18" : null,
  };
}

describe("fila de estudo", () => {
  it("começa pelas revisões e depois os novos", () => {
    const state = startQueue({ due: [card(1)], new: [card(2, false)] });
    expect(state.current?.id).toBe(1);
    expect(state.queue.map((c) => c.id)).toEqual([2]);
    expect(counts(state)).toEqual({ remaining: 2, newCount: 1 });
  });

  it("sessão vazia não tem card atual", () => {
    const state = startQueue({ due: [], new: [] });
    expect(state.current).toBeNull();
    expect(counts(state)).toEqual({ remaining: 0, newCount: 0 });
  });

  it("acertar avança e conta a avaliação", () => {
    let state = reveal(startQueue({ due: [card(1), card(2)], new: [] }));
    expect(state.revealed).toBe(true);
    state = afterGrade(state, 2);
    expect(state.current?.id).toBe(2);
    expect(state.revealed).toBe(false);
    expect(state.done).toBe(1);
  });

  it("errar (L) manda o card pro fim da fila, já como estudado", () => {
    let state = startQueue({ due: [], new: [card(1, false), card(2, false)] });
    state = afterGrade(reveal(state), 0);
    expect(state.queue.map((c) => c.id)).toEqual([1]);
    expect(state.queue[0].introduced_on).not.toBeNull();
    expect(counts(state)).toEqual({ remaining: 2, newCount: 1 });
  });

  it("requeue devolve o card se o salvamento falhar", () => {
    let state = afterGrade(reveal(startQueue({ due: [card(1), card(2)], new: [] })), 2);
    state = requeue(state, card(1));
    expect(state.current?.id).toBe(2);
    expect(state.queue.map((c) => c.id)).toEqual([1]);

    // sessão já terminada: o card volta pra tela
    const finished = afterGrade(reveal(startQueue({ due: [card(3)], new: [] })), 2);
    expect(requeue(finished, card(3)).current?.id).toBe(3);
  });

  it("errar o último card faz ele voltar", () => {
    let state = startQueue({ due: [card(7)], new: [] });
    state = afterGrade(reveal(state), 0);
    expect(state.current?.id).toBe(7);
    state = afterGrade(reveal(state), 3);
    expect(state.current).toBeNull();
    expect(state.done).toBe(2);
  });
});
