"use client";

import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getJob, isJobTerminal } from "@/lib/api";
import { JobDetails } from "@/components/jobs/JobDetails";
import { JobStatusBadge } from "@/components/jobs/JobStatusBadge";
import type { JobResponse } from "@/lib/types";

export default function JobPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState("");
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    const maxAttempts = 40;

    const poll = async () => {
      try {
        const next = await getJob(id);
        if (cancelled) {
          return;
        }
        setJob(next);
        setError("");
        if (isJobTerminal(next.status)) {
          return;
        }
        attempts += 1;
        if (attempts >= maxAttempts) {
          setTimedOut(true);
          return;
        }
        timer = setTimeout(poll, 3000);
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Unable to load this job.");
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [id]);

  if (error) {
    return (
      <main className="section">
        <div className="shell">
          <Link href="/jobs" className="text-link"><ArrowLeft size={15} /> Back to jobs</Link>
          <div className="empty-state" style={{ marginTop: 50 }}>
            <h3>Unable to load this job</h3>
            <p>{error}</p>
          </div>
        </div>
      </main>
    );
  }

  if (!job) {
    return (
      <main className="section">
        <div className="shell">
          <div className="empty-state">
            <RefreshCw className="spin" size={27} />
            <h3>Loading job details</h3>
            <p>The pipeline is checking the latest status.</p>
          </div>
        </div>
      </main>
    );
  }

  if (job.status === "failed" || job.status === "not_found") {
    return (
      <main className="section">
        <div className="shell">
          <Link href="/jobs" className="text-link"><ArrowLeft size={15} /> Back to jobs</Link>
          <div className="empty-state" style={{ marginTop: 50 }}>
            <JobStatusBadge status={job.status} />
            <h3>{job.status === "not_found" ? "Job not found" : "This job could not be processed"}</h3>
            <p>
              {job.status === "failed"
                ? job.error || "The pipeline was unable to structure this listing. Other listings in the same search can still complete."
                : "The job ID is no longer available."}
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main>
      <section className="detail-hero">
        <div className="shell">
          <Link href="/jobs" className="text-link"><ArrowLeft size={15} /> Back to jobs</Link>
          <h1>{job.result?.title || "Processing job details"}</h1>
          <div className="detail-kicker">
            <JobStatusBadge status={job.status} />
            {job.result?.company && <span>{job.result.company}</span>}
          </div>
        </div>
      </section>
      <section className="shell detail-content">
        {job.result ? (
          <JobDetails job={job.result} />
        ) : (
          <div className="empty-state">
            <RefreshCw className="spin" size={24} />
            <h3>{timedOut ? "Still processing" : "Extraction in progress"}</h3>
            <p>
              {timedOut
                ? "This listing is taking longer than expected. Refresh the page to check again, or go back to results that already completed."
                : "This page checks for updates every few seconds."}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
