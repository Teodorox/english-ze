import { describe, expect, it } from "vitest";
import { goalsSummary, levelLabel, toggleGoal } from "./studyProfile";

describe("perfil de estudo", () => {
  it("marca e desmarca objetivos, na ordem da lista", () => {
    expect(toggleGoal([], "musica")).toEqual(["musica"]);
    expect(toggleGoal(["musica"], "streamers")).toEqual(["streamers", "musica"]);
    expect(toggleGoal(["streamers", "musica"], "musica")).toEqual(["streamers"]);
  });

  it("resume os objetivos por extenso", () => {
    expect(goalsSummary(["viagem", "streamers"])).toBe("Streamers e games, Viagem");
    expect(goalsSummary([])).toBe("");
  });

  it("nome do nível", () => {
    expect(levelLabel("basico")).toBe("Me viro");
    expect(levelLabel(null)).toBe("Não informado");
  });
});
