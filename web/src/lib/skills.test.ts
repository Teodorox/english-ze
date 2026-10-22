import { describe, expect, it } from "vitest";
import type { SkillLevel } from "../api/types";
import { skillNote } from "./skills";

const skill = (over: Partial<SkillLevel>): SkillLevel => ({
  id: "listening",
  value: 1,
  band: "A2",
  progress: 0,
  next_band: "B1",
  samples: 0,
  accuracy: null,
  start_band: "A2",
  ...over,
});

describe("nível por habilidade", () => {
  it("sem acertos ainda: diz como medir", () => {
    expect(skillNote(skill({}))).toBe("Ainda sem medida: use o modo Ouvir no Lock In");
  });

  it("com acertos: porcentagem e quantidade, no singular e no plural", () => {
    expect(skillNote(skill({ samples: 40, accuracy: 0.824 }))).toBe("82% de acerto em 40 ditados no Ouvir");
    expect(skillNote(skill({ id: "writing", samples: 1, accuracy: 0.5 }))).toBe("50% de acerto em 1 texto corrigido");
  });
});
