"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="dash">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="dash-body">
        <TopBar onMenu={() => setOpen(true)} />
        <div className="dash-content">{children}</div>
      </div>
    </div>
  );
}
