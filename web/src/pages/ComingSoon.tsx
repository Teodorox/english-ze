import { LargeTitle } from "../components/LargeTitle";
import type { Tab } from "../tabs";

/** Tela provisória enquanto a aba não foi migrada para React (etapa 2.2). */
export function ComingSoon({ tab }: { tab: Tab }) {
  const { Icon } = tab;
  return (
    <section>
      <LargeTitle
        tab={tab}
        accessory={
          <span className="pill live-pill" style={{ marginBottom: 6 }}>
            <span className="dot" />
            LIVE
          </span>
        }
      />
      <div className="glass card">
        <p style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 6px", fontWeight: 600 }}>
          <Icon style={{ color: "var(--tint-text)" }} />
          Em migração
        </p>
        <p className="muted" style={{ margin: 0, fontSize: 15 }}>
          A tela <strong>{tab.pt}</strong> ainda está sendo passada para a versão nova. Enquanto isso, ela continua
          funcionando normalmente na versão atual do app.
        </p>
      </div>
    </section>
  );
}
