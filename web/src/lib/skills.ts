// Nível por habilidade na tela de progresso: nomes, onde se mede cada uma e o texto embaixo da barra.
import type { SkillId, SkillLevel } from "../api/types";

export const SKILL_INFO: Record<SkillId, { emoji: string; label: string; unit: [string, string]; howTo: string }> = {
  vocabulary: { emoji: "📚", label: "Vocabulário", unit: ["revisão no Ler", "revisões no Ler"], howTo: "estude no Lock In, modo Ler" },
  listening: { emoji: "🎧", label: "Escuta", unit: ["ditado no Ouvir", "ditados no Ouvir"], howTo: "use o modo Ouvir no Lock In" },
  speaking: { emoji: "🎤", label: "Fala", unit: ["checagem de pronúncia", "checagens de pronúncia"], howTo: "cheque a pronúncia no Mic Check" },
  writing: { emoji: "✍️", label: "Escrita", unit: ["texto corrigido", "textos corrigidos"], howTo: "escreva no Daily Yap e peça a correção" },
};

/** "82% de acerto em 40 revisões no Ler", ou como começar a medir quando ainda não há acertos. */
export function skillNote(skill: SkillLevel): string {
  const info = SKILL_INFO[skill.id];
  if (skill.samples === 0 || skill.accuracy === null) return `Ainda sem medida: ${info.howTo}`;
  const unit = info.unit[skill.samples === 1 ? 0 : 1];
  return `${Math.round(skill.accuracy * 100)}% de acerto em ${skill.samples} ${unit}`;
}
