import { SectionHead } from "../components/SectionHead";
import type { Tab } from "../tabs";

/** Tela provisória enquanto a aba não foi migrada para React (etapa 2). */
export function ComingSoon({ tab }: { tab: Tab }) {
  return (
    <section>
      <SectionHead tab={tab} />
      <div className="card">
        <p>
          {tab.icon} A aba <strong>{tab.pt}</strong> ainda está sendo migrada para a versão nova.
        </p>
        <p className="muted">Enquanto isso, ela continua funcionando normalmente na versão atual do app.</p>
      </div>
    </section>
  );
}
