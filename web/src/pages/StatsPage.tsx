import { useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { getStats } from "../api/stats";
import { PROGRESS_EVENT } from "../api/study";
import type { Stats } from "../api/types";
import { ActivityRings } from "../components/ActivityRings";
import { LargeTitle } from "../components/LargeTitle";
import { useMe } from "../components/MeContext";
import { Stepper } from "../components/Stepper";
import { todayIso } from "../lib/dueLabel";
import { SKILL_INFO, skillNote } from "../lib/skills";
import { daysActiveThisWeek, fraction, streakMessage, weekdayInitial } from "../lib/stats";
import { loadPref, savePref } from "../lib/storage";
import { levelLabel } from "../lib/studyProfile";
import type { Tab } from "../tabs";

export function StatsPage({ tab }: { tab: Tab }) {
  const me = useMe();
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");
  const [goal, setGoal] = useState<number>(() => loadPref("dailyGoal", 20));

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Sem conexão com o servidor."));
  }, []);

  function changeGoal(value: number) {
    setGoal(value);
    savePref("dailyGoal", value);
    window.dispatchEvent(new Event(PROGRESS_EVENT));
  }

  if (error) {
    return (
      <section>
        <LargeTitle tab={tab} />
        <p className="banner-error" role="alert">
          {error}
        </p>
      </section>
    );
  }
  if (!stats) return <LargeTitle tab={tab} />;

  const week = daysActiveThisWeek(stats.history);
  const today = todayIso();
  const max = Math.max(1, ...stats.history.map((d) => d.reviews));
  const rows = [
    { label: "Revisões hoje", value: String(stats.reviews_today) },
    { label: "Cards estudados", value: `${stats.learned} de ${stats.total_cards}` },
    { label: "Dominados (21+ dias)", value: String(stats.mature) },
    { label: "Pra revisar hoje", value: String(stats.due_today) },
    { label: "Pra amanhã", value: String(stats.due_tomorrow) },
  ];

  return (
    <section className="stats-page">
      <LargeTitle tab={tab} accessory={<span className="pill aura-pill">aura check</span>} />

      {/* No computador: anéis e números lado a lado; gráfico e ajustes embaixo, na largura toda. */}
      <div className="stats-summary">
        <div className="glass card rings-card">
          <ActivityRings
            label={`Meta do dia: ${stats.reviews_today} de ${goal} revisões. Semana: ${week} de 7 dias.`}
            rings={[
              { fraction: fraction(stats.reviews_today, goal), color: "var(--tint)" },
              { fraction: fraction(week, 7), color: "var(--pink)" },
            ]}
          />
          <dl className="rings-legend">
            <div>
              <dt>Meta do dia</dt>
              <dd className="tint">
                {stats.reviews_today} de {goal}
              </dd>
            </div>
            <div>
              <dt>Semana</dt>
              <dd className="pink">{week} de 7 dias</dd>
            </div>
            <div>
              <dt>Sequência</dt>
              <dd>
                {stats.streak} {stats.streak === 1 ? "dia" : "dias"} 🔥
              </dd>
            </div>
          </dl>
        </div>
        <p className="streak-message">{streakMessage(stats.streak)}</p>
      </div>

      <div className="stats-numbers">
        <h2 className="section-header">Números</h2>
        <ul className="glass stats-list">
          {rows.map((row) => (
            <li key={row.label}>
              <span>{row.label}</span>
              <span className="stats-value">{row.value}</span>
            </li>
          ))}
        </ul>
      </div>

      <h2 className="section-header">Seu nível</h2>
      <ul className="glass skills-list">
        {stats.skills.map((skill) => {
          const info = SKILL_INFO[skill.id];
          const pct = Math.round(skill.progress * 100);
          return (
            <li key={skill.id} className="skill-row">
              <div className="skill-head">
                <span className="skill-name">
                  <span aria-hidden="true">{info.emoji}</span> {info.label}
                </span>
                <span className="pill tint skill-band">{skill.band}</span>
              </div>
              <div
                className="skill-bar"
                role="progressbar"
                aria-label={`${info.label}: ${skill.band}${skill.next_band ? `, ${pct}% do caminho até ${skill.next_band}` : ""}`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={pct}
              >
                <span style={{ width: `${Math.max(pct, 2)}%` }} />
              </div>
              <p className="skill-note">
                {skillNote(skill)}
                {skill.next_band ? ` · ${pct}% até ${skill.next_band}` : " · topo da escala do app"}
              </p>
            </li>
          );
        })}
      </ul>
      {stats.skills.length > 0 && (
        <p className="footnote skills-footnote">
          Estimativa pelo que você faz no app, partindo do nível que você escolheu (
          {me ? levelLabel(me.level) : "seu nível"} = {stats.skills[0].start_band}). Sobe com acertos e prática,
          desce com erros. Não é certificado.
        </p>
      )}

      <h2 className="section-header">Revisões nos últimos 14 dias</h2>
      <div className="glass card chart-card">
        <div
          className="bar-chart"
          role="img"
          aria-label={stats.history.map((d) => `${d.day}: ${d.reviews}`).join(", ")}
        >
          {stats.history.map((d) => (
            <div key={d.day} className={`bar${d.day === today ? " today" : ""}`} title={`${d.day}: ${d.reviews} revisões`}>
              <span className="bar-value">{d.reviews || ""}</span>
              <span className="bar-fill" style={{ height: `${(d.reviews / max) * 100}%` }} />
              <span className="bar-day">{weekdayInitial(d.day)}</span>
            </div>
          ))}
        </div>
      </div>

      <h2 className="section-header">Ajustes</h2>
      <div className="glass card study-settings">
        <Stepper label="Meta diária" value={goal} min={5} max={200} step={5} onChange={changeGoal} />
      </div>
    </section>
  );
}
