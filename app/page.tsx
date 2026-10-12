"use client";

import { useEffect, useState } from "react";
import { JobSearchForm } from "@/components/search/JobSearchForm";
import { JobList } from "@/components/jobs/JobList";
import { isJobTerminal, refreshJobs } from "@/lib/api";
import type { JobResponse, SearchJobsResponse } from "@/lib/types";

export default function HomePage() {
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

  const finished = jobs.filter((job) => isJobTerminal(job.status)).length;
  const allDone = jobs.length > 0 && finished === jobs.length;

  return (
    <main>
      <section className="hero">
        <div className="hero-trajectory trajectory-one" />
        <div className="hero-trajectory trajectory-two" />
        <div className="hero-spark"><span /><span /><span /></div>
        <div className="shell hero-grid">
          <div>
            <span className="eyebrow">Glorea Career / Job intelligence</span>
            <h1>Your career path starts here.</h1>
            <p className="hero-copy">Search international opportunities across trusted sources, then let AI organize the signal so you can move forward with confidence.</p>
            <div className="hero-proof"><span>01</span> One search. A clearer direction.</div>
          </div>
          <div className="hero-aside">
            <span className="eyebrow">The journey</span>
            <strong>Search. Discover. Advance.</strong>
            <p>A focused workspace for ambitious careers and the opportunities that move them forward.</p>
          </div>
        </div>
      </section>
      <section className="search-wrap">
        <div className="shell">
          <JobSearchForm
            jobs={jobs}
            onComplete={(result) => {
              setLastSearch(result);
              setJobs(Array.isArray(result.jobs) ? result.jobs : []);
            }}
          />
        </div>
      </section>
      <section className="section" id="about">
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Your workspace</span>
              <h2>Recent opportunities</h2>
            </div>
            <p>
              {lastSearch
                ? allDone
                  ? `Results for “${lastSearch.query}” are ready.`
                  : `Results for “${lastSearch.query}” are being processed (${finished}/${jobs.length}).`
                : "Your processed opportunities will collect here as the pipeline completes."}
            </p>
          </div>
          <JobList jobs={jobs} />
        </div>
      </section>
    </main>
  );
}
