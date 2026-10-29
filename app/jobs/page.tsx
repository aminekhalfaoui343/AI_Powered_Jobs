"use client";

import { useEffect, useMemo, useState } from "react";
import { JobTable } from "@/components/jobs/JobTable";
import { listJobs } from "@/lib/api";
import type { JobResponse } from "@/lib/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listJobs(200)
      .then((rows) => {
        if (!cancelled) {
          setJobs(rows);
        }
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Unable to load stored jobs.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return jobs.filter((job) => {
      if (status !== "all" && job.status !== status) {
        return false;
      }
      if (!needle) {
        return true;
      }
      const haystack = [job.result?.title, job.result?.company, job.result?.location, job.result?.source]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [jobs, query, status]);

  return (
    <div className="dash-page">
      <div className="dash-heading">
        <div>
          <span className="eyebrow">Library</span>
          <h1>Persisted jobs</h1>
        </div>
        <span className="muted-copy">{filtered.length} shown</span>
      </div>
      <div className="filter-bar">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter title, company, location"
        />
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="complete">Complete</option>
          <option value="failed">Failed</option>
          <option value="queued">Queued</option>
          <option value="in_progress">In progress</option>
        </select>
      </div>
      {error && (
        <div className="form-error" role="alert">
          <strong>Could not load jobs</strong>
          <span>{error}</span>
        </div>
      )}
      <section className="dash-panel">
        <JobTable jobs={filtered} empty="Stored extractions from PostgreSQL will appear here." />
      </section>
    </div>
  );
}
