import { CheckCircle2, CircleDashed, TriangleAlert } from "lucide-react";
import type { JobStatus } from "@/lib/types";

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const normalized = status === "complete" ? "completed" : status === "in_progress" ? "processing" : status;
  const icon = normalized === "completed" ? <CheckCircle2 size={14} /> : normalized === "failed" ? <TriangleAlert size={14} /> : <CircleDashed className="spin" size={14} />;
  return <span className={`status-badge status-${normalized}`}>{icon}{normalized === "completed" ? "Completed" : normalized === "failed" ? "Failed" : "Processing"}</span>;
}