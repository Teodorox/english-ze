import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { PROGRESS_EVENT } from "../api/study";
import { getToday, type TodayPlan } from "../api/today";
import { nextStep } from "../lib/todayPlan";
import { CheckIcon } from "./icons";

/** O plano de hoje, atualizado a cada avaliação, fala, entrada do diário ou frase minerada. */
export function useTodayPlan(): TodayPlan | null {
  const [plan, setPlan] = useState<TodayPlan | null>(null);
  const { pathname } = useLocation();

  useEffect(() => {
    const refresh = () => getToday().then(setPlan).catch(() => {});
    refresh();
    window.addEventListener(PROGRESS_EVENT, refresh);
    return () => window.removeEventListener(PROGRESS_EVENT, refresh);
  }, [pathname]);

  return plan;
}

/** Quando o passo desta tela fica pronto: "Feito! Próximo: ..." (ou "Plano de hoje completo"). */
export function NextStep({ path }: { path: string }) {
  const plan = useTodayPlan();
  const item = plan?.items.find((i) => i.path === path);
  if (!plan || !item?.done) return null;
  const next = nextStep(plan, path);

  return (
    <div className="next-step glass card" role="status">
      <span className="next-step-check" aria-hidden="true">
        <CheckIcon />
      </span>
      <div className="next-step-text">
        <strong>{next ? `${item.title}: feito!` : "Plano de hoje completo! 🏆"}</strong>
        <span>{next ? next.detail : "Você fez tudo o que planejou pra hoje."}</span>
      </div>
      <Link className="next-step-link" to={next ? next.path : "/hoje"}>
        {next ? `Próximo: ${next.title}` : "Ver o dia"} →
      </Link>
    </div>
  );
}
