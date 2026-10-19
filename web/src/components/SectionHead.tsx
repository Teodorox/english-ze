import type { Tab } from "../tabs";

export function SectionHead({ tab }: { tab: Tab }) {
  return (
    <div className="section-head">
      <h2>{tab.label}</h2>
      <span className="pt">{tab.pt}</span>
      <span className="tag">{tab.tag}</span>
    </div>
  );
}
