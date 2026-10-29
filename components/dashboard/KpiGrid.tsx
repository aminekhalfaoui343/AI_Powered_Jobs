import type { DashboardStats } from "@/lib/metrics";

export function KpiGrid({ stats }: { stats: DashboardStats }) {
  const items = [
    { label: "Stored jobs", value: stats.total },
    { label: "Extracted", value: stats.complete },
    { label: "Processing", value: stats.processing },
    { label: "Failed", value: stats.failed },
    { label: "Companies", value: stats.companies },
  ];

  return (
    <div className="kpi-grid">
      {items.map((item) => (
        <article key={item.label} className="kpi-card">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      ))}
    </div>
  );
}
