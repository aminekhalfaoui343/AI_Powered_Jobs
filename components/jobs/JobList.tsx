import { Inbox } from "lucide-react";
import type { JobResponse } from "@/lib/types";
import { JobCard } from "./JobCard";

export function JobList({ jobs }: { jobs: JobResponse[] }) {
  if (jobs.length === 0) return <div className="empty-state"><Inbox size={28} /><h3>No individual jobs to display yet</h3><p>Run a search to discover listings. Extracted details appear here as each job finishes.</p></div>;
  return <div className="job-list">{jobs.map((job) => <JobCard key={job.job_id} job={job} />)}</div>;
}