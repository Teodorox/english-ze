import { Link, useNavigate } from "react-router";
import { ActivityRings } from "../components/ActivityRings";
import { CheckIcon } from "../components/icons";
import { LargeTitle } from "../components/LargeTitle";
import { useMe } from "../components/MeContext";
import { useTodayPlan } from "../components/NextStep";
import { greeting } from "../lib/greeting";
import { fraction } from "../lib/stats";
import { GOALS } from "../lib/studyProfile";
import { addRound, nextStep, stepsDone } from "../lib/todayPlan";
import type { Tab } from "../tabs";

/** A primeira aba: o plano do dia, com os passos que já foram feitos marcados sozinhos. */
export function Today({ tab }: { tab: Tab }) {
  const me = useMe();
  const plan = useTodayPlan();
  const navigate = useNavigate();

  const goal = plan && GOALS.find((g) => g.id === plan.goal);
  const steps = plan && stepsDone(plan);
  const next = plan && nextStep(plan);

  function start() {
    if (!plan) return;
    if (next) {
      navigate(next.path);
    } else {
      addRound(); // dia completo: mais uma rodada de frases no Estudar
      navigate("/estudar");
    }
  }

  return (
    <section className="today-page">
      <LargeTitle tab={tab} greeting={me ? greeting(me.name) : undefined} />

      {plan && steps && (
        <>
          <div className="glass card today-summary">
            <ActivityRings
              size={84}
              label={`${steps.done} de ${steps.total} passos feitos hoje.`}
              rings={[{ fraction: fraction(steps.done, steps.total), color: "var(--tint)" }]}
            />
            <div className="today-summary-text">
              <h2>{plan.done ? "Dia completo! 🏆" : `${steps.done} de ${steps.total} passos`}</h2>
              <p>
                {plan.minutes} min por dia
                {goal && (
                  <>
                    {" "}
                    · tema de hoje: {goal.emoji} {goal.label}
                  </>
                )}
              </p>
            </div>
            <button type="button" className="primary today-start" onClick={start}>
              {plan.done ? "Mais uma rodada" : steps.done === 0 ? "Começar sessão" : "Continuar"}
            </button>
          </div>

          <ol className="today-steps" aria-label="Passos de hoje">
            {plan.items.map((item) => (
              <li key={item.id}>
                <Link to={item.path} className={`glass card today-step${item.done ? " done" : ""}`}>
                  <span className="today-step-check" aria-hidden="true">
                    {item.done && <CheckIcon />}
                  </span>
                  <span className="today-step-text">
                    <strong>{item.title}</strong>
                    <span>{item.detail}</span>
                  </span>
                  <span className="today-step-count">
                    {item.done ? "feito" : `${item.count}/${item.target}`}
                  </span>
                </Link>
              </li>
            ))}
          </ol>

          {plan.done && (
            <p className="footnote today-more">
              Quer ir além? "Mais uma rodada" traz mais frases e revisões no Estudar. Falar e escrever a mais também
              contam: é só abrir a aba.
            </p>
          )}
        </>
      )}
    </section>
  );
}
