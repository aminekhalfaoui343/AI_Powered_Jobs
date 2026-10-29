"use client";

import { useEffect, useState } from "react";
import { JobSearchForm } from "@/components/search/JobSearchForm";
import { JobTable } from "@/components/jobs/JobTable";
import { isJobTerminal, refreshJobs } from "@/lib/api";
import type { JobResponse, SearchJobsResponse } from "@/lib/types";

export default function SearchPage() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [lastSearch, setLastSearch] = useState<SearchJobsResponse | null>(null);

  useEffect(() => {
    const queued = lastSearch?.jobs ?? [];
    if (queued.length === 0) {
      return;
    }

    let cancelled = false;
    let attempts = 0;
    let latest = queued;
    const maxAttempts = 45;

    const poll = async () => {
      if (cancelled) {
        return;
      }
      attempts += 1;
      latest = await refreshJobs(latest);
      if (cancelled) {
        return;
      }
      setJobs(latest);
      if (latest.every((job) => isJobTerminal(job.status)) || attempts >= maxAttempts) {
        return;
      }
      timer = setTimeout(poll, 2000);
    };

    let timer: ReturnType<typeof setTimeout> | undefined = setTimeout(poll, 800);
    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [lastSearch]);

  return (
    <div className="dash-page">
      <div className="dash-heading">
        <div>
          <span className="eyebrow">Search</span>
          <h1>Discover and extract listings</h1>
        </div>
      </div>
      <JobSearchForm
        jobs={jobs}
        onComplete={(result) => {
          setLastSearch(result);
          setJobs(Array.isArray(result.jobs) ? result.jobs : []);
        }}
      />
      <section className="dash-panel" style={{ marginTop: 24 }}>
        <div className="dash-panel-head">
          <h2>This search</h2>
          <span className="muted-copy">
            {lastSearch ? `${jobs.length} queued from “${lastSearch.query}”` : "Results appear after you search."}
          </span>
        </div>
        <JobTable jobs={jobs} empty="Submit a query to enqueue jobs through Redis and ARQ." />
      </section>
    </div>
  );
}
