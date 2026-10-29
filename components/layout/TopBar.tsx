"use client";

import { Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";
import type { HealthStatus } from "@/lib/types";

export function TopBar({ onMenu }: { onMenu: () => void }) {
  const [health, setHealth] = useState<HealthStatus>({ status: "unknown" });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const next = await getHealth();
      if (!cancelled) {
        setHealth(next);
      }
    };
    void load();
    const timer = setInterval(load, 20000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const ok = health.status === "ok";

  return (
    <header className="dash-topbar">
      <button type="button" className="dash-menu" onClick={onMenu} aria-label="Open menu">
        <Menu size={18} />
      </button>
      <div>
        <strong>Job intelligence</strong>
        <span>FastAPI · Redis · PostgreSQL · ARQ</span>
      </div>
      <div className={ok ? "health-pills is-ok" : "health-pills is-down"}>
        <span />
        {ok ? "API · Redis · Postgres" : health.detail || "Services unavailable"}
      </div>
    </header>
  );
}
