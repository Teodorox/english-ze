import type { ReactNode } from "react";
import type { Tab } from "../tabs";

/** Título grande no padrão iOS, com o nome em português embaixo. */
export function LargeTitle({ tab, accessory }: { tab: Tab; accessory?: ReactNode }) {
  return (
    <>
      <div className="title-row">
        <h1 className="large-title">{tab.title}</h1>
        {accessory}
      </div>
      <p className="subtitle">{tab.pt}</p>
    </>
  );
}
