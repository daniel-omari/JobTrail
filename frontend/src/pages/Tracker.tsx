import { useEffect, useState } from "react";
import { api, type Application } from "../api";
import { EmptyState } from "../components/EmptyState";
import { StageBadge } from "../components/StageBadge";
import { useScan } from "../scan-context";

const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "—");

function AppTable({ apps }: { apps: Application[] }) {
  return (
    <table className="data">
      <thead>
        <tr><th>Company</th><th>Role</th><th>Stage</th><th>Applied</th><th>Last update</th><th>Source</th></tr>
      </thead>
      <tbody>
        {apps.map((a) => (
          <tr key={a.id}>
            <td><strong>{a.company}</strong></td>
            <td>{a.role}</td>
            <td><StageBadge status={a.current_status} /></td>
            <td className="muted">{fmt(a.applied_date)}</td>
            <td className="muted">{fmt(a.last_update)}</td>
            <td className="muted small">{a.how_applied}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Tracker() {
  const { version } = useScan();
  const [active, setActive] = useState<Application[] | null>(null);
  const [archived, setArchived] = useState<Application[]>([]);
  useEffect(() => {
    api.applications(false).then(setActive);
    api.applications(true).then(setArchived);
  }, [version]);

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Tracker</h1><p className="muted">Every application JobTrail has found, and where it stands.</p></div>
      </div>
      <div className="card">
        <h2>Active applications</h2>
        {active && active.length === 0 ? (
          <EmptyState title="No active applications yet"><p>Run a scan to find application emails.</p></EmptyState>
        ) : active && <AppTable apps={active} />}
      </div>
      <div className="card">
        <h2>Rejected / No Response</h2>
        {archived.length === 0 ? <p className="muted">Nothing here yet.</p> : <AppTable apps={archived} />}
      </div>
    </div>
  );
}
