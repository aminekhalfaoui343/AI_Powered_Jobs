export type JobStatus = "queued" | "in_progress" | "complete" | "failed" | "not_found" | string;

export interface SearchJobsRequest {
  query: string;
  location?: string;
  sources?: string[];
  max_results_per_source: number;
}

export interface SearchJobsError {
  url?: string;
  source?: string;
  error: string;
}

export interface SourceSearchResult {
  status: "success" | "failed" | "unavailable" | "disabled" | string;
  jobs_found: number;
  error?: string;
}

export interface SearchJobsResponse {
  query: string;
  sources_used: string[];
  jobs_discovered: number;
  jobs_enqueued: number;
  duplicates_skipped: number;
  status: string;
  jobs: JobResponse[];
  sources: Record<string, SourceSearchResult>;
  errors: SearchJobsError[];
}

export interface JobPosting {
  title?: string;
  company?: string;
  location?: string;
  description?: string;
  skills?: string[];
  experience?: string | null;
  education?: string | null;
  salary?: string | null;
  contract_type?: string | null;
  source?: string | null;
  source_url?: string | null;
  url?: string | null;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  result: JobPosting | null;
  error?: string;
}

export interface SearchRecord extends SearchJobsResponse {
  createdAt: string;
}

export interface HealthStatus {
  status: string;
  redis?: string;
  postgres?: string;
  detail?: string;
}

export interface SourceStatus {
  id: string;
  name: string;
  enabled: boolean;
  status: string;
  access_type: string;
}

export interface JobListResponse {
  jobs: JobResponse[];
}