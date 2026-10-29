"use client";

import { Check, Globe2 } from "lucide-react";
import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { SourceStatus } from "@/lib/types";

interface SourceSelectorProps {
  selected: string[];
  onChange: (sources: string[]) => void;
}

function canSelect(source: SourceStatus) {
  return source.enabled && source.status === "available";
}

export function SourceSelector({ selected, onChange }: SourceSelectorProps) {
  const [catalog, setCatalog] = useState<SourceStatus[]>([]);

  useEffect(() => {
    let cancelled = false;
    getSources()
      .then((rows) => {
        if (cancelled) {
          return;
        }
        setCatalog(rows);
        const available = rows.filter(canSelect).map((source) => source.id);
        const stillValid = selected.filter((id) => available.includes(id));
        onChange(stillValid.length > 0 ? stillValid : available);
      })
      .catch(() => {
        if (!cancelled) {
          setCatalog([]);
        }
      });
    return () => {
      cancelled = true;
    };
    // Load the backend catalog once so the UI cannot send unknown source IDs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (catalog.length === 0) {
    return <p className="muted-copy">Loading sources from the API…</p>;
  }

  return (
    <div className="source-grid">
      {catalog.map((source) => {
        const selectable = canSelect(source);
        const active = selected.includes(source.id);
        return (
          <button
            type="button"
            key={source.id}
            className={active ? "source-option active" : "source-option"}
            onClick={() => {
              if (!selectable) {
                return;
              }
              onChange(active ? selected.filter((id) => id !== source.id) : [...selected, source.id]);
            }}
            aria-pressed={active}
            disabled={!selectable}
            title={selectable ? source.name : `${source.name} is ${source.status.replaceAll("_", " ")}`}
          >
            <span className="source-icon">
              <Globe2 size={17} />
            </span>
            <span>
              <strong>{source.name}</strong>
              <small>
                {selectable ? source.access_type.replaceAll("_", " ") : source.status.replaceAll("_", " ")}
              </small>
            </span>
            {active && <Check className="source-check" size={17} />}
          </button>
        );
      })}
    </div>
  );
}
