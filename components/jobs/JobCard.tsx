import Link from "next/link";
import { ArrowUpRight, MapPin } from "lucide-react";
import type { JobResponse } from "@/lib/types";
import { JobStatusBadge } from "./JobStatusBadge";

export function JobCard({ job }: { job: JobResponse }) {
  const result = job.result;
  return <article className="job-card"><div className="job-card-top"><JobStatusBadge status={job.status} /><span className="job-id">#{job.job_id.slice(0, 8)}</span></div><h3>{result?.title || "Job processing"}</h3>{result?.company && <p className="job-company">{result.company}</p>}{result?.location && <p className="job-location"><MapPin size={14} />{result.location}</p>}{result?.description && <p className="job-description">{result.description}</p>}{job.status === "failed" && job.error && <p className="job-description">{job.error}</p>}{result?.skills && result.skills.length > 0 && <div className="skill-list">{result.skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}</div>}<Link href={`/jobs/${job.job_id}`} className="text-link">View job <ArrowUpRight size={15} /></Link></article>;
}