import { CheckCircle2, CircleAlert, Clock3, Layers3 } from "lucide-react";
import type { JobResponse, SearchJobsResponse } from "@/lib/types";
import { isJobTerminal } from "@/lib/api";
import { ProcessingPath } from "./ProcessingPath";

export function SearchProgress({
  summary,
  jobs = [],
}: {
  summary: SearchJobsResponse;
  jobs?: JobResponse[];
}) {
  const failedSources = Object.entries(summary.sources).filter(([, result]) => result.status === "failed");
  const searchFailed = failedSources.length > 0 && summary.jobs_discovered === 0;
  const queueErrors = summary.errors.filter((error) => Boolean(error.url));
  const completed = jobs.filter((job) => job.status === "complete").length;
  const failed = jobs.filter((job) => job.status === "failed").length;
  const finished = jobs.filter((job) => isJobTerminal(job.status)).length;
  const allDone = jobs.length > 0 && finished === jobs.length;
  const activeIndex = searchFailed ? 0 : allDone ? 3 : finished > 0 ? 2 : 1;
  const statusLabel = searchFailed ? "failed" : allDone ? "ready" : "processing";

  return (
    <section className="search-summary" aria-live="polite">
      <div className="summary-heading">
        <div>
          <span className="eyebrow">{searchFailed ? "Search issue" : allDone ? "Search complete" : "Search started"}</span>
          <h2>
            {searchFailed
              ? "No opportunities could be retrieved."
              : allDone
                ? "Processed opportunities are ready."
                : "Your search is in motion."}
          </h2>
          <p>
            {searchFailed
              ? "Check the source error below and try again."
              : allDone
                ? `${completed} listing${completed === 1 ? "" : "s"} extracted${failed ? `, ${failed} failed` : ""}.`
                : `The pipeline is processing listings in the background. ${finished}/${jobs.length || summary.jobs_enqueued} finished.`}
          </p>
        </div>
        <span className="summary-status">
          <Clock3 size={15} /> {statusLabel}
        </span>
      </div>
      {!searchFailed && <ProcessingPath activeIndex={activeIndex} />}
      <div className="metric-grid">
        <div>
          <Layers3 size={18} />
          <strong>{summary.jobs_discovered}</strong>
          <span>Discovered</span>
        </div>
        <div>
          <CheckCircle2 size={18} />
          <strong>{completed || summary.jobs_enqueued}</strong>
          <span>{allDone ? "Extracted" : "Queued for AI"}</span>
        </div>
        <div>
          <CircleAlert size={18} />
          <strong>{failed || summary.duplicates_skipped}</strong>
          <span>{failed ? "Failed" : "Duplicates skipped"}</span>
        </div>
      </div>
      <div className="source-results">
        {Object.entries(summary.sources).map(([source, result]) => (
          <div key={source}>
            <strong>{source.replaceAll("_", " ")}</strong>
            <span>{result.status}</span>
            <small>{result.jobs_found} found</small>
          </div>
        ))}
      </div>
      {failedSources.map(
        ([source, result]) => result.error && <p key={source} className="summary-warning">{source.replaceAll("_", " ")}: {result.error}</p>,
      )}
      {queueErrors.length > 0 && (
        <p className="summary-warning">
          {queueErrors.length} listing{queueErrors.length === 1 ? "" : "s"} could not be queued.
        </p>
      )}
    </section>
  );
}
