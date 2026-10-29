import { Check, Compass, Search, Sparkles } from "lucide-react";

const stages = [
  { label: "Search", icon: Search },
  { label: "Discover", icon: Compass },
  { label: "Analyze", icon: Sparkles },
  { label: "Ready", icon: Check },
];

export function ProcessingPath({ activeIndex = 2 }: { activeIndex?: number }) {
  return (
    <div className="processing-path" aria-label="Search processing stages">
      {stages.map(({ label, icon: Icon }, index) => (
        <div className={`processing-stage${index <= activeIndex ? " is-active" : ""}`} key={label}>
          <span className="stage-dot">
            <Icon size={14} />
          </span>
          <span>{label}</span>
          {index < stages.length - 1 && <i />}
        </div>
      ))}
    </div>
  );
}
