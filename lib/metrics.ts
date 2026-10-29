import type { JobResponse } from "./types";

export function dashboardStats(jobs: JobResponse[]) {
  const complete = jobs.filter((job) => job.status === "complete").length;
  const failed = jobs.filter((job) => job.status === "failed").length;
  const processing = jobs.length - complete - failed;
  const companies = new Set(
    jobs.map((job) => job.result?.company).filter((value): value is string => Boolean(value)),
  ).size;

  const skillCounts: Record<string, number> = {};
  const sourceCounts: Record<string, number> = {};
  for (const job of jobs) {
    for (const skill of job.result?.skills ?? []) {
      skillCounts[skill] = (skillCounts[skill] || 0) + 1;
    }
    const source = job.result?.source || "unknown";
    sourceCounts[source] = (sourceCounts[source] || 0) + 1;
  }

  const topSkills = Object.entries(skillCounts)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 8);
  const maxSkill = topSkills[0]?.[1] ?? 1;

  return {
    total: jobs.length,
    complete,
    failed,
    processing,
    companies,
    topSkills,
    maxSkill,
    sourceCounts,
  };
}

export type DashboardStats = ReturnType<typeof dashboardStats>;
