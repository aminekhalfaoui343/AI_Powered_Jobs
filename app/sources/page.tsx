"use client";

import { useEffect, useState } from "react";
import { getSources } from "@/lib/api";
import type { SourceStatus } from "@/lib/types";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getSources()
      .then(setSources)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load sources."));
  }, []);

  return (
    <div className="dash-page">
      <div className="dash-heading">
        <div>
          <span className="eyebrow">Connectors</span>
          <h1>Job sources</h1>
        </div>
      </div>
      {error && (
        <div className="form-error" role="alert">
          <strong>Could not load sources</strong>
          <span>{error}</span>
        </div>
      )}
      <section className="dash-panel">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Enabled</th>
                <th>Access</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    <strong>{source.name}</strong>
                    <small>{source.id}</small>
                  </td>
                  <td>{source.status.replaceAll("_", " ")}</td>
                  <td>{source.enabled ? "Yes" : "No"}</td>
                  <td>{source.access_type.replaceAll("_", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sources.length === 0 && !error && (
          <p className="muted-copy">Source status appears when the API is reachable.</p>
        )}
      </section>
    </div>
  );
}
