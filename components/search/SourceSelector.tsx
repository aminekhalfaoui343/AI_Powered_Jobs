import { Check, Globe2 } from "lucide-react";

export const JOB_SOURCES = [
  { id: "france_travail", label: "France Travail", note: "National listings" },
  { id: "indeed", label: "Indeed", note: "Approved provider required" },
  { id: "hellowork", label: "HelloWork", note: "Adapter pending" },
  { id: "welcome_to_the_jungle", label: "Welcome to the Jungle", note: "JS or restricted" },
  { id: "jobteaser", label: "JobTeaser", note: "JS or restricted" },
  { id: "apec", label: "APEC", note: "Access method pending" },
];

interface SourceSelectorProps { selected: string[]; onChange: (sources: string[]) => void; }

export function SourceSelector({ selected, onChange }: SourceSelectorProps) {
  return <div className="source-grid">
    {JOB_SOURCES.map((source) => {
      const active = selected.includes(source.id);
      return <button type="button" key={source.id} className={active ? "source-option active" : "source-option"} onClick={() => onChange(active ? selected.filter((id) => id !== source.id) : [...selected, source.id])} aria-pressed={active}>
        <span className="source-icon"><Globe2 size={17} /></span><span><strong>{source.label}</strong><small>{source.note}</small></span>{active && <Check className="source-check" size={17} />}
      </button>;
    })}
  </div>;
}