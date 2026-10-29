"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";
import { KpiGrid } from "@/components/dashboard/KpiGrid";
import { JobTable } from "@/components/jobs/JobTable";
import { getSources, listJobs } from "@/lib/api";
import { dashboardStats } from "@/lib/metrics";
import type { JobResponse, SourceStatus } from "@/lib/types";

export default function OverviewPage() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([listJobs(50), getSources()])
      .then(([nextJobs, nextSources]) => {
        if (cancelled) {
          return;
        }
        setJobs(nextJobs);
        setSources(nextSources);
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Unable to load dashboard data.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = dashboardStats(jobs);

  return (
    <div className="dash-page">
      <div className="dash-heading">
        <div>
          <span className="eyebrow">Overview</span>
          <h1>Extracted jobs stored in PostgreSQL</h1>
        </div>
        <Link href="/search" className="text-link">
          New search <ArrowUpRight size={16} />
        </Link>
      </div>
      {error && (
        <div className="form-error" role="alert">
          <strong>Dashboard data unavailable</strong>
          <span>{error}</span>
        </div>
      )}
      <KpiGrid stats={stats} />
      <div className="dash-split">
        <section className="dash-panel">
          <div className="dash-panel-head">
            <h2>Recent jobs</h2>
            <Link href="/jobs" className="text-link">
              All jobs <ArrowUpRight size={14} />
            </Link>
          </div>
          <JobTable jobs={jobs.slice(0, 8)} empty="Run a search to persist listings here." />
        </section>
        <div className="dash-stack">
          <section className="dash-panel">
            <div className="dash-panel-head">
              <h2>Sources</h2>
            </div>
            <ul className="source-status-list">
              {sources.map((source) => (
                <li key={source.id}>
                  <span className={source.status === "available" ? "dot ok" : "dot muted"} />
                  <strong>{source.name}</strong>
                  <small>{source.status.replaceAll("_", " ")}</small>
                </li>
              ))}
            </ul>
          </section>
          <section className="dash-panel">
            <div className="dash-panel-head">
              <h2>Top skills</h2>
            </div>
            {stats.topSkills.length === 0 ? (
              <p className="muted-copy">Skills appear after extractions complete.</p>
            ) : (
              <ul className="skill-bars">
                {stats.topSkills.map(([skill, count]) => (
                  <li key={skill}>
                    <span>{skill}</span>
                    <i>
                      <b style={{ width: `${Math.max(12, (count / stats.maxSkill) * 100)}%` }} />
                    </i>
                    <em>{count}</em>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
