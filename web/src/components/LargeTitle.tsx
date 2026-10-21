import type { ReactNode } from "react";
import type { Tab } from "../tabs";

/** Título grande no padrão iOS, com o nome em português embaixo e, se vier, uma saudação em cima. */
export function LargeTitle({ tab, accessory, greeting }: { tab: Tab; accessory?: ReactNode; greeting?: string }) {
  return (
    <div className="title-block">
      {greeting && <p className="greeting">{greeting}</p>}
      <div className="title-row">
        <h1 className="large-title">{tab.title}</h1>
        {accessory}
      </div>
      <p className="subtitle">{tab.pt}</p>
    </div>
  );
}
