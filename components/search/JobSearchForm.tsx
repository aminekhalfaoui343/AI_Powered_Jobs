"use client";

import { ArrowUpRight, Search, SlidersHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";
import { searchJobs } from "@/lib/api";
import type { JobResponse, SearchJobsResponse } from "@/lib/types";
import { SourceSelector } from "./SourceSelector";
import { SearchProgress } from "./SearchProgress";

export function JobSearchForm({
  jobs = [],
  onComplete,
}: {
  jobs?: JobResponse[];
  onComplete?: (summary: SearchJobsResponse) => void;
}) {
  const [query, setQuery] = useState(""); const [location, setLocation] = useState(""); const [sources, setSources] = useState<string[]>([]); const [limit, setLimit] = useState("10"); const [loading, setLoading] = useState(false); const [summary, setSummary] = useState<SearchJobsResponse | null>(null); const [error, setError] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); if (!query.trim() || sources.length === 0) return; setLoading(true); setError(""); setSummary(null); try { const result = await searchJobs({ query: query.trim(), location: location.trim() || undefined, sources, max_results_per_source: Number(limit) }); setSummary(result); onComplete?.(result); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to search jobs right now."); } finally { setLoading(false); } }
  return <div className="search-panel">
    <div className="panel-label"><span><Search size={16} /> Search workspace</span><span>ASYNC PIPELINE</span></div>
    <form onSubmit={submit}>
      <div className="form-row primary-row"><label className="field field-query"><span>What are you looking for?</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. DevOps Engineer, Python Developer" required /></label><label className="field"><span>Where?</span><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="e.g. Paris, Lyon, Remote" /></label></div>
      <div className="form-divider" />
      <div className="form-row options-row"><div className="field source-field"><span>Sources</span><SourceSelector selected={sources} onChange={setSources} /></div><label className="field limit-field"><span>Max results per source</span><span className="select-wrap"><SlidersHorizontal size={15} /><select value={limit} onChange={(event) => setLimit(event.target.value)}><option value="5">5 results</option><option value="10">10 results</option><option value="20">20 results</option><option value="50">50 results</option></select></span></label></div>
      {error && <div className="form-error" role="alert"><strong>Unable to search jobs</strong><span>{error} Please try again.</span></div>}
      <button className="search-button" type="submit" disabled={loading || sources.length === 0}>{loading ? "Searching..." : "Search jobs"}<ArrowUpRight size={18} /></button>
    </form>
    {summary && <SearchProgress summary={summary} jobs={jobs} />}
  </div>;
}