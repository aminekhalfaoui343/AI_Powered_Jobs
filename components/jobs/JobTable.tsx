import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { JobResponse } from "@/lib/types";
import { JobStatusBadge } from "./JobStatusBadge";

export function JobTable({
  jobs,
  empty = "No jobs match this view yet.",
}: {
  jobs: JobResponse[];
  empty?: string;
}) {
  if (jobs.length === 0) {
    return (
      <div className="empty-state compact">
        <h3>No jobs to display</h3>
        <p>{empty}</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Company</th>
            <th>Location</th>
            <th>Source</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.job_id}>
              <td>
                <strong>{job.result?.title || "Processing"}</strong>
                <small>#{job.job_id.slice(0, 8)}</small>
              </td>
              <td>{job.result?.company || "—"}</td>
              <td>{job.result?.location || "—"}</td>
              <td>{job.result?.source || "—"}</td>
              <td>
                <JobStatusBadge status={job.status} />
              </td>
              <td>
                <Link href={`/jobs/${job.job_id}`} className="text-link">
                  Open <ArrowUpRight size={14} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
