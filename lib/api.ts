import type { JobResponse, SearchJobsRequest, SearchJobsResponse } from "./types";

const API_BASE = "/backend";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (error) {
    console.error("JobIntel API network error", error);
    throw new Error("The job search service is temporarily unavailable.");
  }

  if (!response.ok) {
    let message = "The job search service returned an error.";
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail || message;
    } catch {
      // Keep a stable user-facing error when the backend did not return JSON.
    }
    console.error("JobIntel API error", response.status, message);
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function searchJobs(payload: SearchJobsRequest) {
  return request<SearchJobsResponse>("/jobs/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getJob(jobId: string) {
  return request<JobResponse>(`/jobs/${encodeURIComponent(jobId)}`);
}

const TERMINAL_STATUSES = new Set(["complete", "failed", "not_found"]);

export function isJobTerminal(status: string) {
  return TERMINAL_STATUSES.has(status);
}

export async function refreshJobs(jobs: JobResponse[]): Promise<JobResponse[]> {
  return Promise.all(
    jobs.map(async (job) => {
      if (isJobTerminal(job.status)) {
        return job;
      }
      try {
        const next = await getJob(job.job_id);
        return {
          ...job,
          ...next,
          result: next.result || job.result,
        };
      } catch (error) {
        console.error("Job status poll failed", job.job_id, error);
        return job;
      }
    }),
  );
}